from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextDocument, QDesktopServices, QFont
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
        # generous width and height so all invoice columns and numbers display cleanly
        self.setMinimumSize(720, 560)
        self.setMaximumWidth(960)
        self._build_ui()
        self._fill_data()

    def _build_ui(self):
        # Outer dialog layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Top fixed action bar (sticky for immediate action access)
        top_bar = QWidget()
        top_bar.setStyleSheet("background: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        nav = QHBoxLayout(top_bar)
        nav.setContentsMargins(16, 12, 16, 12)
        nav.setSpacing(10)

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

        outer_layout.addWidget(top_bar)

        # Scrollable container for the full invoice body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #f8fafc; border: none; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: #f8fafc;")
        root = QVBoxLayout(scroll_content)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(14)

        # Dark header (branding + invoice no)
        header = QFrame()
        header.setStyleSheet("background: #1e293b; border-radius: 8px; color: #ffffff; padding: 12px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 8, 12, 8)

        # Left: branding
        brand_col = QVBoxLayout()
        brand_col.setSpacing(3)
        brand_lbl = QLabel("🛒 نظام السوبرماركت")
        brand_lbl.setStyleSheet("color: #f8fafc; font-weight: 800; font-size: 16px; background: transparent;")
        brand_sub = QLabel("نظام إدارة المبيعات والمخزون")
        brand_sub.setStyleSheet("color: #cbd5e1; font-size: 11px; background: transparent;")
        brand_col.addWidget(brand_lbl)
        brand_col.addWidget(brand_sub)

        # Right: invoice title and meta (Arabic)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("فاتورة مبيعات")
        title_lbl.setStyleSheet("color: #ffffff; font-weight: 900; font-size: 20px; background: transparent;")
        self.inv_no_lbl = QLabel("رقم الفاتورة: INV-XXXX")
        self.inv_no_lbl.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 12px; background: transparent;")
        self.inv_time_lbl = QLabel("-")
        self.inv_time_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; background: transparent;")
        title_col.addStretch()
        title_col.addWidget(title_lbl, alignment=Qt.AlignRight)
        title_col.addWidget(self.inv_no_lbl, alignment=Qt.AlignRight)
        title_col.addWidget(self.inv_time_lbl, alignment=Qt.AlignRight)

        h_layout.addLayout(brand_col, 1)
        h_layout.addStretch(1)
        h_layout.addLayout(title_col, 1)

        root.addWidget(header)

        # Meta summary grid (3 info cards: Customer, Payment, Summary)
        meta_grid = QGridLayout()
        meta_grid.setSpacing(12)

        card_qss = """
            QFrame#info_card_item {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                min-height: 75px;
                padding: 10px 12px;
            }
        """

        self.bill_to_card = QFrame()
        self.bill_to_card.setObjectName("info_card_item")
        self.bill_to_card.setStyleSheet(card_qss)
        bt_layout = QVBoxLayout(self.bill_to_card)
        bt_layout.setContentsMargins(6, 6, 6, 6)
        bt_layout.setSpacing(6)
        self.bill_title = QLabel("👤 بيانات العميل")
        self.bill_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #0f172a; background: transparent; border: none;")
        self.bill_body = QLabel("-")
        self.bill_body.setStyleSheet("color: #334155; font-size: 12px; background: transparent; border: none;")
        self.bill_body.setWordWrap(True)
        bt_layout.addWidget(self.bill_title)
        bt_layout.addWidget(self.bill_body)
        bt_layout.addStretch()

        self.payment_card = QFrame()
        self.payment_card.setObjectName("info_card_item")
        self.payment_card.setStyleSheet(card_qss)
        pay_layout = QVBoxLayout(self.payment_card)
        pay_layout.setContentsMargins(6, 6, 6, 6)
        pay_layout.setSpacing(6)
        self.pay_title = QLabel("💳 طريقة الدفع")
        self.pay_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #0f172a; background: transparent; border: none;")
        self.pay_body = QLabel("-")
        self.pay_body.setStyleSheet("color: #334155; font-size: 12px; background: transparent; border: none;")
        self.pay_body.setWordWrap(True)
        pay_layout.addWidget(self.pay_title)
        pay_layout.addWidget(self.pay_body)
        pay_layout.addStretch()

        self.summary_card = QFrame()
        self.summary_card.setObjectName("info_card_item")
        self.summary_card.setStyleSheet(card_qss)
        s_layout = QVBoxLayout(self.summary_card)
        s_layout.setContentsMargins(6, 6, 6, 6)
        s_layout.setSpacing(6)
        self.sum_title = QLabel("📋 ملخص الفاتورة")
        self.sum_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #0f172a; background: transparent; border: none;")
        self.sum_body = QLabel("-")
        self.sum_body.setStyleSheet("color: #334155; font-size: 12px; background: transparent; border: none;")
        self.sum_body.setWordWrap(True)
        s_layout.addWidget(self.sum_title)
        s_layout.addWidget(self.sum_body)
        s_layout.addStretch()

        meta_grid.addWidget(self.bill_to_card, 0, 0)
        meta_grid.addWidget(self.payment_card, 0, 1)
        meta_grid.addWidget(self.summary_card, 0, 2)

        root.addLayout(meta_grid)

        # Watermark label (light)
        watermark = QLabel("INVOICE")
        watermark.setStyleSheet("color: rgba(15,23,42,0.04); font-size: 72px; font-weight: 900; margin-top: -30px; margin-bottom: -15px;")
        watermark.setAlignment(Qt.AlignCenter)
        watermark.setAttribute(Qt.WA_TransparentForMouseEvents)
        root.addWidget(watermark)

        # Items table (compact, Arabic headers, generous column padding & spacing)
        self.items_table = QTableWidget(0, 6)
        self.invoice_table = self.items_table  # alias for direct compatibility
        self.items_table.setHorizontalHeaderLabels([
            "#", "اسم المنتج", "الباركود", "الكمية", "سعر الوحدة", "الإجمالي"
        ])
        self.items_table.verticalHeader().setVisible(False)
        # Set explicit row height for all items (comfortable vertical breathing room)
        self.items_table.verticalHeader().setDefaultSectionSize(45)

        header = self.items_table.horizontalHeader()
        # Set explicit column stretching and minimum widths
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Item # / Index
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Product Name (give maximum space)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Barcode
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Quantity
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Unit Price
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Total Price

        # Set minimum width for key numeric columns so content never gets squeezed
        self.items_table.setColumnWidth(1, 180)  # Product Name min width
        self.items_table.setColumnWidth(4, 80)   # Unit Price min width
        self.items_table.setColumnWidth(5, 90)   # Total Price min width

        # custom header styling and vertical cell padding
        self.items_table.setStyleSheet(
            """
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
                font-size: 13px;
                color: #1e293b;
            }
            QHeaderView::section {
                background-color: #4f46e5;
                color: #ffffff;
                padding-top: 10px;
                padding-bottom: 10px;
                padding-left: 10px;
                padding-right: 10px;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid #4338ca;
            }
            QTableWidget::item {
                padding-top: 8px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                font-size: 13px;
                border-bottom: 1px solid #f1f5f9;
            }
            """
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(240)

        root.addWidget(self.items_table)

        # Totals summary box aligned to right
        totals_row = QHBoxLayout()
        totals_row.addStretch()

        self.totals_card = QFrame()
        self.totals_card.setObjectName("totalsSummaryCard")
        self.totals_card.setStyleSheet(
            """
            QFrame#totalsSummaryCard {
                background: #ffffff;
                border: 1.5px solid #e2e8f0;
                border-radius: 10px;
                min-width: 300px;
                padding: 12px 16px;
            }
            """
        )
        tc_layout = QVBoxLayout(self.totals_card)
        tc_layout.setContentsMargins(12, 12, 12, 12)
        tc_layout.setSpacing(10)  # Explicit vertical spacing

        self.subtotal_lbl = QLabel("المجموع الفرعي: 0.00")
        self.subtotal_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569; min-height: 28px; background: transparent; border: none;")

        self.discount_lbl = QLabel("الخصم: 0.00")
        self.discount_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569; min-height: 28px; background: transparent; border: none;")

        self.tax_lbl = QLabel("الضريبة: 0.00")
        self.tax_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569; min-height: 28px; background: transparent; border: none;")

        self.total_lbl = QLabel("الصافي النهائي: 0.00")
        self.total_lbl.setStyleSheet("color: #059669; font-weight: 900; font-size: 19px; min-height: 38px; padding-top: 6px; padding-bottom: 2px; border-top: 1.5px solid #e2e8f0; background: transparent;")

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
        self.status_pills.setStyleSheet("font-weight:700; color: #065f46; background: transparent;")
        left_footer.addWidget(self.status_pills)

        # signatures
        sig_layout = QHBoxLayout()
        cust_sig = QLabel("Customer Signature\n\n____________________")
        cust_sig.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
        auth_sig = QLabel("Authorized Signature\n\n____________________")
        auth_sig.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
        sig_layout.addWidget(cust_sig)
        sig_layout.addWidget(auth_sig)

        left_footer.addLayout(sig_layout)

        footer.addLayout(left_footer)
        footer.addStretch()
        thank_lbl = QLabel("Thank you for your purchase!")
        thank_lbl.setStyleSheet("font-weight:800; color: #0f172a; background: transparent;")
        footer.addWidget(thank_lbl, alignment=Qt.AlignCenter)
        footer.addStretch()

        root.addLayout(footer)

        # Set scroll content widget and attach to outer layout
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll)

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
        self.pay_body.setText(f"طريقة الدفع: {inv.get('payment_method','نقداً')}\nالحالة: مدفوع ✓\nالكاشير: {cashier}")
        self.sum_body.setText(f"التاريخ: {created_at}\nعدد الأصناف: {len(inv.get('items', []))}")

        items = inv.get("items", [])
        self.items_table.setRowCount(len(items))
        for i, item in enumerate(items, start=1):
            idx_item = QTableWidgetItem(str(i))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i - 1, 0, idx_item)

            name_item = QTableWidgetItem(item.get("name") or "-")
            name_item.setFont(QFont("", weight=75))
            self.items_table.setItem(i - 1, 1, name_item)

            barcode_item = QTableWidgetItem(str(item.get("barcode") or "-"))
            barcode_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i - 1, 2, barcode_item)

            qty_item = QTableWidgetItem(str(item.get("qty", 0)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i - 1, 3, qty_item)

            price_item = QTableWidgetItem(f"{float(item.get('manual_price', 0)):.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i - 1, 4, price_item)

            subtotal_item = QTableWidgetItem(f"{float(item.get('subtotal', 0)):.2f}")
            subtotal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i - 1, 5, subtotal_item)

        total = float(inv.get("total", 0.0) or 0.0)
        paid = float(inv.get("paid", 0.0) or 0.0)
        change = float(inv.get("change_amount", 0.0) or 0.0)
        subtotal = sum(float(item.get('subtotal', 0) or 0) for item in items)
        self.subtotal_lbl.setText(f"المجموع الفرعي: {subtotal:.2f}")
        self.discount_lbl.setText(f"الخصم: {float(inv.get('discount', 0) or 0):.2f}")
        self.tax_lbl.setText(f"الضريبة: {float(inv.get('tax', 0) or 0):.2f}")
        self.total_lbl.setText(f"الصافي النهائي: {total:.2f}")

    def _render_html(self) -> str:
        inv = self.invoice_data
        rows = []
        for item in inv.get("items", []):
            rows.append(
                f"<tr>"
                f"<td style='padding:6px 10px;'>{item.get('name', '-')}</td>"
                f"<td style='text-align:center; padding:6px 10px;'>{item.get('barcode', '-')}</td>"
                f"<td style='text-align:center; padding:6px 10px;'>{item.get('qty', 0)}</td>"
                f"<td style='text-align:right; padding:6px 10px;'>{float(item.get('manual_price', 0)):.2f}</td>"
                f"<td style='text-align:right; padding:6px 10px;'>{float(item.get('subtotal', 0)):.2f}</td>"
                f"</tr>"
            )

        body_rows = "".join(rows)
        return f"""
        <html dir='rtl' lang='ar'>
          <body style='font-family: Segoe UI, Tahoma, sans-serif; font-size: 12px; max-width:600px; margin:0 auto; padding:10px;'>
            <h2 style='text-align:center'>فاتورة مبيعات #{inv.get('invoice_no', '-')}</h2>
            <p style='text-align:center; color:#64748b;'>التاريخ: {inv.get('created_at', '-')} &nbsp;|&nbsp; الكاشير: {inv.get('username', '-')}</p>
            <table border='0' cellspacing='0' cellpadding='6' width='100%' style='border-collapse:collapse;'>
              <thead>
                <tr style='background:#f8fafc; color:#0f172a; border-bottom:2px solid #e2e8f0;'>
                  <th style='text-align:right; padding:6px 10px;'>اسم المنتج</th>
                  <th style='width:90px; text-align:center; padding:6px 10px;'>الباركود</th>
                  <th style='width:60px; text-align:center; padding:6px 10px;'>الكمية</th>
                  <th style='width:80px; text-align:right; padding:6px 10px;'>السعر</th>
                  <th style='width:90px; text-align:right; padding:6px 10px;'>الإجمالي</th>
                </tr>
              </thead>
              <tbody>{body_rows}</tbody>
            </table>
            <div style='margin-top:12px; text-align:right;'>
              <p>المجموع الفرعي: {float(inv.get('subtotal', 0) or 0):.2f}</p>
              <p>الخصم: {float(inv.get('discount', 0) or 0):.2f}</p>
              <p>الضريبة: {float(inv.get('tax', 0) or 0):.2f}</p>
              <p style='font-weight:900; font-size:16px; color:#10b981;'>الصافي النهائي: {float(inv.get('total', 0) or 0):.2f}</p>
            </div>
            <p style='text-align:center; margin-top:16px; color:#64748b;'>شكراً لزيارتكم! نتمنى لكم يوماً سعيداً</p>
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
