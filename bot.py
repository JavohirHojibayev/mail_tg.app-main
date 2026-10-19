#!/usr/bin/env python3
"""
UZ-Potash Korporativ Pochta — Telegram Bot
Asosiy ishga tushirish fayli
Bot: @dkzmail_bot
"""

import sys
import logging
from telebot import TeleBot
import config
from services.data_manager import DataManager
from handlers.bot_handlers import register_handlers

# Loglash sozlamalari
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("UZPotashBot")

def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN.startswith("YOUR_"):
        logger.error("❌ BOT_TOKEN sozlanmagan! Iltimos .env faylini tekshiring.")
        sys.exit(1)

    logger.info("🚀 UZ-Potash Telegram Bot ishga tushirilmoqda...")
    bot = TeleBot(config.BOT_TOKEN, parse_mode=None)

    # Ma'lumotlar menejeri
    data_manager = DataManager()

    # Avtomatik keshni yangilashga urinish
    try:
        data_manager.refresh_cache()
    except Exception as e:
        logger.warning(f"Boshlang'ich kesh yangilashda ogohlantirish: {e}")

    # Handlerlarni ro'yxatga olish
    register_handlers(bot, data_manager)

    bot_info = bot.get_me()
    logger.info(f"✅ Bot muvaffaqiyatli ulandi: @{bot_info.username} (ID: {bot_info.id})")
    print(f"\n==========================================")
    print(f"  UZ-POTASH KORPORATIV TELEGRAM BOT")
    print(f"  Bot Username: @{bot_info.username}")
    print(f"  Holati: ISHLAMOQDA (Polling...)")
    print(f"==========================================\n")

    # Polling orqali tinglash
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
    except Exception as e:
        logger.error(f"Kutilmagan xatolik yuz berdi: {e}")

if __name__ == "__main__":
    main()
