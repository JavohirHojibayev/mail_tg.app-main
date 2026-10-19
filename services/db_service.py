import logging
import re
import html
import requests
import urllib3
import psycopg2
from psycopg2.extras import RealDictCursor
import config

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DBService:
    def __init__(self):
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        self.dbname = config.DB_NAME
        self.user = config.DB_USER
        self.password = config.DB_PASSWORD

    def _get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            connect_timeout=2,
            cursor_factory=RealDictCursor
        )

    def _is_direct_available(self) -> bool:
        if not self.password:
            return False
        try:
            conn = self._get_connection()
            conn.close()
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        """Server bazasiga (DB, SSH yoki Web Sync orqali) ulanish mumkinligini tekshiradi"""
        if self._is_direct_available():
            return True
        if bool(config.SSH_HOST and config.SSH_PASSWORD):
            return True
        if bool(getattr(config, "IREDADMIN_URL", None) and getattr(config, "IREDADMIN_PASSWORD", None)):
            return True
        return False

    def _get_users_from_ssh(self) -> list:
        if not config.SSH_HOST or not config.SSH_PASSWORD:
            return []
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                config.SSH_HOST,
                username=config.SSH_USER,
                password=config.SSH_PASSWORD,
                timeout=5
            )
            sql = """
                SELECT 
                    m.username as email,
                    COALESCE(NULLIF(mp.display_name, ''), NULLIF(m.name, ''), split_part(m.username, '@', 1)) as name,
                    COALESCE(m.employeeid, '') as employeeid
                FROM mailbox m
                LEFT JOIN messenger_profiles mp ON mp.email = m.username
                WHERE m.active = 1
                ORDER BY name ASC;
            """
            cmd = f"PGPASSWORD='{self.password}' psql -h 127.0.0.1 -U {self.user} -d {self.dbname} -t -A -F'|' -c \"{sql}\""
            stdin, stdout, stderr = client.exec_command(cmd)
            raw = stdout.read().decode('utf-8').strip()
            client.close()

            if not raw:
                return []

            users = []
            for line in raw.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    email = parts[0].strip().lower()
                    name = parts[1].strip() or email.split('@')[0]
                    emp_id = parts[2].strip() if len(parts) >= 3 else ""
                    users.append({"name": name, "email": email, "employeeid": emp_id})
            return users
        except Exception as e:
            logger.error(f"SSH get_users xatosi: {e}")
            return []

    def _get_users_from_web(self) -> list:
        """
        iRedAdmin Web boshqaruv paneli orqali to'g'ridan-to'g'ri foydalanuvchilar va
        ularning 'User/Employee ID' (lavozim/telefon/IP) ma'lumotlarini sinxronlash.
        """
        base_url = getattr(config, "IREDADMIN_URL", "")
        admin_user = getattr(config, "IREDADMIN_USER", "")
        admin_pwd = getattr(config, "IREDADMIN_PASSWORD", "")

        if not base_url or not admin_pwd:
            return []

        try:
            s = requests.Session()
            login_url = f"{base_url.rstrip('/')}/login"
            login_res = s.post(
                login_url,
                data={
                    "username": admin_user,
                    "password": admin_pwd,
                    "form_login": "Login"
                },
                verify=False,
                timeout=10
            )

            if login_res.status_code != 200:
                logger.warning(f"iRedAdmin web tizimiga kirishda xatolik: HTTP {login_res.status_code}")
                return []

            domain = getattr(config, "MAIL_DOMAIN", "uz-potash.uz")
            users = []
            page = 1

            while page <= 20: # Cheklov (20 sahifa x 50 ta = 1000 xodim)
                page_url = f"{base_url.rstrip('/')}/users/{domain}/page/{page}?order_name=name"
                res = s.get(page_url, verify=False, timeout=10)
                if res.status_code != 200:
                    break

                pos = res.text.find('<tbody>')
                end_pos = res.text.find('</tbody>')
                if pos == -1 or end_pos == -1:
                    break

                tbody = res.text[pos:end_pos]
                rows = tbody.split('<tr>')
                found_on_page = 0

                for r in rows:
                    if not r.strip():
                        continue

                    # Email
                    m_email = re.search(r'name=["\']mail["\'][^>]*value=["\']([^"\']+)["\']', r)
                    if not m_email:
                        continue
                    email = m_email.group(1).strip().lower()

                    # Display Name
                    m_name = re.search(r'<a[^>]+title=["\']Edit account profile["\'][^>]*>(.*?)</a>', r)
                    raw_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip() if m_name else email.split('@')[0]
                    name = html.unescape(raw_name)

                    # User/Employee ID (3-vcenter td)
                    tds = re.findall(r'<td[^>]*class=["\']vcenter["\'][^>]*>(.*?)</td>', r, re.DOTALL)
                    emp_id = ""
                    if len(tds) >= 3:
                        raw_emp = re.sub(r'<[^>]+>', '', tds[2]).strip()
                        emp_id = html.unescape(raw_emp)

                    users.append({
                        "name": name,
                        "email": email,
                        "employeeid": emp_id
                    })
                    found_on_page += 1

                if found_on_page == 0:
                    break
                page += 1

            logger.info(f"🌐 iRedAdmin Web orqali {len(users)} ta xodim ma'lumotlari muvaffaqiyatli olindi.")
            return users
        except Exception as e:
            logger.error(f"iRedAdmin Web sinxronizatsiya xatosi: {e}")
            return []

    def get_users(self) -> list:
        """Serverdan (DB, SSH yoki Web orqali) eng so'nggi xodimlar ro'yxatini oladi"""
        # 1. To'g'ridan-to'g'ri PostgreSQL orqali urinib ko'rish
        if self._is_direct_available():
            conn = None
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                query = """
                    SELECT 
                        m.username as email,
                        COALESCE(NULLIF(mp.display_name, ''), NULLIF(m.name, ''), split_part(m.username, '@', 1)) as name,
                        COALESCE(m.employeeid, '') as employeeid
                    FROM mailbox m
                    LEFT JOIN messenger_profiles mp ON mp.email = m.username
                    WHERE m.active = 1
                    ORDER BY name ASC;
                """
                cur.execute(query)
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"DB get_users xatosi: {e}")
            finally:
                if conn:
                    conn.close()

        # 2. Agar port 5432 tashqaridan yopiq bo'lsa, xavfsiz SSH orqali olish
        ssh_users = self._get_users_from_ssh()
        if ssh_users:
            return ssh_users

        # 3. Web boshqaruv paneli (iRedAdmin HTTPS) orqali olish
        web_users = self._get_users_from_web()
        if web_users:
            return web_users

        return []

