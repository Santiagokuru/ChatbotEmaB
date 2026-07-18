import re
import unicodedata
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from bot.models import ClientInfo, Item

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle("QuoteTitle", parent=_styles["Heading1"], fontSize=18)
_heading_style = ParagraphStyle("QuoteHeading", parent=_styles["Heading2"], fontSize=12)
_normal_style = _styles["Normal"]
_presupuesto_style = ParagraphStyle(
    "PresupuestoLabel", parent=_styles["Heading1"], fontSize=20, alignment=TA_RIGHT
)
_quote_number_style = ParagraphStyle(
    "QuoteNumber", parent=_normal_style, fontSize=11, alignment=TA_RIGHT
)
_farewell_style = ParagraphStyle(
    "Farewell", parent=_normal_style, fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor("#555555")
)

_FIXED_INTRO = (
    "En respuesta al pedido de cotización de sistema de seguridad para el domicilio del solicitante "
    "se cotiza la siguiente propuesta."
)
_FIXED_PAYMENT_TERMS = (
    "50% de entrega al concretar la obra y el saldo al finalizar el trabajo."
)
_FIXED_FAREWELL = (
    "Como es conocido, hace más de 30 años que se prestan servicios de seguridad y se brindan "
    "soluciones de ingeniería integral en esta ciudad y localidades vecinas lo que demuestra "
    "continuidad, reserva y compromiso permanente con nuestros clientes."
)

_CAMERA_KEYWORDS = ["camara", "cam"]
_ALARM_KEYWORDS = ["alarma", "sensor", "central", "sirena", "teclado", "panel", "detector", "x-28", "x28"]
_CAMERA_WARRANTY = "La marca de las cámaras presupuestadas es Imou de Dahua y tienen 2 años de garantía."
_ALARM_WARRANTY = "La marca de los equipos es X-28 y tiene 5 años de garantía."
_INCLUDES_LABOR = (
    "Todos los valores cotizados incluyen tanto mano de obra como los accesorios necesarios "
    "para la instalación."
)


def format_quote_number(prefix: str, quote_number: int) -> str:
    number = f"{quote_number:06d}"
    return f"{prefix}-{number}" if prefix else number


def _normalize(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return stripped.lower()


def _matches_any(text: str, keywords: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)


def _warranty_lines(items: list[Item]) -> list[str]:
    normalized_names = [_normalize(item.name) for item in items]
    lines = []
    if any(_matches_any(name, _CAMERA_KEYWORDS) for name in normalized_names):
        lines.append(_CAMERA_WARRANTY)
    if any(_matches_any(name, _ALARM_KEYWORDS) for name in normalized_names):
        lines.append(_ALARM_WARRANTY)
    return lines


def _logo_flowable(logo_path: str, max_width: float = 45 * mm, max_height: float = 25 * mm):
    if not logo_path:
        return None
    try:
        reader = ImageReader(logo_path)
        iw, ih = reader.getSize()
        scale = min(max_width / iw, max_height / ih)
        return Image(logo_path, width=iw * scale, height=ih * scale)
    except Exception:
        return None


def build_quote_pdf(
    business: dict,
    client: ClientInfo,
    items: list[Item],
    total: float,
    quote_number: int,
    estimated_time: str = "",
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

    issue_date = datetime.now()
    due_date = issue_date + timedelta(days=business.get("validity_days", 15))

    logo = _logo_flowable(business.get("logo_path", "")) or Paragraph(
        business.get("name") or "Cotización", _title_style
    )
    header_right = [
        Paragraph("PRESUPUESTO", _presupuesto_style),
        Paragraph(f"N° {format_quote_number(business.get('quote_prefix', ''), quote_number)}", _quote_number_style),
    ]
    header_table = Table([[logo, header_right]], colWidths=[90 * mm, 80 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    dates_lines = [
        f"Fecha de emisión: {issue_date:%d/%m/%Y}",
        f"Fecha de validez: {due_date:%d/%m/%Y}",
    ]
    contact_lines = list(
        filter(
            None,
            [
                f"Teléfono: {business['phone']}" if business.get("phone") else None,
                f"Email: {business['email']}" if business.get("email") else None,
            ],
        )
    )
    payment_lines = list(
        filter(
            None,
            [
                f"Cuenta: {business['bank_account']}" if business.get("bank_account") else None,
                f"Alias: {business['bank_alias']}" if business.get("bank_alias") else None,
            ],
        )
    )
    info_table = Table(
        [
            [
                Paragraph("<br/>".join(dates_lines), _normal_style),
                Paragraph("<br/>".join(contact_lines) or "", _normal_style),
                Paragraph("<br/>".join(payment_lines) or "", _normal_style),
            ]
        ],
        colWidths=[55 * mm, 55 * mm, 60 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [
        header_table,
        Spacer(1, 8 * mm),
        Paragraph("Cliente", _heading_style),
        Paragraph(client.name, _normal_style),
    ]
    if client.contact:
        story.append(Paragraph(client.contact, _normal_style))
    story.append(Spacer(1, 6 * mm))
    story.append(info_table)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(_FIXED_INTRO, _normal_style))
    story.append(Spacer(1, 6 * mm))

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
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Condiciones de pago", _heading_style))
    story.append(Paragraph(_FIXED_PAYMENT_TERMS, _normal_style))

    other_details_lines = _warranty_lines(items) + [_INCLUDES_LABOR]
    if estimated_time:
        other_details_lines.append(f"El tiempo estimado de realización es de {estimated_time}.")
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Otros detalles", _heading_style))
    story.append(Paragraph("<br/>".join(other_details_lines), _normal_style))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(_FIXED_FAREWELL, _farewell_style))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("LE SALUDAN ATTE.", _farewell_style))
    if business.get("signature"):
        story.append(Paragraph(business["signature"], _farewell_style))

    doc.build(story)
    return buffer.getvalue()
