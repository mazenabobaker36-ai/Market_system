from pathlib import Path
from typing import Dict

from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter

from utils.paths import REPORTS_DIR, TEMPLATE_PATH


def _rows_html(invoice: Dict) -> str:
    rows = []
    for idx, item in enumerate(invoice.get("items", []), start=1):
        rows.append(
            f"""
            <tr>
                <td>{idx}</td>
                <td>{item['barcode']}</td>
                <td>{item['name']}</td>
                <td>{item['qty']}</td>
                <td>{item['manual_price']:.2f}</td>
                <td>{item['subtotal']:.2f}</td>
            </tr>
            """
        )
    return "\n".join(rows)


def generate_invoice_pdf(invoice: Dict) -> str:
    html_template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rows = _rows_html(invoice)

    replacements = {
        "{invoice_no}": str(invoice["invoice_no"]),
        "{created_at}": str(invoice["created_at"]),
        "{cashier}": str(invoice.get("username") or "-"),
        "{customer}": str(invoice.get("customer_name") or "عميل مباشر"),
        "{rows}": rows,
        "{total}": f"{invoice['total']:.2f}",
        "{paid}": f"{invoice['paid']:.2f}",
        "{change_amount}": f"{invoice['change_amount']:.2f}",
    }

    html_text = html_template
    for key, value in replacements.items():
        html_text = html_text.replace(key, value)

    output_file = REPORTS_DIR / f"{invoice['invoice_no']}.pdf"
    export_invoice_to_pdf(html_text, output_file)
    return str(output_file)


def export_invoice_to_pdf(html_content: str, output_filepath: Path) -> None:
    """Render invoice HTML with Qt's native PDF printer (no GTK dependencies)."""
    output_path = Path(output_filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = QTextDocument()
    document.setHtml(html_content)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(output_path))
    document.print_(printer)
