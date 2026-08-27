from pathlib import Path
from typing import Dict

from weasyprint import HTML


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "assets" / "invoice_template.html"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


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
    HTML(string=html_text, base_url=str(BASE_DIR)).write_pdf(str(output_file))
    return str(output_file)
