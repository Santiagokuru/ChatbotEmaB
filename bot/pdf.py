from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from bot.models import ClientInfo, Item

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle("QuoteTitle", parent=_styles["Heading1"], fontSize=18)
_heading_style = ParagraphStyle("QuoteHeading", parent=_styles["Heading2"], fontSize=12)
_normal_style = _styles["Normal"]


def build_quote_pdf(business: dict, client: ClientInfo, items: list[Item], total: float) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

    story = [
        Paragraph(business.get("name") or "Cotización", _title_style),
        Paragraph(
            " · ".join(filter(None, [business.get("phone"), business.get("email"), business.get("address")])),
            _normal_style,
        ),
        Spacer(1, 10 * mm),
        Paragraph(f"Fecha: {datetime.now():%d/%m/%Y}", _normal_style),
        Paragraph("Cliente", _heading_style),
        Paragraph(client.name, _normal_style),
    ]
    if client.contact:
        story.append(Paragraph(client.contact, _normal_style))
    story.append(Spacer(1, 8 * mm))

    table_data = [["Ítem", "Cantidad", "Precio unit.", "Subtotal"]]
    for item in items:
        table_data.append(
            [item.name, f"{item.quantity:g}", f"${item.unit_price:,.2f}", f"${item.subtotal:,.2f}"]
        )
    table_data.append(["", "", "Total", f"${total:,.2f}"])

    table = Table(table_data, colWidths=[80 * mm, 25 * mm, 35 * mm, 35 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b2b2b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
