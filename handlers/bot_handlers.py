import logging
import math
import time
import uuid
from telebot import TeleBot
from telebot.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat
)
from services.data_manager import DataManager
from services.user_prefs import get_user_lang, set_user_lang
from utils.pdf_generator import generate_employees_pdf
from utils.locales import t, LANGUAGES
import config

logger = logging.getLogger(__name__)

PAGE_SIZE = 10

def get_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Foydalanuvchi tili bo'yicha asosiy menyu tugmalari"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, row_width=2)
    keyboard.add(
        KeyboardButton(t("btn_list", lang)),
        KeyboardButton(t("btn_search", lang))
    )
    keyboard.add(
        KeyboardButton(t("btn_pdf", lang)),
        KeyboardButton(t("btn_help", lang))
    )
    keyboard.add(
        KeyboardButton(t("btn_lang", lang))
    )
    return keyboard

def get_lang_inline_markup() -> InlineKeyboardMarkup:
    """Tilni tanlash uchun inline tugmalar (faqat O'zbek va Rus tili)"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang:ru")
    )
    return markup

def send_language_prompt(bot: TeleBot, chat_id: int):
    """Til tanlash kerakligini takidlovchi xabar"""
    text = (
        "🌐 *Iltimos, interfeys tilini tanlang / Пожалуйста, выберите язык интерфейса:*\n\n"
        "⚠️ _Botdan foydalanish uchun 2 tildan birini tanlashingiz lozim:_\n"
        "_Для работы с ботом необходимо выбрать один из 2 языков:_"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_lang_inline_markup())

def update_bot_commands_for_lang(bot: TeleBot, chat_id: int, lang: str):
    """Telegram [Menu] buyruqlarini ushbu chat uchun tanlangan tilda sozlash"""
    try:
        commands = [
            BotCommand("list", t("cmd_list", lang)),
            BotCommand("pdf", t("cmd_pdf", lang)),
            BotCommand("search", t("cmd_search", lang)),
            BotCommand("sync", t("cmd_sync", lang)),
            BotCommand("help", t("cmd_help", lang)),
            BotCommand("lang", t("cmd_lang", lang)),
            BotCommand("start", t("cmd_start", lang)),
        ]
        bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e:
        logger.warning(f"set_my_commands (chat scope) xatosi: {e}")

def build_pagination_text_and_markup(users: list, page: int, lang: str = "uz", prefix: str = "pg"):
    total_users = len(users)
    total_pages = max(1, math.ceil(total_users / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_users)
    page_users = users[start_idx:end_idx]

    lines = [
        t("pagination_header", lang),
        t("pagination_page_info", lang, page=page + 1, total_pages=total_pages, total_users=total_users),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    for idx, u in enumerate(page_users, start=start_idx + 1):
        name = u.get("name") or u.get("email", "").split("@")[0]
        pos = u.get("position", "—")
        email = u.get("email", "")
        phone = u.get("phone", "—")
        ip_phone = u.get("ip_phone", "—")

        entry = f"*{idx}.* 👤 *{name}*\n"
        if pos and pos != "—":
            entry += f"     💼 _{pos}_\n"
        entry += f"     📧 `{email}`\n"
        contacts = []
        if phone and phone != "—":
            contacts.append(f"📞 `{phone}`")
        if ip_phone and ip_phone != "—":
            contacts.append(f"☎️ `{ip_phone}`")
        if contacts:
            entry += f"     {' | '.join(contacts)}\n"
        lines.append(entry)

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(t("pagination_footer", lang))

    text = "\n".join(lines)

    # Inline navigatsiya tugmalari
    markup = InlineKeyboardMarkup()
    nav_row = []

    if page > 0:
        nav_row.append(InlineKeyboardButton(t("btn_prev", lang), callback_data=f"{prefix}:{page-1}"))
    else:
        nav_row.append(InlineKeyboardButton("⏹", callback_data="noop"))

    nav_row.append(InlineKeyboardButton(f"📄 {page+1} / {total_pages}", callback_data="noop"))

    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(t("btn_next", lang), callback_data=f"{prefix}:{page+1}"))
    else:
        nav_row.append(InlineKeyboardButton("⏹", callback_data="noop"))

    markup.row(*nav_row)
    markup.add(
        InlineKeyboardButton(t("btn_export_all_pdf", lang, total_users=total_users), callback_data="export_pdf")
    )

    return text, markup

def format_user_card(user: dict, lang: str = "uz") -> str:
    name = user.get("name") or user.get("email", "").split("@")[0]
    email = user.get("email", "—")
    position = user.get("position", "—")
    phone = user.get("phone", "—")
    ip_phone = user.get("ip_phone", "—")
    return t("user_card", lang, name=name, position=position, email=email, phone=phone, ip_phone=ip_phone)

SEARCH_SESSIONS: dict = {}
USER_LAST_SEARCH: dict = {}
MAX_SEARCH_SESSIONS = 500

def save_search_session(chat_id: int, query: str, users: list) -> str:
    sid = uuid.uuid4().hex[:8]
    if len(SEARCH_SESSIONS) > MAX_SEARCH_SESSIONS:
        sorted_keys = sorted(SEARCH_SESSIONS.keys(), key=lambda k: SEARCH_SESSIONS[k].get("time", 0))
        for k in sorted_keys[:100]:
            SEARCH_SESSIONS.pop(k, None)
    session_data = {
        "chat_id": chat_id,
        "query": query,
        "users": users,
        "time": time.time()
    }
    SEARCH_SESSIONS[sid] = session_data
    USER_LAST_SEARCH[chat_id] = session_data
    return sid

def get_search_session(sid: str, chat_id: int) -> dict:
    if sid and sid in SEARCH_SESSIONS:
        return SEARCH_SESSIONS[sid]
    if chat_id in USER_LAST_SEARCH:
        return USER_LAST_SEARCH[chat_id]
    return None

def build_search_pagination_text_and_markup(
    query: str, users: list, page: int, sid: str, lang: str = "uz"
):
    total_users = len(users)
    total_pages = max(1, math.ceil(total_users / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_users)
    page_users = users[start_idx:end_idx]

    safe_query = query.replace("*", "").replace("_", "").replace("`", "")
    header = t("search_found_multiple", lang, query=safe_query, count=total_users).rstrip()

    lines = [header]
    if total_pages > 1:
        lines.append(t("pagination_page_info", lang, page=page + 1, total_pages=total_pages, total_users=total_users).strip())
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for idx, u in enumerate(page_users, start=start_idx + 1):
        name = (u.get("name") or u.get("email", "").split("@")[0]).replace("*", "")
        email = u.get("email", "").replace("`", "")
        pos = (u.get("position", "—") or "—").replace("_", "")
        phone = u.get("phone", "—")
        ip_phone = u.get("ip_phone", "—")

        entry = f"*{idx}.* 👤 *{name}*\n"
        if pos and pos != "—":
            entry += f"     💼 _{pos}_\n"
        entry += f"     📧 `{email}`\n"
        contacts = []
        if phone and phone != "—":
            contacts.append(f"📞 `{phone}`")
        if ip_phone and ip_phone != "—":
            contacts.append(f"☎️ `{ip_phone}`")
        if contacts:
            entry += f"     {' | '.join(contacts)}\n"
        lines.append(entry)

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(t("pagination_footer", lang))

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup()
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(t("btn_prev", lang), callback_data=f"spg:{sid}:{page-1}"))
        else:
            nav_row.append(InlineKeyboardButton("⏹", callback_data="noop"))

        nav_row.append(InlineKeyboardButton(f"📄 {page+1} / {total_pages}", callback_data="noop"))

        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(t("btn_next", lang), callback_data=f"spg:{sid}:{page+1}"))
        else:
            nav_row.append(InlineKeyboardButton("⏹", callback_data="noop"))

        markup.row(*nav_row)

    # Faqat ushbu qidiruv natijalari uchun PDF tugmasi
    pdf_btn_text = f"{t('btn_results_pdf', lang)} ({total_users})"
    markup.add(
        InlineKeyboardButton(pdf_btn_text, callback_data=f"spdf:{sid}")
    )

    return text, markup

def send_pdf_document(bot: TeleBot, chat_id: int, users: list, lang: str = "uz", query: str = None):
    wait_msg = bot.send_message(
        chat_id,
        t("pdf_wait", lang),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(lang)
    )
    try:
        if query:
            pdf_title = f"DKZ AJ mail xodimlar ro'yxati (Qidiruv: {query})" if lang == "uz" else f"Список сотрудников АО «ДКЗ» (Поиск: {query})"
            caption = t("pdf_search_caption", lang, query=query, count=len(users))
        else:
            pdf_title = "DKZ AJ mail xodimlar ro'yxati" if lang == "uz" else "Список сотрудников АО «ДКЗ»"
            caption = t("pdf_caption", lang, count=len(users))

        pdf_path = generate_employees_pdf(users, title=pdf_title)
        with open(pdf_path, "rb") as f:
            bot.send_document(
                chat_id,
                f,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(lang)
            )
        try:
            bot.delete_message(chat_id, wait_msg.message_id)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"PDF yuborishda xatolik: {e}")
        bot.edit_message_text(
            f"❌ PDF xatosi: {str(e)}",
            chat_id=chat_id,
            message_id=wait_msg.message_id
        )

def register_handlers(bot: TeleBot, data_manager: DataManager):

    # Standart global buyruqlar menyusini o'rnatish
    try:
        # Standart (O'zbekcha)
        bot.set_my_commands([
            BotCommand("list", t("cmd_list", "uz")),
            BotCommand("pdf", t("cmd_pdf", "uz")),
            BotCommand("search", t("cmd_search", "uz")),
            BotCommand("sync", t("cmd_sync", "uz")),
            BotCommand("help", t("cmd_help", "uz")),
            BotCommand("lang", t("cmd_lang", "uz")),
            BotCommand("start", t("cmd_start", "uz")),
        ])
        # Rus tili uchun
        bot.set_my_commands([
            BotCommand("list", t("cmd_list", "ru")),
            BotCommand("pdf", t("cmd_pdf", "ru")),
            BotCommand("search", t("cmd_search", "ru")),
            BotCommand("sync", t("cmd_sync", "ru")),
            BotCommand("help", t("cmd_help", "ru")),
            BotCommand("lang", t("cmd_lang", "ru")),
            BotCommand("start", t("cmd_start", "ru")),
        ], language_code="ru")
    except Exception as e:
        logger.warning(f"set_my_commands xatosi: {e}")

    # /start
    @bot.message_handler(commands=['start'])
    def cmd_start(message: Message):
        chat_id = message.chat.id
        lang = get_user_lang(chat_id)

        # Start bosilganda til tanlash kerakligi takidlanadi
        send_language_prompt(bot, chat_id)

        if lang:
            update_bot_commands_for_lang(bot, chat_id, lang)
            users_count = len(data_manager.get_users())
            bot.send_message(
                chat_id,
                t("start_text", lang, count=users_count),
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(lang)
            )

    # /lang komandasi
    @bot.message_handler(commands=['lang'])
    def cmd_lang(message: Message):
        send_language_prompt(bot, message.chat.id)

    # 🔄 /sync komandasi (Server bilan darhol sinxronlash)
    @bot.message_handler(commands=['sync', 'refresh'])
    def cmd_sync(message: Message):
        lang = get_user_lang(message.chat.id) or "uz"
        wait_msg = bot.send_message(message.chat.id, t("sync_wait", lang), parse_mode="Markdown")
        try:
            success = data_manager.refresh_from_db()
            total_users = len(data_manager.get_all_users_raw())
            if success:
                bot.edit_message_text(
                    t("sync_success", lang, total=total_users, updated="bajarildi"),
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.edit_message_text(
                    f"ℹ️ Server ma'lumotlari keshlandi. Jami: {total_users} ta xodim.",
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id
                )
        except Exception as e:
            logger.error(f"/sync xatosi: {e}")
            bot.edit_message_text(
                f"❌ Sinxronizatsiya xatosi: {str(e)}",
                chat_id=message.chat.id,
                message_id=wait_msg.message_id
            )

    # /help va Yordam tugmasi
    @bot.message_handler(commands=['help'])
    @bot.message_handler(func=lambda m: m.text in [
        t("btn_help", "uz"), t("btn_help", "ru"), "ℹ️ Yordam", "ℹ️ Помощь"
    ])
    def cmd_help(message: Message):
        lang = get_user_lang(message.chat.id) or "uz"
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("💬 Javohir Hojibayev (Telegram)", url="https://t.me/Javohir_Hojibayev")
        )
        markup.add(
            InlineKeyboardButton("💬 Nurbek Jumayev (Telegram)", url="https://t.me/nurbekjumayev")
        )
        bot.send_message(
            message.chat.id,
            t("help_text", lang),
            parse_mode="Markdown",
            reply_markup=markup,
            disable_web_page_preview=True
        )

    # 📋 Ro'yxat komandasi (/list)
    @bot.message_handler(commands=['list'])
    @bot.message_handler(func=lambda m: m.text in [
        t("btn_list", "uz"), t("btn_list", "ru"), "📋 Xodimlar ro'yxati", "📋 Список сотрудников"
    ])
    def cmd_list(message: Message):
        lang = get_user_lang(message.chat.id) or "uz"
        users = data_manager.get_users()
        if not users:
            bot.send_message(
                message.chat.id,
                "⚠️ Ro'yxat bo'sh / Список пуст.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(lang)
            )
            return

        text, markup = build_pagination_text_and_markup(users, page=0, lang=lang, prefix="pg")
        bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=markup
        )

    # 📥 PDF yuklab olish (/pdf)
    @bot.message_handler(commands=['pdf'])
    @bot.message_handler(func=lambda m: m.text in [
        t("btn_pdf", "uz"), t("btn_pdf", "ru"), "📥 PDF yuklab olish", "📥 Скачать PDF"
    ])
    def cmd_pdf(message: Message):
        lang = get_user_lang(message.chat.id) or "uz"
        users = data_manager.get_users()
        if not users:
            bot.send_message(
                message.chat.id,
                "⚠️ Ro'yxat bo'sh / Список пуст.",
                reply_markup=get_main_keyboard(lang)
            )
            return
        send_pdf_document(bot, message.chat.id, users, lang=lang)

    # 🔍 Qidirish prompti (/search)
    @bot.message_handler(commands=['search'])
    @bot.message_handler(func=lambda m: m.text in [
        t("btn_search", "uz"), t("btn_search", "ru"), "🔍 Qidirish", "🔍 Поиск"
    ])
    def btn_search_prompt(message: Message):
        lang = get_user_lang(message.chat.id) or "uz"
        bot.send_message(
            message.chat.id,
            t("search_prompt", lang),
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(lang)
        )

    # 🌐 Til almashtirish tugmasi
    @bot.message_handler(func=lambda m: m.text in [
        t("btn_lang", "uz"), t("btn_lang", "ru"), "🌐 Til / Язык", "🌐 Язык / Til"
    ])
    def btn_lang_prompt(message: Message):
        send_language_prompt(bot, message.chat.id)

    # 👑 /admin (Faqat Javohir Hojibayev uchun maxsus boshqaruv)
    @bot.message_handler(commands=['admin'])
    def cmd_admin(message: Message):
        user = message.from_user
        username = (user.username or "").lower()
        target_admin = config.ADMIN_USERNAME.lower()

        if username != target_admin:
            bot.send_message(
                message.chat.id,
                f"⛔ *Ruxsat berilmagan!*\nBu bo'lim faqat bot administratori (@{config.ADMIN_USERNAME}) uchun.",
                parse_mode="Markdown"
            )
            return

        users_count = len(data_manager.get_users())
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔄 Server bilan sinxronlash (Sync Now)", callback_data="admin_sync")
        )
        markup.add(
            InlineKeyboardButton("📊 Baza holati va statistika", callback_data="admin_stats")
        )

        admin_text = (
            f"👑 *BOSH ADMINISTRATOR PANELI*\n\n"
            f"Assalomu alaykum, *Javohir Hojibayev*!\n\n"
            f"📊 *Tizim holati:*\n"
            f"• Xodimlar soni: *{users_count}* nafar\n"
            f"• Pochta serveri: `YOUR_SSH_HOST_HERE`\n"
            f"• Auto-Sync: *Faol (har 5 daqiqada)*\n"
            f"• Bot holati: *Online*\n\n"
            f"Kerakli amalni tanlang 👇"
        )
        bot.send_message(message.chat.id, admin_text, parse_mode="Markdown", reply_markup=markup)

    # Callback handler (Til tanlash, Pagination, PDF & Admin)
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call: CallbackQuery):
        data = call.data
        chat_id = call.message.chat.id

        if data == "noop":
            bot.answer_callback_query(call.id)
            return

        # Admin amallari
        if data == "admin_sync":
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            bot.answer_callback_query(call.id, "Sinxronizatsiya boshlandi...")
            success = data_manager.refresh_from_db()
            count = len(data_manager.get_users())
            if success:
                bot.send_message(chat_id, f"✅ Server bilan muvaffaqiyatli sinxronlandi!\nJami xodimlar: *{count}* nafar", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "⚠️ Sinxronizatsiyada ogohlantirish bo'ldi, keshdagi ma'lumotlar saqlab qolindi.")
            return

        if data == "admin_stats":
            count = len(data_manager.get_users())
            bot.answer_callback_query(call.id, f"Xodimlar: {count}")
            bot.send_message(
                chat_id,
                f"📈 *Batafsil statistika:*\n"
                f"• Jami korporativ pochta: *{count}* ta\n"
                f"• Rasmiy domen: `@uz-potash.uz`\n"
                f"• Boshqaruv serveri: `YOUR_SSH_HOST_HERE` (vmail)\n"
                f"• SSH ulanishi: *Muvaffaqiyatli*\n"
                f"• Bosh administrator: *@Javohir_Hojibayev*",
                parse_mode="Markdown"
            )
            return

        # 1. Til tanlash
        if data.startswith("set_lang:"):
            lang = data.split(":")[1]
            set_user_lang(chat_id, lang)
            bot.answer_callback_query(call.id, "✅")
            update_bot_commands_for_lang(bot, chat_id, lang)

            # Til o'rnatilganligi haqida xabar
            bot.send_message(
                chat_id,
                t("lang_selected_confirm", lang),
                parse_mode="Markdown"
            )

            # Asosiy salomlashish va menyuni chiqarish
            users_count = len(data_manager.get_users())
            bot.send_message(
                chat_id,
                t("start_text", lang, count=users_count),
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(lang)
            )
            return

        # 2. PDF yuklab olish (Barcha xodimlar)
        if data == "export_pdf":
            lang = get_user_lang(chat_id) or "uz"
            bot.answer_callback_query(call.id, "PDF...")
            users = data_manager.get_users()
            send_pdf_document(bot, chat_id, users, lang=lang)
            return

        # 3. 10 qatordan iborat barcha xodimlar pagination: pg:<page>
        if data.startswith("pg:"):
            page = int(data.split(":")[1])
            lang = get_user_lang(chat_id) or "uz"
            users = data_manager.get_users()
            text, markup = build_pagination_text_and_markup(users, page=page, lang=lang, prefix="pg")
            try:
                bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return

        # 4. Qidiruv natijalari pagination: spg:<sid>:<page>
        if data.startswith("spg:"):
            parts = data.split(":")
            if len(parts) == 3:
                sid = parts[1]
                page = int(parts[2])
                session = get_search_session(sid, chat_id)
                if not session or not session.get("users"):
                    bot.answer_callback_query(call.id, "Qidiruv eskirgan / Поиск устарел", show_alert=True)
                    return

                lang = get_user_lang(chat_id) or "uz"
                text, markup = build_search_pagination_text_and_markup(
                    query=session["query"],
                    users=session["users"],
                    page=page,
                    sid=sid,
                    lang=lang
                )
                try:
                    bot.edit_message_text(
                        text,
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.warning(f"edit_message_text xatosi (spg): {e}")
            bot.answer_callback_query(call.id)
            return

        # 5. Qidiruv natijalari bo'yicha PDF eksport: spdf:<sid>
        if data.startswith("spdf:"):
            parts = data.split(":")
            sid = parts[1] if len(parts) > 1 else ""
            session = get_search_session(sid, chat_id)
            lang = get_user_lang(chat_id) or "uz"
            if not session or not session.get("users"):
                bot.answer_callback_query(call.id, "Qidiruv eskirgan / Поиск устарел", show_alert=True)
                return

            bot.answer_callback_query(call.id, "PDF...")
            send_pdf_document(bot, chat_id, session["users"], lang=lang, query=session.get("query"))
            return

    # Foydalanuvchi istalgan matn yozganda avtomatik qidiruv
    @bot.message_handler(func=lambda m: True)
    def handle_text_search(message: Message):
        chat_id = message.chat.id
        query = message.text.strip()
        if not query or query.startswith("/"):
            return

        lang = get_user_lang(chat_id)
        if not lang:
            # Agar foydalanuvchi hali tilni tanlamagan bo'lsa, avval tilni tanlashni so'raymiz
            send_language_prompt(bot, chat_id)
            return

        users = data_manager.get_users(search=query)

        if not users:
            bot.send_message(
                chat_id,
                t("search_not_found", lang, query=query.replace("*", "").replace("_", "")),
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(lang)
            )
            return

        if len(users) == 1:
            user = users[0]
            sid = save_search_session(chat_id, query, users)
            text = (
                t("search_found_single", lang) +
                format_user_card(user, lang)
            )
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(f"{t('btn_results_pdf', lang)} (1)", callback_data=f"spdf:{sid}")
            )
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        else:
            sid = save_search_session(chat_id, query, users)
            text, markup = build_search_pagination_text_and_markup(
                query=query, users=users, page=0, sid=sid, lang=lang
            )
            bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )
