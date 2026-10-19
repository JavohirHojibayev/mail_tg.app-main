"""
Xodimning 'User/Employee ID' maydonidan lavozim, telefon va IP telefon ma'lumotlarini
ajratib olish (parse) moduli.

Qo'llab-quvvatlanadigan ajratuvchi belgilar:
  /   @   #   $   %   |

Belgilardan oldin va keyin istalgancha probellar bo'lishi mumkin.
Misollar:
 - Muhandis-dasturchi/+998945424121
 - Muhandis-dasturchi / +998945424121
 - Muhandis-dasturchi @ +998945424121
 - Muhandis-dasturchi # +998945424121
 - Muhandis-dasturchi $ +998945424121
 - Muhandis-dasturchi % +998945424121
 - Muhandis-dasturchi / +998945424121 / 102
 - Bosh bugalter/+998945424121/+9989701849299
 - Bosh energetik (faqat lavozim)
"""
import re

def parse_employee_id(raw_str: str) -> dict:
    if not raw_str or not str(raw_str).strip():
        return {
            "position": "—",
            "phone": "—",
            "ip_phone": "—",
            "raw_info": ""
        }
    
    clean = str(raw_str).strip()
    
    # Har qanday belgilangan ajratuvchilar: / @ # $ % | va ularning atrofidagi probellar
    parts = [p.strip() for p in re.split(r'\s*[/@#$%|]+\s*', clean) if p.strip()]
    
    if not parts:
        return {
            "position": "—",
            "phone": "—",
            "ip_phone": "—",
            "raw_info": clean
        }
        
    position = parts[0]
    phone = "—"
    ip_phone = "—"
    
    if len(parts) == 2:
        val = parts[1]
        # Agar 2-4 ta raqamdan iborat qisqa son bo'lsa (masalan 102, 204), bu IP telefon
        digits_only = re.sub(r'\D', '', val)
        if len(digits_only) <= 4 and not val.startswith('+'):
            ip_phone = val
        else:
            phone = val
    elif len(parts) >= 3:
        phone = parts[1]
        ip_phone = parts[2]
        
    return {
        "position": position,
        "phone": phone,
        "ip_phone": ip_phone,
        "raw_info": clean
    }

def parse_employee_template(text: str) -> dict:
    """
    Foydalanuvchi yuborgan shablon matnidan xodim ma'lumotlarini ajratib oladi:
    👤 F.I.SH: Eshmatov Toshmat
    💼 Lavozimi: Bosh muhandis
    📧 Pochta manzili: t.eshmatov@uz-potash.uz
    📞 Telefon raqami: +998901234567
    ☎️ IP telefon: 105
    """
    res = {
        "name": "",
        "position": "",
        "email": "",
        "phone": "",
        "ip_phone": ""
    }
    if not text:
        return res

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    for line in lines:
        clean_line = re.sub(r'^[👤💼📧📞☎️\*\-_•\s]+', '', line).strip()
        if ':' in clean_line:
            key, val = clean_line.split(':', 1)
            key_lower = key.strip().lower()
            val_clean = val.strip()

            if any(k in key_lower for k in ['f.i.sh', 'fish', 'ism', 'fio', 'name']):
                res['name'] = val_clean
            elif any(k in key_lower for k in ['lavozim', 'position', 'mutaxassis']):
                res['position'] = val_clean
            elif any(k in key_lower for k in ['pochta', 'email', 'mail']):
                res['email'] = val_clean
            elif any(k in key_lower for k in ['ip', 'ichki']):
                res['ip_phone'] = val_clean
            elif any(k in key_lower for k in ['telefon', 'tel', 'phone', 'mobil', 'aloqa']):
                res['phone'] = val_clean

    # Agar email qatorida topilmagan bo'lsa, butun matndan email qidiramiz
    if not res['email']:
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
        if email_match:
            res['email'] = email_match.group(0).strip()

    # Agar email domenisiz kiritilgan bo'lsa (masalan t.eshmatov)
    if res['email'] and '@' not in res['email']:
        res['email'] = f"{res['email']}@uz-potash.uz"

    return res

