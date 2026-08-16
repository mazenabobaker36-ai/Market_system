from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextDocument, QDesktopServices, QFont
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.invoice_pdf import generate_invoice_pdf


class InvoiceViewDialog(QDialog):
    def __init__(self, invoice_data: dict, parent=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.tax_rate = 0.0

        self.setWindowTitle(f"معاينة الفاتورة - {invoice_data.get('invoice_no', '-')}")
        self.setModal(True)
        # make dialog compact and constrain width so receipt preview is readable on small screens
        self.setMinimumSize(560, 480)
        self.setMaximumWidth(800)
        self._build_ui()
        self._fill_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Top navigation row (Arabic)
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← رجوع إلى المبيعات")
        self.back_btn.setObjectName("navBackBtn")
        self.back_btn.setProperty("variant", "outline")
        self.back_btn.clicked.connect(self._go_back_to_sales)

        self.print_btn = QPushButton("🖨️ طباعة")
        self.print_btn.setProperty("variant", "primary")
        self.print_btn.clicked.connect(self.print_invoice)

        self.pdf_btn = QPushButton("📥 تنزيل PDF")
        self.pdf_btn.setProperty("variant", "danger")
        self.pdf_btn.clicked.connect(self.download_pdf)

        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.print_btn)
        nav.addWidget(self.pdf_btn)

        root.addLayout(nav)

        # Dark header
        header = QFrame()
        header.setStyleSheet("background: #1e293b; border-radius: 8px; color: #ffffff; padding: 10px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 6, 10, 6)

        # Left: branding
        brand_col = QVBoxLayout()
        brand_lbl = QLabel("🛒 نظام السوبرماركت")
        brand_lbl.setStyleSheet("color: #f8fafc; font-weight: 800; font-size: 16px;")
        brand_sub = QLabel("نظام إدارة المبيعات والمخزون")
        brand_sub.setStyleSheet("color: #e6eef8; font-size: 10px;")
        brand_col.addWidget(brand_lbl)
        brand_col.addWidget(brand_sub)

        # Right: invoice title and meta (Arabic)
        title_col = QVBoxLayout()
        title_lbl = QLabel("فاتورة مبيعات")
        title_lbl.setStyleSheet("color: #ffffff; font-weight: 900; font-size: 20px;")
        self.inv_no_lbl = QLabel("رقم الفاتورة: INV-XXXX")
        self.inv_no_lbl.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 12px;")
        self.inv_time_lbl = QLabel("-")
        self.inv_time_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        title_col.addStretch()
        title_col.addWidget(title_lbl, alignment=Qt.AlignRight)
        title_col.addWidget(self.inv_no_lbl, alignment=Qt.AlignRight)
        title_col.addWidget(self.inv_time_lbl, alignment=Qt.AlignRight)

        h_layout.addLayout(brand_col, 1)
        h_layout.addStretch(1)
        h_layout.addLayout(title_col, 1)

        root.addWidget(header)

        # Meta summary grid (3 columns)
        meta_grid = QGridLayout()
        meta_grid.setSpacing(12)

        self.bill_to_card = QFrame()
        self.bill_to_card.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding:10px;")
        bt_layout = QVBoxLayout(self.bill_to_card)
        self.bill_title = QLabel("👤 بيانات العميل")
        self.bill_title.setStyleSheet("font-weight: 800; color: #0f172a;")
        self.bill_body = QLabel("-")
        self.bill_body.setWordWrap(True)
        bt_layout.addWidget(self.bill_title)
        bt_layout.addWidget(self.bill_body)

        self.payment_card = QFrame()
        self.payment_card.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding:10px;")
        pay_layout = QVBoxLayout(self.payment_card)
        self.pay_title = QLabel("💳 طريقة الدفع")
        self.pay_title.setStyleSheet("font-weight: 800; color: #0f172a;")
        self.pay_body = QLabel("-")
        pay_layout.addWidget(self.pay_title)
        pay_layout.addWidget(self.pay_body)

        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding:10px;")
        s_layout = QVBoxLayout(self.summary_card)
        self.sum_title = QLabel("📋 ملخص الفاتورة")
        self.sum_title.setStyleSheet("font-weight: 800; color: #0f172a;")
        self.sum_body = QLabel("-")
        s_layout.addWidget(self.sum_title)
        s_layout.addWidget(self.sum_body)

        meta_grid.addWidget(self.bill_to_card, 0, 0)
        meta_grid.addWidget(self.payment_card, 0, 1)
        meta_grid.addWidget(self.summary_card, 0, 2)

        root.addLayout(meta_grid)

        # Watermark label (light)
        watermark = QLabel("INVOICE")
        watermark.setStyleSheet("color: rgba(15,23,42,0.04); font-size: 72px; font-weight: 900; margin-top: -40px;")
        watermark.setAlignment(Qt.AlignCenter)
        watermark.setAttribute(Qt.WA_TransparentForMouseEvents)
        root.addWidget(watermark)

        # Items table (compact, Arabic headers)
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["#", "اسم المنتج", "الكمية", "السعر", "الإجمالي"])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(28)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        # custom header styling for this table
        self.items_table.setStyleSheet(
            "QHeaderView::section { background: #4f46e5; color: white; padding:6px; font-weight:800; }"
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(200)

        root.addWidget(self.items_table)

        # Totals box aligned to right
        totals_row = QHBoxLayout()
        totals_row.addStretch()
        self.totals_card = QFrame()
        self.totals_card.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding:12px; min-width:260px;")
        tc_layout = QVBoxLayout(self.totals_card)
        tc_layout.setSpacing(6)
        self.subtotal_lbl = QLabel("Subtotal: 0.00")
        self.discount_lbl = QLabel("Discount: 0.00")
        self.tax_lbl = QLabel("Tax: 0.00")
        self.total_lbl = QLabel("TOTAL: 0.00")
        self.total_lbl.setStyleSheet("color: #10b981; font-weight: 900; font-size: 18px;")
        tc_layout.addWidget(self.subtotal_lbl)
        tc_layout.addWidget(self.discount_lbl)
        tc_layout.addWidget(self.tax_lbl)
        tc_layout.addWidget(self.total_lbl)
        totals_row.addWidget(self.totals_card)

        root.addLayout(totals_row)

        # Footer: status pills, signatures, thank you
        footer = QHBoxLayout()
        # left: pills
        left_footer = QVBoxLayout()
        self.status_pills = QLabel("Online / Cash   ✓ Paid")
        self.status_pills.setStyleSheet("font-weight:700; color: #065f46;")
        left_footer.addWidget(self.status_pills)

        # signatures
        sig_layout = QHBoxLayout()
        cust_sig = QLabel("Customer Signature\n\n____________________")
        auth_sig = QLabel("Authorized Signature\n\n____________________")
        sig_layout.addWidget(cust_sig)
        sig_layout.addWidget(auth_sig)

        left_footer.addLayout(sig_layout)

        footer.addLayout(left_footer)
        footer.addStretch()
        thank_lbl = QLabel("Thank you for your purchase!")
        thank_lbl.setStyleSheet("font-weight:800; color: #0f172a;")
        footer.addWidget(thank_lbl, alignment=Qt.AlignCenter)
        footer.addStretch()

        root.addLayout(footer)

    def _go_back_to_sales(self):
        # Close dialog and attempt to navigate main window to invoices/sales tab
        self.close()
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'switch_page'):
                target = 'invoices' if 'invoices' in getattr(parent, 'nav_buttons', {}) else 'reports'
                try:
                    parent.switch_page(target)
                except Exception:
                    pass
                break
            # move up the QObject parent chain
            try:
                parent = parent.parent()
            except Exception:
                parent = None

    def _fill_data(self):
        inv = self.invoice_data
        invoice_no = inv.get("invoice_no", "-")
        created_at = inv.get("created_at", "-")
        cashier = inv.get("username") or "-"
        customer = inv.get("customer_name") or "عميل مباشر"

        # update header labels
        self.inv_no_lbl.setText(invoice_no)
        self.inv_time_lbl.setText(created_at)

        try:
            self.total_lbl.setText(f"TOTAL: {float(inv.get('total',0)):.2f}")
        except Exception:
            pass

        self.bill_body.setText(f"{customer}\n{inv.get('customer_phone','') or ''}")
        self.pay_body.setText(f"Method: {inv.get('payment_method','Cash')}\nStatus: Paid\nCashier: {cashier}")
        self.sum_body.setText(f"Date: {created_at}\nItems: {len(inv.get('items', []))}")

        items = inv.get("items", [])
        self.items_table.setRowCount(len(items))
        for i, item in enumerate(items, start=1):
            self.items_table.setItem(i-1, 0, QTableWidgetItem(str(i)))
            name_item = QTableWidgetItem(item.get("name") or "-")
            name_item.setFont(QFont("", weight=75))
            self.items_table.setItem(i-1, 1, name_item)
            self.items_table.setItem(i-1, 2, QTableWidgetItem(str(item.get("qty", 0))))
            self.items_table.setItem(i-1, 3, QTableWidgetItem(f"{item.get('manual_price',0):.2f}"))
            self.items_table.setItem(i-1, 4, QTableWidgetItem(f"{item.get('subtotal',0):.2f}"))

        total = float(inv.get("total", 0.0))
        paid = float(inv.get("paid", 0.0))
        change = float(inv.get("change_amount", 0.0))
        subtotal = sum(item.get('subtotal',0) for item in items)
        self.subtotal_lbl.setText(f"المجموع الفرعي: {subtotal:.2f}")
        self.discount_lbl.setText(f"الخصم: {float(inv.get('discount',0)):.2f}")
        self.tax_lbl.setText(f"الضريبة: {float(inv.get('tax',0)):.2f}")
        self.total_lbl.setText(f"الصافي النهائي: {total:.2f}")

    def _render_html(self) -> str:
        inv = self.invoice_data
        rows = []
        for item in inv.get("items", []):
            rows.append(
                f"<tr><td>{item.get('name','-')}</td>"
                f"<td style='text-align:center'>{item.get('qty',0)}</td><td style='text-align:right'>{item.get('manual_price',0):.2f}</td>"
                f"<td style='text-align:right'>{item.get('subtotal',0):.2f}</td></tr>"
            )

        body_rows = "".join(rows)
        return f"""
        <html dir='rtl' lang='ar'>
          <body style='font-family: Segoe UI; font-size: 12px; max-width:540px; margin:0 auto;'>
            <h2 style='text-align:center'>فاتورة مبيعات #{inv.get('invoice_no','-')}</h2>
            <p style='text-align:center'>التاريخ: {inv.get('created_at','-')} &nbsp;|&nbsp; الكاشير: {inv.get('username','-')}</p>
            <table border='0' cellspacing='0' cellpadding='6' width='100%' style='border-collapse:collapse;'>
              <thead><tr style='background:#f8fafc; color:#0f172a;'><th style='text-align:left'>اسم المنتج</th><th style='width:70px;text-align:center'>الكمية</th><th style='width:90px;text-align:right'>السعر</th><th style='width:110px;text-align:right'>الإجمالي</th></tr></thead>
              <tbody>{body_rows}</tbody>
            </table>
            <div style='margin-top:10px; text-align:right;'>
              <p>المجموع الفرعي: {float(inv.get('subtotal',0)):.2f}</p>
              <p>الخصم: {float(inv.get('discount',0)):.2f}</p>
              <p>الضريبة: {float(inv.get('tax',0)):.2f}</p>
              <p style='font-weight:900; font-size:16px'>الصافي النهائي: {float(inv.get('total',0)):.2f}</p>
            </div>
            <p style='text-align:center; margin-top:14px;'>شكراً لزيارتكم! نتمنى لكم يوماً سعيداً</p>
          </body>
        </html>
        """

    def print_invoice(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        document = QTextDocument()
        document.setHtml(self._render_html())
        document.print_(printer)

    def download_pdf(self):
        try:
            pdf_path = Path(generate_invoice_pdf(self.invoice_data))
            QMessageBox.information(self, "تم", f"تم إنشاء الملف:\n{pdf_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))
