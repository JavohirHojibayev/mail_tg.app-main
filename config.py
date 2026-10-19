import os
from pathlib import Path

# .env faylini yuklash (mavjud bo'lsa)
env_path = Path(__file__).resolve().parent / ".env"

if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# Telegram Bot Token (maxfiy, faqat .env dan olinadi)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Mail Server & Domen
MAIL_SERVER = os.getenv("MAIL_SERVER", "127.0.0.1")
MAIL_DOMAIN = os.getenv("MAIL_DOMAIN", "uz-potash.uz")

# PostgreSQL sozlamalari (iRedMail vmail bazasi)
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "vmail")
DB_USER = os.getenv("DB_USER", "vmailadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# SSH sozlamalari (Server bilan to'g'ridan-to'g'ri xavfsiz sinxronizatsiya uchun)
SSH_HOST = os.getenv("SSH_HOST", "")
SSH_USER = os.getenv("SSH_USER", "")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "")

# Bot Administratori
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Javohir_Hojibayev")

# iRedAdmin Web sozlamalari (Faqat .env orqali olinadi)
IREDADMIN_URL = os.getenv("IREDADMIN_URL", "https://mail.uz-potash.uz/iredadmin")
IREDADMIN_USER = os.getenv("IREDADMIN_USER", "")
IREDADMIN_PASSWORD = os.getenv("IREDADMIN_PASSWORD", "")
