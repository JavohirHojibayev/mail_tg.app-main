import os
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import datetime

# Unicode qo'llab-quvvatlash uchun shriftlar
FONT_NAME = 'Helvetica'
FONT_NAME_BOLD = 'Helvetica-Bold'

for font_path, bold_path in [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('CustomUnicode', font_path))
            FONT_NAME = 'CustomUnicode'
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('CustomUnicode-Bold', bold_path))
                FONT_NAME_BOLD = 'CustomUnicode-Bold'
            else:
                FONT_NAME_BOLD = 'CustomUnicode'
            break
        except Exception:
            pass

def generate_employees_pdf(users: list, output_path: str = None, title: str = "DKZ AJ mail xodimlar ro'yxati") -> str:
    """
    PDF sarlavhasida berilgan sarlavha va xodim nomi, lavozimi, pochta manzili,
    telefon raqami hamda IP telefonidan iborat rasmiy jadval bo'ladi.
    """
    if not output_path:
        output_dir = Path(__file__).resolve().parent.parent / "generated_docs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "DKZ_AJ_qidiruv" if "Qidiruv" in title or "Поиск" in title else "DKZ_AJ_mail_xodimlar_royxati"
        output_path = str(output_dir / f"{prefix}_{timestamp}.pdf")

    # Albom (Landscape) formatda A4
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=35,
        rightMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()

    # Sarlavha stili
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName=FONT_NAME_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0B3954"),
        alignment=1, # Center
        spaceAfter=15
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1A202C")
    )

    pos_cell_style = ParagraphStyle(
        'PosCellText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2D3748")
    )

    email_cell_style = ParagraphStyle(
        'EmailCellText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0052CC")
    )

    phone_cell_style = ParagraphStyle(
        'PhoneCellText',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1A202C")
    )

    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName=FONT_NAME_BOLD,
        fontSize=9.5,
        leading=13,
        textColor=colors.white,
        alignment=1 # Center
    )

    num_cell_style = ParagraphStyle(
        'NumCell',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
        alignment=1 # Center
    )

    elements = []

    # Sarlavha
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 10))

    # Jadval: №, Xodim F.I.SH, Lavozimi, Korporativ Pochta, Telefon raqami, IP telefon
    table_data = [
        [
            Paragraph("<b>№</b>", header_cell_style),
            Paragraph("<b>Xodimning F.I.SH (Nomi)</b>", header_cell_style),
            Paragraph("<b>Lavozimi</b>", header_cell_style),
            Paragraph("<b>Korporativ Pochta Manzili</b>", header_cell_style),
            Paragraph("<b>Telefon raqami</b>", header_cell_style),
            Paragraph("<b>IP telefon</b>", header_cell_style),
        ]
    ]

    for idx, u in enumerate(users, start=1):
        name = u.get("name") or u.get("email", "").split("@")[0]
        pos = u.get("position", "—")
        email = u.get("email", "")
        phone = u.get("phone", "—")
        ip_phone = u.get("ip_phone", "—")

        table_data.append([
            Paragraph(str(idx), num_cell_style),
            Paragraph(f"<b>{name}</b>", cell_style),
            Paragraph(pos, pos_cell_style),
            Paragraph(f"<b>{email}</b>", email_cell_style),
            Paragraph(phone, phone_cell_style),
            Paragraph(ip_phone, phone_cell_style),
        ])

    # Ustun kengliklari (A4 Landscape = 842 pt; 770 pt jadval uchun)
    col_widths = [30, 185, 160, 185, 120, 80]

    emp_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0B3954")),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
        ('TOPPADDING', (0, 0), (-1, 0), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))

    elements.append(emp_table)
    doc.build(elements)
    return output_path

