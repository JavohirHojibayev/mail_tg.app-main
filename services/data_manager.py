import logging
import json
import threading
import time
from pathlib import Path
from services.db_service import DBService
from utils.translit import calculate_match_score
from utils.parser import parse_employee_id
import config

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

            target_domain = getattr(config, "MAIL_DOMAIN", "uz-potash.uz").lower()
            new_users = []
            for su in server_users:
                em = su.get("email", "").lower().strip()
                if not em or "@" not in em or em.startswith("postmaster@"):
                    continue
                name = su.get("name", "").strip() or em.split("@")[0]
                emp_id_raw = su.get("employeeid", "")
                parsed = parse_employee_id(emp_id_raw)

                new_users.append({
                    "name": name,
                    "email": em,
                    "position": parsed["position"],
                    "phone": parsed["phone"],
                    "ip_phone": parsed["ip_phone"],
                    "raw_info": parsed["raw_info"]
                })

            new_users.sort(key=lambda x: x.get("name", "").lower())
            self._cached_users = new_users
            self._save_cache(new_users)
            logger.info(f"✅ Server sinxronizatsiyasi yakunlandi. Jami: {len(new_users)} ta xodim")
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

    def add_or_update_employee(self, name: str, email: str, position: str = "", phone: str = "", ip_phone: str = "", raw_info: str = "") -> bool:
        """Yangi xodim qo'shish yoki mavjudini yangilash"""
        email_clean = email.strip().lower()
        name_clean = name.strip() or email_clean.split('@')[0]
        pos_clean = position.strip() or "—"
        phone_clean = phone.strip() or "—"
        ip_clean = ip_phone.strip() or "—"

        if not raw_info:
            parts = []
            if pos_clean != "—":
                parts.append(pos_clean)
            if phone_clean != "—":
                parts.append(phone_clean)
            if ip_clean != "—":
                parts.append(ip_clean)
            raw_info = " / ".join(parts)

        # 1. Server bazasida upsert
        db_success = self.db.upsert_employee(name_clean, email_clean, raw_info)

        # 2. Lokal keshda yangilash yoki qo'shish
        all_users = self._load_cache()
        found = False
        for u in all_users:
            if u.get("email", "").lower() == email_clean:
                u["name"] = name_clean
                u["position"] = pos_clean
                u["phone"] = phone_clean
                u["ip_phone"] = ip_clean
                u["raw_info"] = raw_info
                found = True
                break

        if not found:
            all_users.append({
                "name": name_clean,
                "email": email_clean,
                "position": pos_clean,
                "phone": phone_clean,
                "ip_phone": ip_clean,
                "raw_info": raw_info
            })

        all_users.sort(key=lambda x: x.get("name", "").lower())
        self._cached_users = all_users
        self._save_cache(all_users)
        logger.info(f"✅ Xodim saqlandi: {email_clean} ({name_clean})")
        return db_success or True

