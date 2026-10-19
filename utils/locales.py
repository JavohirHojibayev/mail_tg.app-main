"""
Ko'p tilli (Multi-language) lokalizatsiya moduli.
Faqat O'zbek (uz) va Rus (ru) tillari qo'llab-quvvatlanadi.
"""

LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
}

TEXTS = {
    "uz": {
        "select_lang_prompt": (
            "🌐 *Iltimos, interfeys tilini tanlang / Пожалуйста, выберите язык интерфейса:*\n\n"
            "⚠️ _Botdan foydalanish uchun 2 tildan birini tanlashingiz lozim:_\n"
            "_Для работы с ботом необходимо выбрать один из 2 языков:_"
        ),
        "lang_selected_confirm": "✅ Interfeys tili muvaffaqiyatli o'rnatildi: *O'zbek tili*",
        "btn_list": "📋 Xodimlar ro'yxati",
        "btn_search": "🔍 Qidirish",
        "btn_pdf": "📥 PDF yuklab olish",
        "btn_help": "ℹ️ Yordam",
        "btn_lang": "🌐 Til / Язык",
        "start_text": (
            "👋 *Assalomu alaykum!*\n\n"
            "Bu *DKZ AJ* korporativ pochta xodimlari ma'lumotnoma boti (`uz-potash.uz`).\n\n"
            "📊 Tizimda jami: *{count}* nafar xodim pochtasi mavjud.\n\n"
            "📋 *Xodimlar ro'yxati:* 10 tadan sahifalangan holda xodimlar nomi va pochtasini ko'rish.\n"
            "🔍 *Tezkor qidiruv:* Xodim ismini lotin yoki krill, katta yoki kichik harflarda yozib yuboring.\n"
            "_Misol: `Javohir`, `Hojibayev`, `javohir hojibayev`, `жавоҳир ҳожибаев`..._\n\n"
            "Quyidagi menyu tugmalaridan birini tanlang 👇"
        ),
        "help_text": (
            "📖 *QO'LLANMA VA YORDAM*\n\n"
            "🔹 *Xodimlar ro'yxati:* «📋 Xodimlar ro'yxati» yoki /list — xodimlarni 10 tadan sahifalab ko'rish.\n"
            "🔹 *PDF Export:* «📥 PDF yuklab olish» yoki /pdf — rasmiy PDF hujjatni yuklab olish.\n"
            "🔹 *Qidirish:* Xodim ismini to'g'ridan-to'g'ri yozing (Lotin va Krill yozuvlariga to'liq moslashgan).\n"
            "🔹 *Tilni almashtirish:* «🌐 Til / Язык» tugmasi yoki /lang komandasi.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📩 *YANGI POCHTA OCHISH:*\n"
            "Yangi korporativ pochta ochish yoki texnik murojaatlar uchun mas'ul mutaxassislarga bog'laning:\n\n"
            "1. 👑 *Javohir Hojibayev* _(Bosh administrator)_\n"
            "   ✈️ Telegram: [@Javohir_Hojibayev](https://t.me/Javohir_Hojibayev)\n"
            "   📞 Telefon: `+998 94 542 41 21`\n\n"
            "2. 👤 *Nurbek Jumayev*\n"
            "   ✈️ Telegram: [@nurbekjumayev](https://t.me/nurbekjumayev)\n"
            "   📞 Telefon: `+998 94 175 86 52`\n\n"
            "🌐 *Rasmiy pochta domeni:* `@uz-potash.uz`"
        ),
        "search_prompt": (
            "🔍 Qidirmoqchi bo'lgan xodimning ismini yozing:\n"
            "_(Lotin yoki Krill, katta yoki kichik harflarda yozishingiz mumkin)_\n\n"
            "Misol: `Javohir`, `Hojibayev`, `javohir hojibayev`, `жавоҳир ҳожибаев`..."
        ),
        "pagination_header": "📋 *DKZ AJ XODIMLAR RO'YXATI*",
        "pagination_page_info": "📊 _Sahifa: {page} / {total_pages} (Jami: {total_users} nafar)_\n",
        "pagination_footer": "💡 _Pochta manzilini nusxalash uchun ustiga bosing._",
        "btn_prev": "⬅️ Oldingi",
        "btn_next": "Keyingi ➡️",
        "btn_export_all_pdf": "📥 Barchasini .PDF yuklab olish ({total_users} nafar)",
        "btn_results_pdf": "📥 Natijalarni .PDF yuklab olish",
        "user_card": (
            "👤 *F.I.SH:* {name}\n"
            "💼 *Lavozimi:* {position}\n"
            "📧 *Pochta manzili:* `{email}`\n"
            "📞 *Telefon raqami:* `{phone}`\n"
            "☎️ *IP telefon:* `{ip_phone}`\n\n"
            "👉 _Nusxalash uchun kerakli ma'lumot ustiga bosing_"
        ),
        "search_found_single": "✅ *Xodim topildi:*\n\n",
        "search_found_multiple": "🔍 *\"{query}\"* bo'yicha {count} ta xodim topildi:\n\n",
        "search_not_found": (
            "🔍 *\"{query}\"* bo'yicha hech qanday xodim topilmadi.\n\n"
            "💡 Ismni boshqacha yozib ko'ring yoki barcha xodimlarni ko'ring: /list"
        ),
        "pdf_wait": "⏳ *PDF hujjat tayyorlanmoqda, kuting...*",
        "pdf_caption": (
            "📄 *DKZ AJ xodimlar ma'lumotlari*\n\n"
            "👥 Jami: *{count}* nafar xodim\n"
            "🌐 Rasmiy domen: `@uz-potash.uz`"
        ),
        "pdf_search_caption": (
            "📄 *Qidiruv natijalari bo'yicha ma'lumotnoma*\n\n"
            "🔍 Qidiruv: *\"{query}\"*\n"
            "👥 Topilgan xodimlar: *{count}* nafar\n"
            "🌐 Rasmiy domen: `@uz-potash.uz`"
        ),
        "contact_javohir": "💬 Javohir Hojibayev (Telegram)",
        "contact_nurbek": "💬 Nurbek Jumayev (Telegram)",
        "cmd_list": "📋 Xodimlar ro'yxati (10 tadan)",
        "cmd_pdf": "📥 Ro'yxatni PDF yuklab olish",
        "cmd_search": "🔍 Xodim qidirish",
        "cmd_start": "🔄 Asosiy menyu",
        "cmd_help": "ℹ️ Yordam va kontaktlar",
        "cmd_lang": "🌐 Tilni tanlash / Выбрать язык",
        "cmd_sync": "🔄 Serverdan yangilash (Admin)",
        "sync_wait": "⏳ *Server bilan sinxronizatsiya qilinmoqda, kuting...*",
        "sync_success": "✅ *Server bilan sinxronizatsiya yakunlandi!*\n📊 Jami xodimlar: *{total}* nafar\n🔄 Yangilanganlar: *{updated}* ta",

    },
    "ru": {
        "select_lang_prompt": (
            "🌐 *Пожалуйста, выберите язык интерфейса / Iltimos, interfeys tilini tanlang:*\n\n"
            "⚠️ _Для работы с ботом необходимо выбрать один из 2 языков:_\n"
            "_Botdan foydalanish uchun 2 tildan birini tanlashingiz lozim:_"
        ),
        "lang_selected_confirm": "✅ Язык интерфейса успешно установлен: *Русский*",
        "btn_list": "📋 Список сотрудников",
        "btn_search": "🔍 Поиск",
        "btn_pdf": "📥 Скачать PDF",
        "btn_help": "ℹ️ Помощь",
        "btn_lang": "🌐 Язык / Til",
        "start_text": (
            "👋 *Здравствуйте!*\n\n"
            "Это официальный справочный Telegram-бот корпоративной почты *АО «ДКЗ»* (`uz-potash.uz`).\n\n"
            "📊 Всего в системе: *{count}* адресов сотрудников.\n\n"
            "📋 *Список сотрудников:* Просмотр списка по 10 человек с постраничной навигацией.\n"
            "🔍 *Быстрый поиск:* Отправьте имя сотрудника латиницей или кириллицей.\n"
            "_Пример: `Javohir`, `Hojibayev`, `javohir hojibayev`, `жавоҳир ҳожибаев`..._\n\n"
            "Выберите нужный раздел из меню ниже 👇"
        ),
        "help_text": (
            "📖 *СПРАВКА И ПОДДЕРЖКА*\n\n"
            "🔹 *Список сотрудников:* Нажмите «📋 Список сотрудников» или команду /list — постраничный просмотр по 10 записей.\n"
            "🔹 *Экспорт в PDF:* Нажмите «📥 Скачать PDF» или команду /pdf — скачать официальный PDF-документ.\n"
            "🔹 *Поиск:* Напишите имя или фамилию (поддерживаются латиница, кириллица, о/а).\n"
            "🔹 *Смена языка:* Нажмите «🌐 Язык / Til» или команду /lang.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📩 *ОТКРЫТИЕ НОВОЙ КОРПОРАТИВНОЙ ПОЧТЫ:*\n"
            "Для открытия нового почтового ящика или по техническим вопросам обращайтесь к ответственным специалистам:\n\n"
            "1. 👑 *Javohir Hojibayev* _(Главный администратор)_\n"
            "   ✈️ Telegram: [@Javohir_Hojibayev](https://t.me/Javohir_Hojibayev)\n"
            "   📞 Телефон: `+998 94 542 41 21`\n\n"
            "2. 👤 *Nurbek Jumayev*\n"
            "   ✈️ Telegram: [@nurbekjumayev](https://t.me/nurbekjumayev)\n"
            "   📞 Телефон: `+998 94 175 86 52`\n\n"
            "🌐 *Официальный почтовый домен:* `@uz-potash.uz`"
        ),
        "search_prompt": (
            "🔍 Введите имя или фамилию сотрудника для поиска:\n"
            "_(Можно писать на латинице или кириллице, строчными или заглавными буквами)_\n\n"
            "Пример: `Javohir`, `Hojibayev`, `javohir hojibayev`, `жавоҳир ҳожибаев`..."
        ),
        "pagination_header": "📋 *СПИСОК СОТРУДНИКОВ АО «ДКЗ»*",
        "pagination_page_info": "📊 _Страница: {page} / {total_pages} (Всего: {total_users} чел.)_\n",
        "pagination_footer": "💡 _Нажмите на адрес электронной почты для копирования._",
        "btn_prev": "⬅️ Назад",
        "btn_next": "Вперед ➡️",
        "btn_export_all_pdf": "📥 Скачать всё в .PDF ({total_users} чел.)",
        "btn_results_pdf": "📥 Скачать результаты в .PDF",
        "user_card": (
            "👤 *Ф.И.О:* {name}\n"
            "💼 *Должность:* {position}\n"
            "📧 *Эл. почта:* `{email}`\n"
            "📞 *Номер телефона:* `{phone}`\n"
            "☎️ *IP-телефон:* `{ip_phone}`\n\n"
            "👉 _Нажмите на нужное поле для копирования_"
        ),
        "search_found_single": "✅ *Сотрудник найден:*\n\n",
        "search_found_multiple": "🔍 По запросу *\"{query}\"* найдено {count} сотрудников:\n\n",
        "search_not_found": (
            "🔍 По запросу *\"{query}\"* сотрудники не найдены.\n\n"
            "💡 Попробуйте ввести имя иначе или посмотрите полный список: /list"
        ),
        "pdf_wait": "⏳ *PDF документ формируется, пожалуйста подождите...*",
        "pdf_caption": (
            "📄 *Информация о сотрудниках АО «ДКЗ»*\n\n"
            "👥 Всего сотрудников: *{count}*\n"
            "🌐 Официальный домен: `@uz-potash.uz`"
        ),
        "pdf_search_caption": (
            "📄 *Справка по результатам поиска*\n\n"
            "🔍 Запрос: *\"{query}\"*\n"
            "👥 Найдено сотрудников: *{count}*\n"
            "🌐 Официальный домен: `@uz-potash.uz`"
        ),
        "contact_javohir": "💬 Javohir Hojibayev (Telegram)",
        "contact_nurbek": "💬 Nurbek Jumayev (Telegram)",
        "cmd_list": "📋 Список сотрудников (по 10 чел.)",
        "cmd_pdf": "📥 Скачать список в PDF",
        "cmd_search": "🔍 Поиск сотрудника",
        "cmd_start": "🔄 Главное меню",
        "cmd_help": "ℹ️ Помощь и контакты",
        "cmd_lang": "🌐 Выбрать язык / Tilni tanlash",
        "cmd_sync": "🔄 Синхронизация с сервером (Админ)",
        "sync_wait": "⏳ *Выполняется синхронизация с сервером, подождите...*",
        "sync_success": "✅ *Синхронизация с сервером успешно завершена!*\n📊 Всего сотрудников: *{total}* чел.\n🔄 Обновлено: *{updated}*",
    }
}

def t(key: str, lang: str = "uz", **kwargs) -> str:
    """Belgilangan til bo'yicha matnni qaytaradi (standart 'uz')"""
    if lang not in TEXTS:
        lang = "uz"
    template = TEXTS[lang].get(key, TEXTS["uz"].get(key, ""))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
