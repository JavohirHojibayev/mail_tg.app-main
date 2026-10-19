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
from utils.parser import parse_employee_template
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
            pdf_title = f"DKZ AJ xodimlar ma'lumotlari (Qidiruv: {query})" if lang == "uz" else f"Информация о сотрудниках АО «ДКЗ» (Поиск: {query})"
            caption = t("pdf_search_caption", lang, query=query, count=len(users))
        else:
            pdf_title = "DKZ AJ xodimlar ma'lumotlari" if lang == "uz" else "Информация о сотрудниках АО «ДКЗ»"
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

ADMIN_AUTH_SESSIONS = {}
AUTH_SESSION_LIFETIME = 600  # 10 daqiqa faol seans

def is_admin_authenticated(chat_id: int) -> bool:
    """Admin paroli tasdiqlanganligini tekshiradi"""
    return time.time() < ADMIN_AUTH_SESSIONS.get(chat_id, 0)

def set_admin_authenticated(chat_id: int):
    """Admin seansini faollashtiradi"""
    ADMIN_AUTH_SESSIONS[chat_id] = time.time() + AUTH_SESSION_LIFETIME

def clear_admin_auth(chat_id: int):
    """Admin seansini qulflaydi"""
    ADMIN_AUTH_SESSIONS.pop(chat_id, None)

def get_admin_keyboard(is_auth: bool = False) -> InlineKeyboardMarkup:
    """Bosh administrator paneli tugmalari"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✏️ Xodimni tahrirlash", callback_data="admin_edit_search"),
        InlineKeyboardButton("➕ Yangi xodim qo'shish", callback_data="admin_add_user")
    )
    markup.add(
        InlineKeyboardButton("🔄 Server bilan sinxronlash (Sync Now)", callback_data="admin_sync")
    )
    markup.add(
        InlineKeyboardButton("📊 Baza holati va statistika", callback_data="admin_stats")
    )
    if is_auth:
        markup.add(
            InlineKeyboardButton("🔒 Seansni qulflash (Chiqish)", callback_data="admin_lock")
        )
    return markup

def get_user_edit_markup(email: str) -> InlineKeyboardMarkup:
    """Xodim ma'lumotlarini tahrirlash uchun maxsus menyu"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💼 Lavozim", callback_data=f"adm_ed:pos:{email}"),
        InlineKeyboardButton("📞 Telefon", callback_data=f"adm_ed:ph:{email}")
    )
    markup.row(
        InlineKeyboardButton("☎️ IP telefon", callback_data=f"adm_ed:ip:{email}"),
        InlineKeyboardButton("📝 Hammasi bittada", callback_data=f"adm_ed:all:{email}")
    )
    markup.add(
        InlineKeyboardButton("🗑 Ma'lumotlarni tozalash", callback_data=f"adm_ed:clear:{email}")
    )
    markup.add(
        InlineKeyboardButton("🔙 Admin menyusiga qaytish", callback_data="admin_menu")
    )
    return markup

def send_user_edit_menu(bot: TeleBot, chat_id: int, user: dict, edit_message_id: int = None):
    """Xodim ma'lumotlari kartasi va tahrirlash tugmalarini chiqarish"""
    name = user.get("name") or user.get("email", "").split("@")[0]
    email = user.get("email", "")
    pos = user.get("position") or "—"
    phone = user.get("phone") or "—"
    ip = user.get("ip_phone") or "—"
    raw = user.get("raw_info") or "—"

    text = (
        f"👑 *BOSH ADMINISTRATOR: Xodim tahrirlash*\n\n"
        f"• *Ism:* {name}\n"
        f"• *Email:* `{email}`\n"
        f"• *Lavozim:* {pos}\n"
        f"• *Telefon:* `{phone}`\n"
        f"• *IP telefon:* `{ip}`\n"
        f"• *Bazada (employeeid):* `{raw}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Qaysi ma'lumotni kiritmoqchisiz yoki o'zgartirmoqchisiz? Tanlang 👇"
    )
    markup = get_user_edit_markup(email)
    if edit_message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=edit_message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def send_add_user_template(bot: TeleBot, chat_id: int):
    """Yangi xodim qo'shish uchun nusxalanadigan shablon xabarini chiqaradi"""
    template_text = (
        "➕ *YANGI XODIM QO'SHISH SHABLONI*\n\n"
        "Quyidagi shablondan nusxa oling *(ustiga bossangiz avtomatik nusxalanadi)*, "
        "ma'lumotlarni to'ldiring va botga yuboring:\n\n"
        "`👤 F.I.SH: \n"
        "💼 Lavozimi: \n"
        "📧 Pochta manzili: \n"
        "📞 Telefon raqami: \n"
        "☎️ IP telefon: `\n\n"
        "💡 *Namunaviy to'ldirish:*\n"
        "`👤 F.I.SH: Eshmatov Toshmat Ali o'g'li\n"
        "💼 Lavozimi: Bosh muhandis\n"
        "📧 Pochta manzili: t.eshmatov@uz-potash.uz\n"
        "📞 Telefon raqami: +998901234567\n"
        "☎️ IP telefon: 105`\n\n"
        "❌ _Bekor qilish uchun /cancel deb yozing._"
    )
    return bot.send_message(chat_id, template_text, parse_mode="Markdown")

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

    # Admin xavfsizlik paroli va tahrirlash bosqichlari (Next step handlers)
    def handle_admin_auth_step(message: Message, on_success: str):
        user = message.from_user
        if (user.username or "").lower() != config.ADMIN_USERNAME.lower():
            return
        if not message.text:
            return
        text = message.text.strip()
        if text.lower() in ["/cancel", "cancel", "bekor", "ortga"]:
            bot.send_message(
                message.chat.id,
                "Admin amali bekor qilindi.",
                reply_markup=get_main_keyboard(get_user_lang(message.chat.id) or "uz")
            )
            return

        expected = getattr(config, "ADMIN_EDIT_PASSWORD", "")
        if text != expected:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔑 Qaytadan kiritish", callback_data="admin_edit_search"),
                InlineKeyboardButton("🔙 Admin menyusi", callback_data="admin_menu")
            )
            bot.send_message(
                message.chat.id,
                "❌ *Xavfsizlik paroli noto'g'ri!*\n\nXodim ma'lumotlarini o'zgartirishga ruxsat berilmadi.",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        # Parol to'g'ri kiritildi
        set_admin_authenticated(message.chat.id)
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        bot.send_message(
            message.chat.id,
            "🔓 *Xavfsizlik paroli tasdiqlandi!*\n_Xodim ma'lumotlarini tahrirlash seansi faollashtirildi._",
            parse_mode="Markdown"
        )

        if on_success == "search":
            msg = bot.send_message(
                message.chat.id,
                "🔍 *Xodimni qidirish:*\n\n"
                "Ma'lumotlarini o'zgartirmoqchi bo'lgan xodimning *ismi*, *familiyasi* yoki *email* manzilini yozing:\n"
                "_(Masalan: Javohir, bekzod yoki admin@uz-potash.uz)_\n\n"
                "❌ Bekor qilish uchun: /cancel",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, handle_admin_search_step)
        elif on_success == "add_user":
            msg = send_add_user_template(bot, message.chat.id)
            bot.register_next_step_handler(msg, handle_admin_add_user_step)
        elif on_success.startswith("user:"):
            target_email = on_success.split(":", 1)[1]
            u = data_manager.get_user_by_email(target_email)
            if u:
                send_user_edit_menu(bot, message.chat.id, u)
            else:
                bot.send_message(message.chat.id, "❌ Xodim topilmadi!")

    def handle_admin_search_step(message: Message):
        user = message.from_user
        if (user.username or "").lower() != config.ADMIN_USERNAME.lower():
            return
        if not message.text:
            return
        query = message.text.strip()
        if query.lower() in ["/cancel", "cancel", "bekor", "ortga"]:
            bot.send_message(
                message.chat.id,
                "Admin amali bekor qilindi.",
                reply_markup=get_main_keyboard(get_user_lang(message.chat.id) or "uz")
            )
            return

        found = data_manager.get_users(search=query)
        if not found:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔍 Qaytadan qidirish", callback_data="admin_edit_search"),
                InlineKeyboardButton("🔙 Admin menyusi", callback_data="admin_menu")
            )
            bot.send_message(
                message.chat.id,
                f"❌ *'{query}'* bo'yicha hech qanday xodim topilmadi.",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        markup = InlineKeyboardMarkup()
        for u in found[:10]:
            uname = u.get("name") or u.get("email", "").split("@")[0]
            uemail = u.get("email", "")
            markup.add(InlineKeyboardButton(f"👤 {uname} ({uemail})", callback_data=f"adm_usr:{uemail}"))

        markup.add(InlineKeyboardButton("🔙 Admin menyusiga qaytish", callback_data="admin_menu"))

        bot.send_message(
            message.chat.id,
            f"📋 *Topilgan xodimlar ({len(found)} ta):*\nTahrirlash uchun xodimni tanlang 👇",
            parse_mode="Markdown",
            reply_markup=markup
        )

    def handle_admin_add_user_step(message: Message):
        user = message.from_user
        if (user.username or "").lower() != config.ADMIN_USERNAME.lower():
            return
        if not message.text:
            return
        text = message.text.strip()
        if text.lower() in ["/cancel", "cancel", "bekor", "ortga"]:
            bot.send_message(
                message.chat.id,
                "Yangi xodim qo'shish bekor qilindi.",
                reply_markup=get_main_keyboard(get_user_lang(message.chat.id) or "uz")
            )
            return

        parsed = parse_employee_template(text)
        email = parsed.get("email", "").strip().lower()

        if not email:
            msg = bot.send_message(
                message.chat.id,
                "❌ *Pochta manzili (email) topilmadi!*\n\n"
                "Iltimos, shablondagi `📧 Pochta manzili:` qatorini to'liq kiriting (masalan: `xodim@uz-potash.uz`).\n\n"
                "Qaytadan to'ldirib yuboring yoki bekor qilish uchun /cancel deb yozing:",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, handle_admin_add_user_step)
            return

        name = parsed.get("name") or email.split("@")[0]
        pos = parsed.get("position") or "—"
        phone = parsed.get("phone") or "—"
        ip = parsed.get("ip_phone") or "—"

        data_manager.add_or_update_employee(
            name=name,
            email=email,
            position=pos,
            phone=phone,
            ip_phone=ip
        )
        set_admin_authenticated(message.chat.id)

        result_text = (
            f"✅ *YANGI XODIM MUVAFFAQIYATLI SAQLANDI!*\n\n"
            f"👤 *F.I.SH:* {name}\n"
            f"💼 *Lavozimi:* {pos}\n"
            f"📧 *Pochta manzili:* `{email}`\n"
            f"📞 *Telefon raqami:* `{phone}`\n"
            f"☎️ *IP telefon:* `{ip}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💾 *PostgreSQL bazasi*, *iRedAdmin web paneli* hamda *Bot kesh*ida ma'lumotlar darhol yangilandi."
        )
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Yana xodim qo'shish", callback_data="admin_add_user"),
            InlineKeyboardButton("🔙 Admin menyusi", callback_data="admin_menu")
        )
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown", reply_markup=markup)

    def handle_admin_update_field(message: Message, email: str, field_type: str):
        user = message.from_user
        if (user.username or "").lower() != config.ADMIN_USERNAME.lower():
            return
        if not message.text:
            return
        text = message.text.strip()
        if text.lower() in ["/cancel", "cancel", "bekor", "ortga"]:
            bot.send_message(message.chat.id, "Tahrirlash bekor qilindi.")
            u = data_manager.get_user_by_email(email)
            if u:
                send_user_edit_menu(bot, message.chat.id, u)
            return

        target_user = data_manager.get_user_by_email(email)
        if not target_user:
            bot.send_message(message.chat.id, "❌ Xodim topilmadi!")
            return

        curr_pos = target_user.get("position") or ""
        if curr_pos == "—":
            curr_pos = ""
        curr_ph = target_user.get("phone") or ""
        if curr_ph == "—":
            curr_ph = ""
        curr_ip = target_user.get("ip_phone") or ""
        if curr_ip == "—":
            curr_ip = ""

        if field_type == "pos":
            new_pos = text
            parts = [new_pos]
            if curr_ph:
                parts.append(curr_ph)
            if curr_ip:
                parts.append(curr_ip)
            new_raw = " / ".join(parts)
        elif field_type == "ph":
            new_ph = text
            parts = []
            if curr_pos:
                parts.append(curr_pos)
            parts.append(new_ph)
            if curr_ip:
                parts.append(curr_ip)
            new_raw = " / ".join(parts)
        elif field_type == "ip":
            new_ip = text
            parts = []
            if curr_pos:
                parts.append(curr_pos)
            if curr_ph:
                parts.append(curr_ph)
            parts.append(new_ip)
            new_raw = " / ".join(parts)
        elif field_type == "all":
            new_raw = text
        else:
            new_raw = text

        success = data_manager.update_user_employee_info(email, new_raw)
        u_name = target_user.get("name") or email

        if success:
            set_admin_authenticated(message.chat.id)
            bot.send_message(
                message.chat.id,
                f"✅ *Muvaffaqiyatli saqlandi!*\n\n"
                f"👤 Xodim: *{u_name}*\n"
                f"📝 Yangi ma'lumot: `{new_raw}`\n"
                f"💾 Server bazasi (PostgreSQL / iRedAdmin) va bot ma'lumotlari darhol yangilandi.",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"⚠️ Ma'lumot lokal keshda yangilandi, ammo server DB ga yozishda muammo yuz berdi.",
                parse_mode="Markdown"
            )

        updated_user = data_manager.get_user_by_email(email)
        if updated_user:
            send_user_edit_menu(bot, message.chat.id, updated_user)

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
        is_auth = is_admin_authenticated(message.chat.id)
        markup = get_admin_keyboard(is_auth=is_auth)
        session_status = "🔓 *Faol (Ochiq)*" if is_auth else "🔒 *Qulflangan (Parol talab qilinadi)*"

        admin_text = (
            f"👑 *BOSH ADMINISTRATOR PANELI*\n\n"
            f"Assalomu alaykum, *Javohir Hojibayev*!\n\n"
            f"📊 *Tizim holati:*\n"
            f"• Xodimlar soni: *{users_count}* nafar\n"
            f"• Pochta tizimi: `iRedMail ({config.MAIL_DOMAIN})`\n"
            f"• Tahrirlash seansi: {session_status}\n"
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
        if data == "admin_menu":
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            bot.answer_callback_query(call.id)
            bot.clear_step_handler_by_chat_id(chat_id)
            users_count = len(data_manager.get_users())
            is_auth = is_admin_authenticated(chat_id)
            session_status = "🔓 *Faol (Ochiq)*" if is_auth else "🔒 *Qulflangan (Parol talab qilinadi)*"
            admin_text = (
                f"👑 *BOSH ADMINISTRATOR PANELI*\n\n"
                f"Assalomu alaykum, *Javohir Hojibayev*!\n\n"
                f"📊 *Tizim holati:*\n"
                f"• Xodimlar soni: *{users_count}* nafar\n"
                f"• Pochta tizimi: `iRedMail ({config.MAIL_DOMAIN})`\n"
                f"• Tahrirlash seansi: {session_status}\n"
                f"• Auto-Sync: *Faol (har 5 daqiqada)*\n"
                f"• Bot holati: *Online*\n\n"
                f"Kerakli amalni tanlang 👇"
            )
            try:
                bot.edit_message_text(
                    admin_text,
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=get_admin_keyboard(is_auth=is_auth)
                )
            except Exception:
                bot.send_message(chat_id, admin_text, parse_mode="Markdown", reply_markup=get_admin_keyboard(is_auth=is_auth))
            return

        if data == "admin_lock":
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            clear_admin_auth(chat_id)
            bot.answer_callback_query(call.id, "🔒 Tahrirlash seansi qulflandi!")
            users_count = len(data_manager.get_users())
            admin_text = (
                f"👑 *BOSH ADMINISTRATOR PANELI*\n\n"
                f"Assalomu alaykum, *Javohir Hojibayev*!\n\n"
                f"🔒 *Tahrirlash seansi qulflandi.* Ma'lumotlarni o'zgartirish uchun parol talab qilinadi.\n\n"
                f"📊 *Tizim holati:*\n"
                f"• Xodimlar soni: *{users_count}* nafar\n"
                f"• Pochta tizimi: `iRedMail ({config.MAIL_DOMAIN})`\n"
                f"• Tahrirlash seansi: 🔒 *Qulflangan*\n"
                f"• Auto-Sync: *Faol (har 5 daqiqada)*\n"
                f"• Bot holati: *Online*\n\n"
                f"Kerakli amalni tanlang 👇"
            )
            try:
                bot.edit_message_text(
                    admin_text,
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=get_admin_keyboard(is_auth=False)
                )
            except Exception:
                bot.send_message(chat_id, admin_text, parse_mode="Markdown", reply_markup=get_admin_keyboard(is_auth=False))
            return

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
                f"• Boshqaruv bazasi: `PostgreSQL (vmail)`\n"
                f"• Sinxronizatsiya: *Faol*\n"
                f"• Bosh administrator: *@Javohir_Hojibayev*",
                parse_mode="Markdown"
            )
            return

        if data in ["admin_add_user", "admin_edit_search"]:
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            bot.answer_callback_query(call.id)
            bot.clear_step_handler_by_chat_id(chat_id)

            if not is_admin_authenticated(chat_id):
                action_text = "Yangi xodim qo'shish" if data == "admin_add_user" else "Xodim ma'lumotlarini o'zgartirish"
                next_action = "add_user" if data == "admin_add_user" else "search"
                msg = bot.send_message(
                    chat_id,
                    f"🔐 *XAVFSIZLIK TEKSHIRUVI:*\n\n"
                    f"{action_text} uchun *xavfsizlik paroli*ni kiriting:\n\n"
                    f"❌ Bekor qilish uchun: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_auth_step(m, on_success=next_action))
                return

            if data == "admin_add_user":
                msg = send_add_user_template(bot, chat_id)
                bot.register_next_step_handler(msg, handle_admin_add_user_step)
            else:
                msg = bot.send_message(
                    chat_id,
                    "🔍 *Xodimni qidirish:*\n\n"
                    "Ma'lumotlarini o'zgartirmoqchi bo'lgan xodimning *ismi*, *familiyasi* yoki *email* manzilini yozing:\n"
                    "_(Masalan: Javohir, bekzod yoki admin@uz-potash.uz)_\n\n"
                    "❌ Bekor qilish uchun: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, handle_admin_search_step)
            return

        if data.startswith("adm_usr:"):
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            email = data.split(":", 1)[1]
            user = data_manager.get_user_by_email(email)
            if not user:
                bot.answer_callback_query(call.id, "Xodim topilmadi!", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            bot.clear_step_handler_by_chat_id(chat_id)

            if not is_admin_authenticated(chat_id):
                u_name = user.get("name") or email
                msg = bot.send_message(
                    chat_id,
                    "🔐 *XAVFSIZLIK TEKSHIRUVI:*\n\n"
                    f"*{u_name}* ma'lumotlarini tahrirlash uchun *xavfsizlik paroli*ni kiriting:\n\n"
                    "❌ Bekor qilish uchun: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_auth_step(m, on_success=f"user:{email}"))
                return

            send_user_edit_menu(bot, chat_id, user, edit_message_id=call.message.message_id)
            return

        if data.startswith("adm_ed:"):
            if (call.from_user.username or "").lower() != config.ADMIN_USERNAME.lower():
                bot.answer_callback_query(call.id, "Ruxsat yo'q!")
                return
            parts = data.split(":")
            action = parts[1]
            email = parts[2]
            user = data_manager.get_user_by_email(email)
            if not user:
                bot.answer_callback_query(call.id, "Xodim topilmadi!", show_alert=True)
                return

            u_name = user.get("name") or email
            bot.clear_step_handler_by_chat_id(chat_id)

            if not is_admin_authenticated(chat_id):
                bot.answer_callback_query(call.id, "🔐 Parol talab qilinadi!", show_alert=True)
                msg = bot.send_message(
                    chat_id,
                    "🔐 *Xavfsizlik paroli talab qilinadi!*\n\nXodim ma'lumotlarini o'zgartirish uchun parolni kiriting:\n\n❌ Bekor qilish: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_auth_step(m, on_success=f"user:{email}"))
                return

            if action == "clear":
                bot.answer_callback_query(call.id, "Tozalanmoqda...")
                data_manager.update_user_employee_info(email, "")
                updated = data_manager.get_user_by_email(email)
                bot.send_message(chat_id, f"🗑 *{u_name}* ma'lumotlari tozalandi va server bazasida bo'shatildi.", parse_mode="Markdown")
                send_user_edit_menu(bot, chat_id, updated)
                return

            bot.answer_callback_query(call.id)

            if action == "pos":
                msg = bot.send_message(
                    chat_id,
                    f"💼 *{u_name}* uchun yangi *lavozim* nomini kiriting:\n_(Masalan: Bosh mutaxassis)_\n\n❌ Bekor qilish: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_update_field(m, email, "pos"))
            elif action == "ph":
                msg = bot.send_message(
                    chat_id,
                    f"📞 *{u_name}* uchun yangi *telefon raqami*ni kiriting:\n_(Masalan: +998901234567)_\n\n❌ Bekor qilish: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_update_field(m, email, "ph"))
            elif action == "ip":
                msg = bot.send_message(
                    chat_id,
                    f"☎️ *{u_name}* uchun yangi *IP telefon* raqamini kiriting:\n_(Masalan: 105 yoki 241)_\n\n❌ Bekor qilish: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_update_field(m, email, "ip"))
            elif action == "all":
                msg = bot.send_message(
                    chat_id,
                    f"📝 *{u_name}* uchun ma'lumotlarni bir qatorda kiriting:\n"
                    f"Format: `Lavozim / Telefon / IP telefon`\n\n"
                    f"_(Ajratish uchun /, @, #, $, % belgilaridan foydalanishingiz mumkin)_\n"
                    f"Masalan:\n`Bosh energetik / +998901234567 / 105`\n\n"
                    f"❌ Bekor qilish: /cancel",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, lambda m: handle_admin_update_field(m, email, "all"))
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
            # Admin uchun qulay tezkor tahrirlash tugmasi
            if (message.from_user.username or "").lower() == config.ADMIN_USERNAME.lower():
                markup.add(
                    InlineKeyboardButton("✏️ Tahrirlash (Admin)", callback_data=f"adm_usr:{user.get('email')}")
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
