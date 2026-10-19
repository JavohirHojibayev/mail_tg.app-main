import logging
import json
import threading
import time
from pathlib import Path
from services.db_service import DBService
from utils.translit import calculate_match_score
from utils.parser import parse_employee_id

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "users_cache.json"

class DataManager:
    def __init__(self):
        self.db = DBService()
        self._cached_users = self._load_cache()
        # Fonda har 60 soniyada serverdan avtomatik sinxronizatsiya qilish
        self._start_background_sync()

    def _start_background_sync(self):
        def sync_worker():
            # Boshlang'ich kesh yangilash
            time.sleep(3)
            self.refresh_from_db()

            while True:
                time.sleep(60) # Har 60 soniyada (real-vaqt rejimida tekshiruv)
                try:
                    self.refresh_from_db()
                except Exception as e:
                    logger.warning(f"Avtomatik server sinxronizatsiya xatosi: {e}")

        sync_thread = threading.Thread(target=sync_worker, daemon=True, name="Server-AutoSync")
        sync_thread.start()

    def get_all_users_raw(self) -> list:
        """Barcha mavjud xodimlarni Kesh yoki xotiradan qaytaradi"""
        if self._cached_users:
            return self._cached_users
        self._cached_users = self._load_cache()
        return self._cached_users

    def get_users(self, search: str = None) -> list:
        """
        Xodimlarni qidirish:
        - Ism + familiya, lavozim, telefon yoki IP raqam bo'yicha topadi
        - Katta-kichik harf farqsiz (case-insensitive)
        - Lotin va Krill yozuvlariga to'liq moslashgan (transliteratsiya)
        - Eng mos kelgan xodimlar ball bo'yicha yuqorida chiqadi
        """
        all_users = self.get_all_users_raw()
        if not all_users:
            return []

        if not search:
            return all_users

        search_clean = search.strip()
        scored_users = []

        for u in all_users:
            score = calculate_match_score(u, search_clean)
            if score >= 20: # Moslik ostonasi
                scored_users.append((score, u))

        # Moslik darajasi bo'yicha saralash (eng moslari eng birinchi)
        scored_users.sort(key=lambda x: x[0], reverse=True)

        if scored_users and scored_users[0][0] >= 70:
            scored_users = [item for item in scored_users if item[0] >= 70]

        return [u for score, u in scored_users]

    def refresh_from_db(self) -> bool:
        """
        Server bazasidan (iRedAdmin / PostgreSQL) eng so'nggi xodimlarni o'qib
        avtomatik sinxronizatsiya qiladi.
        Yangi xodim qo'shilsa yoki lavozim/telefon/IP o'zgartirilsa, avtomatik yangilanadi.
        """
        try:
            if not self.db.is_available():
                return False
            server_users = self.db.get_users()
            if not server_users:
                return False

            current_users = self._load_cache()
            user_map = {u["email"].lower(): u for u in current_users}

            updated_count = 0
            for su in server_users:
                em = su.get("email", "").lower().strip()
                if not em:
                    continue
                name = su.get("name", "").strip() or em.split("@")[0]
                emp_id_raw = su.get("employeeid", "")
                parsed = parse_employee_id(emp_id_raw)

                if em in user_map:
                    existing = user_map[em]
                    changed = False
                    if name and existing.get("name") != name:
                        existing["name"] = name
                        changed = True
                    if existing.get("position") != parsed["position"]:
                        existing["position"] = parsed["position"]
                        changed = True
                    if existing.get("phone") != parsed["phone"]:
                        existing["phone"] = parsed["phone"]
                        changed = True
                    if existing.get("ip_phone") != parsed["ip_phone"]:
                        existing["ip_phone"] = parsed["ip_phone"]
                        changed = True
                    if existing.get("raw_info") != parsed["raw_info"]:
                        existing["raw_info"] = parsed["raw_info"]
                        changed = True

                    if changed:
                        updated_count += 1
                else:
                    user_map[em] = {
                        "name": name,
                        "email": em,
                        "position": parsed["position"],
                        "phone": parsed["phone"],
                        "ip_phone": parsed["ip_phone"],
                        "raw_info": parsed["raw_info"]
                    }
                    updated_count += 1

            merged_list = list(user_map.values())
            merged_list.sort(key=lambda x: x.get("name", "").lower())
            self._cached_users = merged_list
            self._save_cache(merged_list)
            logger.info(f"✅ Server sinxronizatsiyasi yakunlandi. Jami: {len(merged_list)} ta xodim (O'zgarishlar: {updated_count})")
            return True
        except Exception as e:
            logger.error(f"refresh_from_db xatosi: {e}")
            return False

    def refresh_cache(self) -> bool:
        return self.refresh_from_db()

    def _save_cache(self, users: list):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Kesh saqlashda xatolik: {e}")

    def _load_cache(self) -> list:
        if not CACHE_FILE.exists():
            return []
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    u.setdefault("position", "—")
                    u.setdefault("phone", "—")
                    u.setdefault("ip_phone", "—")
                    u.setdefault("raw_info", "")
                return data
        except Exception as e:
            logger.warning(f"Kesh o'qishda xatolik: {e}")
            return []

    def get_user_by_email(self, email: str) -> dict:
        """Berilgan email bo'yicha xodimni topadi"""
        if not email:
            return None
        target = email.strip().lower()
        for u in self.get_all_users_raw():
            if u.get("email", "").lower() == target:
                return u
        return None

    def update_user_employee_info(self, email: str, new_raw_info: str) -> bool:
        """
        Xodimning lavozim, telefon va IP telefon ma'lumotlarini server bazasida (PostgreSQL)
        hamda lokal keshda darhol yangilaydi.
        """
        parsed = parse_employee_id(new_raw_info)
        email_clean = email.strip().lower()

        # 1. Server bazasida yangilash
        db_success = self.db.update_employee_id(email_clean, new_raw_info)

        # 2. Lokal keshda yangilash
        all_users = self._load_cache()
        updated = False
        for u in all_users:
            if u.get("email", "").lower() == email_clean:
                u["position"] = parsed["position"]
                u["phone"] = parsed["phone"]
                u["ip_phone"] = parsed["ip_phone"]
                u["raw_info"] = parsed["raw_info"]
                updated = True
                break

        if updated:
            self._cached_users = all_users
            self._save_cache(all_users)
            logger.info(f"✅ Kesh yangilandi: {email_clean} -> {parsed}")

        return db_success or updated

