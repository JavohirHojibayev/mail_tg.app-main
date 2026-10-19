# 📬 UZ-Potash Mail Bot

**UZ-Potash (DKZ AJ)** korporativ pochta xodimlari ma'lumotnomasi va qidiruv tizimi uchun Telegram bot (`@dkzmail_bot`).

---

## ⚡ Asosiy Imkoniyatlar

- 🔍 **Aqlli Qidiruv** — Ism va familiya bo'yicha tezkor qidiruv (Lotin va Krill yozuvlariga to'liq moslashgan).
- 📄 **PDF Eksport** — Barcha xodimlar va pochta manzillarini rasmiy PDF jadval ko'rinishida yuklab olish.
- 🌐 **Ko'p Tilli Interfeys** — O'zbek va Rus tillarini qo'llab-quvvatlash (`UZ` / `RU`).
- 🔄 **Avto-Sinxronizatsiya** — Server bazasi (PostgreSQL / vmail) bilan fonda avtomatik sinxronlash va kesh tizimi.

---

## 🚀 Tezkor Boshlash

### 1. O'rnatish
```bash
pip install -r requirements.txt
```

### 2. Sozlash
`.env.example` dan nusxa olib `.env` faylini yarating va kerakli token hamda ulanish parametrlarini kiriting:
```bash
cp .env.example .env    # Linux
copy .env.example .env  # Windows
```

### 3. Ishga tushirish
```bash
python bot.py
```
*(Windows foydalanuvchilari uchun `run_bot.bat` skripti ham mavjud).*

---

## 📌 Asosiy Buyruqlar

| Buyruq | Tavsif |
|---|---|
| `/start` | Botni ishga tushirish va til tanlash |
| `/list` | Xodimlar ro'yxatini sahifalab ko'rish (10 tadan) |
| `/search` | Xodim ismi yoki emaili bo'yicha qidiruv |
| `/pdf` | Xodimlar ro'yxatini PDF formatda yuklab olish |
| `/lang` | Interfeys tilini almashtirish |
| `/help` | Texnik yordam va ma'muriyat bilan bog'lanish |

---

## 👨‍💻 Ma'muriyat
Savollar yoki yangi korporativ pochta ochish bo'yicha:
- **Javohir Hojibayev** — [@Javohir_Hojibayev](https://t.me/Javohir_Hojibayev)
