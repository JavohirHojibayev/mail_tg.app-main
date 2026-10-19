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
