from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.stock_window import StockWindow
from utils.invoice_pdf import generate_invoice_pdf



class CashierWindow(QMainWindow):
    def __init__(self, db, current_user, login_history_id=None):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.login_history_id = login_history_id
        self.current_product = None
        self.cart = []

        self.setWindowTitle(
            f"Super Market POS - المستخدم: {current_user['username']} ({current_user['role']})"
        )
        self.resize(1280, 800)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.pos_tab = self._build_pos_tab()
        self.dashboard_tab = self._build_dashboard_tab()
        self.customer_tab = self._build_customer_tab()
        self.reports_tab = self._build_reports_tab()
        self.stock_tab = StockWindow(self.db)

        self.tabs.addTab(self.pos_tab, "الكاشير")
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.customer_tab, "العملاء")
        self.tabs.addTab(self.stock_tab, "المخزون")
        self.tabs.addTab(self.reports_tab, "التقارير")

        self._apply_role_permissions()
        self.refresh_dashboard()
        self.refresh_customers_table()
        self.refresh_customer_combo()
        self.refresh_reports()

    def _apply_role_permissions(self):
        role = self.current_user.get("role", "Saler")
        if role == "Saler":
            self.tabs.setTabEnabled(self.tabs.indexOf(self.stock_tab), False)
            self.tabs.setTabEnabled(self.tabs.indexOf(self.reports_tab), False)
        elif role == "Admin":
            self.tabs.setTabEnabled(self.tabs.indexOf(self.reports_tab), True)

    # ---------------------------------------------------------------------
    # POS TAB (Refactored)
    # ---------------------------------------------------------------------
    def _build_pos_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Scan / Product Section (Bootstrap Card-like group)
        scan_box = QGroupBox("مسح QR / Barcode")
        scan_layout = QGridLayout(scan_box)
        scan_layout.setHorizontalSpacing(10)
        scan_layout.setVerticalSpacing(10)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("امسح الرمز هنا ثم Enter")
        self.barcode_input.returnPressed.connect(self.on_scan_barcode)

        self.product_label = QLabel("المنتج: -")
        self.product_label.setProperty("role", "muted")

        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("الكمية")

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("السعر اليدوي")
        self.price_input.returnPressed.connect(self.add_item_to_cart)

        self.add_to_cart_btn = QPushButton("إضافة للسلة")
        self.add_to_cart_btn.setProperty("variant", "primary")
        self.add_to_cart_btn.clicked.connect(self.add_item_to_cart)

        scan_layout.addWidget(QLabel("QR/Barcode:"), 0, 0)
        scan_layout.addWidget(self.barcode_input, 0, 1, 1, 5)
        scan_layout.addWidget(self.product_label, 1, 0, 1, 6)

        scan_layout.addWidget(QLabel("الكمية:"), 2, 0)
        scan_layout.addWidget(self.qty_input, 2, 1)
        scan_layout.addWidget(QLabel("السعر:"), 2, 2)
        scan_layout.addWidget(self.price_input, 2, 3)
        scan_layout.addWidget(self.add_to_cart_btn, 2, 4, 1, 2)

        # Cart Table
        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels([
            "Product ID",
            "Barcode",
            "الاسم",
            "الكمية",
            "السعر",
            "الإجمالي",
        ])
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.horizontalHeader().setStretchLastSection(True)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)

        # Payment Section
        payment_box = QGroupBox("الدفع")
        payment_layout = QFormLayout(payment_box)
        payment_layout.setHorizontalSpacing(14)
        payment_layout.setVerticalSpacing(10)

        self.customer_combo = QComboBox()

        self.total_label = QLabel("0.00")
        self.total_label.setProperty("role", "value")

        self.paid_input = QLineEdit("0")
        self.change_label = QLabel("0.00")
        self.change_label.setProperty("role", "value")

        self.checkout_btn = QPushButton("تأكيد البيع + طباعة الفاتورة")
        self.checkout_btn.setProperty("variant", "success")
        self.checkout_btn.clicked.connect(self.checkout)

        self.clear_btn = QPushButton("تفريغ السلة")
        self.clear_btn.setProperty("variant", "danger")
        self.clear_btn.clicked.connect(self.clear_cart)

        payment_layout.addRow("العميل:", self.customer_combo)
        payment_layout.addRow("الإجمالي:", self.total_label)
        payment_layout.addRow("المدفوع:", self.paid_input)
        payment_layout.addRow("الباقي:", self.change_label)

        payment_actions = QHBoxLayout()
        payment_actions.addWidget(self.checkout_btn)
        payment_actions.addWidget(self.clear_btn)
        payment_layout.addRow(payment_actions)

        layout.addWidget(scan_box)
        layout.addWidget(self.cart_table)
        layout.addWidget(payment_box)
        return root

    # ---------------------------------------------------------------------
    # DASHBOARD TAB (Refactored with Stats Cards)
    # ---------------------------------------------------------------------
    def _build_dashboard_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("لوحة التحكم")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #212529;")
        subtitle = QLabel("نظرة سريعة على أهم مؤشرات اليوم")
        subtitle.setProperty("role", "muted")

        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)

        products_card, self.products_count_label = self._create_stat_card(
            icon_text="📦",
            title_text="Total Products",
            value_text="0",
            variant="products",
        )
        customers_card, self.customers_count_label = self._create_stat_card(
            icon_text="👥",
            title_text="Total Customers",
            value_text="0",
            variant="customers",
        )
        sales_card, self.sales_today_label = self._create_stat_card(
            icon_text="💰",
            title_text="Today's Sales",
            value_text="0.00",
            variant="sales",
        )
        invoices_card, self.invoices_today_label = self._create_stat_card(
            icon_text="🧾",
            title_text="Today's Invoices",
            value_text="0",
            variant="invoices",
        )

        cards_grid.addWidget(products_card, 0, 0)
        cards_grid.addWidget(customers_card, 0, 1)
        cards_grid.addWidget(sales_card, 1, 0)
        cards_grid.addWidget(invoices_card, 1, 1)

        for col in range(2):
            cards_grid.setColumnStretch(col, 1)

        refresh_btn = QPushButton("تحديث Dashboard")
        refresh_btn.setProperty("variant", "primary")
        refresh_btn.clicked.connect(self.refresh_dashboard)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(cards_grid)
        layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)
        layout.addStretch()
        return root

    def _create_stat_card(self, icon_text: str, title_text: str, value_text: str, variant: str):
        card = QFrame()
        card.setProperty("card", "stat")
        card.setProperty("cardVariant", variant)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("font-size: 22px;")

        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #495057;")

        value_label = QLabel(value_text)
        value_label.setProperty("role", "value")

        card_layout.addWidget(icon_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()

        return card, value_label

    def _build_customer_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        form_box = QGroupBox("إضافة عميل دائم")
        form = QFormLayout(form_box)

        self.customer_name_input = QLineEdit()
        self.customer_phone_input = QLineEdit()
        self.customer_address_input = QLineEdit()

        form.addRow("الاسم:", self.customer_name_input)
        form.addRow("الهاتف:", self.customer_phone_input)
        form.addRow("العنوان:", self.customer_address_input)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("إضافة")
        add_btn.clicked.connect(self.add_customer)
        refresh_btn = QPushButton("تحديث")
        refresh_btn.clicked.connect(self.refresh_customers_table)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(refresh_btn)
        form.addRow(btn_row)

        self.customers_table = QTableWidget(0, 6)
        self.customers_table.setHorizontalHeaderLabels([
            "ID",
            "الاسم",
            "الهاتف",
            "العنوان",
            "النقاط",
            "آخر زيارة",
        ])

        layout.addWidget(form_box)
        layout.addWidget(self.customers_table)
        return root

    def _build_reports_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        sales_filter = QGroupBox("تقرير المبيعات")
        sales_filter_layout = QHBoxLayout(sales_filter)

        self.sales_start_date = QDateEdit()
        self.sales_start_date.setCalendarPopup(True)
        self.sales_start_date.setDate(QDate.currentDate().addDays(-7))

        self.sales_end_date = QDateEdit()
        self.sales_end_date.setCalendarPopup(True)
        self.sales_end_date.setDate(QDate.currentDate())

        sales_btn = QPushButton("تحميل تقرير المبيعات")
        sales_btn.clicked.connect(self.load_sales_report)

        sales_filter_layout.addWidget(QLabel("من:"))
        sales_filter_layout.addWidget(self.sales_start_date)
        sales_filter_layout.addWidget(QLabel("إلى:"))
        sales_filter_layout.addWidget(self.sales_end_date)
        sales_filter_layout.addWidget(sales_btn)

        self.sales_table = QTableWidget(0, 6)
        self.sales_table.setHorizontalHeaderLabels([
            "رقم الفاتورة",
            "التاريخ",
            "الإجمالي",
            "المدفوع",
            "الباقي",
            "الكاشير",
        ])

        expiry_box = QGroupBox("تقرير الصلاحية")
        expiry_layout = QHBoxLayout(expiry_box)
        expiry_btn = QPushButton("تحديث تقرير الانتهاء")
        expiry_btn.clicked.connect(self.load_expiry_report)
        expiry_layout.addWidget(expiry_btn)

        self.expiry_table = QTableWidget(0, 5)
        self.expiry_table.setHorizontalHeaderLabels([
            "Barcode",
            "الاسم",
            "المخزون",
            "تاريخ الانتهاء",
            "الحالة",
        ])

        login_box = QGroupBox("سجل دخول المستخدمين")
        login_layout = QVBoxLayout(login_box)
        login_refresh_btn = QPushButton("تحديث سجل الدخول")
        login_refresh_btn.clicked.connect(self.load_login_history)

        self.login_table = QTableWidget(0, 6)
        self.login_table.setHorizontalHeaderLabels([
            "المستخدم",
            "الدور",
            "تسجيل الدخول",
            "تسجيل الخروج",
            "الحالة",
            "ID",
        ])

        login_layout.addWidget(login_refresh_btn)
        login_layout.addWidget(self.login_table)

        layout.addWidget(sales_filter)
        layout.addWidget(self.sales_table)
        layout.addWidget(expiry_box)
        layout.addWidget(self.expiry_table)
        layout.addWidget(login_box)
        return root

    def on_scan_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return

        product = self.db.find_product_by_barcode(barcode)
        if not product:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على المنتج")
            self.barcode_input.selectAll()
            self.barcode_input.setFocus()
            return

        self.current_product = product
        self.product_label.setText(
            f"المنتج: {product['name']} | متاح: {product['stock_qty']} | سعر افتراضي: {product['default_price']:.2f}"
        )
        self.price_input.setText(str(product["default_price"]))

        # الانتقال الإجباري لحقل السعر فور قراءة الرمز
        self.price_input.setFocus()
        self.price_input.selectAll()

    def add_item_to_cart(self):
        if not self.current_product:
            QMessageBox.warning(self, "تنبيه", "امسح المنتج أولاً")
            return

        try:
            qty = float(self.qty_input.text().strip())
            price = float(self.price_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الكمية والسعر يجب أن يكونا رقماً")
            return

        if qty <= 0 or price < 0:
            QMessageBox.warning(self, "خطأ", "الكمية يجب أن تكون أكبر من صفر")
            return

        already_in_cart = sum(
            item["qty"] for item in self.cart if item["product_id"] == self.current_product["id"]
        )
        if already_in_cart + qty > float(self.current_product["stock_qty"]):
            QMessageBox.warning(self, "مخزون غير كافٍ", "الكمية المطلوبة أكبر من المتاح")
            return

        self.cart.append(
            {
                "product_id": self.current_product["id"],
                "barcode": self.current_product["barcode"],
                "name": self.current_product["name"],
                "qty": qty,
                "manual_price": price,
            }
        )
        self.refresh_cart()

        self.barcode_input.clear()
        self.qty_input.setText("1")
        self.price_input.clear()
        self.product_label.setText("المنتج: -")
        self.current_product = None
        self.barcode_input.setFocus()

    def refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart))
        total = 0.0

        for row, item in enumerate(self.cart):
            subtotal = item["qty"] * item["manual_price"]
            total += subtotal

            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item["product_id"])))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item["barcode"]))
            self.cart_table.setItem(row, 2, QTableWidgetItem(item["name"]))
            self.cart_table.setItem(row, 3, QTableWidgetItem(str(item["qty"])))
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{item['manual_price']:.2f}"))
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"{subtotal:.2f}"))

        self.total_label.setText(f"{total:.2f}")
        try:
            paid = float(self.paid_input.text().strip())
        except ValueError:
            paid = 0.0

        self.change_label.setText(f"{paid - total:.2f}")

        self.cart_table.resizeColumnsToContents()
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def clear_cart(self):
        self.cart = []
        self.refresh_cart()

    def _build_receipt_html(self, invoice: dict) -> str:
        items = invoice.get("items", [])
        rows_html = []
        for idx, it in enumerate(items, start=1):
            name = it.get("name", "-")
            qty = it.get("qty", 0)
            price = float(it.get("manual_price", 0.0) or 0.0)
            subtotal = float(it.get("subtotal", 0.0) or 0.0)
            rows_html.append(
                f"""
                <tr>
                    <td style="padding: 4px 2px; text-align: right; font-weight: bold;">{name}</td>
                    <td style="padding: 4px 2px; text-align: center;">{qty}</td>
                    <td style="padding: 4px 2px; text-align: center;">{price:.2f}</td>
                    <td style="padding: 4px 2px; text-align: left; font-weight: bold;">{subtotal:.2f}</td>
                </tr>
                """
            )
        rows_str = "".join(rows_html)

        subtotal_val = float(invoice.get("subtotal", 0.0) or 0.0)
        total_val = float(invoice.get("total", 0.0) or 0.0)
        paid_val = float(invoice.get("paid", 0.0) or 0.0)
        change_val = float(invoice.get("change_amount", 0.0) or 0.0)
        cashier_name = invoice.get("username") or "-"
        customer_name = invoice.get("customer_name") or "عميل مباشر"
        inv_no = invoice.get("invoice_no", "-")
        created_at = invoice.get("created_at", "")

        return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: sans-serif; font-size: 11px; margin: 0; padding: 6px; }}
    .receipt {{ max-width: 280px; margin: auto; text-align: right; }}
    .divider {{ border-top: 1px dashed #000; margin: 6px 0; }}
  </style>
</head>
<body>
  <div class="receipt">
    <div style="text-align: center; font-weight: bold; font-size: 14px;">🛒 سوبرماركت الفتح</div>
    <div class="divider"></div>
    <div>رقم الفاتورة: {inv_no}</div>
    <div>التاريخ: {created_at}</div>
    <div>الكاشير: {cashier_name} | العميل: {customer_name}</div>
    <div class="divider"></div>
    <table style="width: 100%; border-collapse: collapse; font-size: 10px;">
      <thead>
        <tr style="border-bottom: 1px solid #000;">
          <th style="text-align: right;">الصنف</th>
          <th style="text-align: center;">الكمية</th>
          <th style="text-align: center;">السعر</th>
          <th style="text-align: left;">الإجمالي</th>
        </tr>
      </thead>
      <tbody>{rows_str}</tbody>
    </table>
    <div class="divider"></div>
    <div style="font-weight: bold;">الإجمالي: {total_val:.2f} ج.م</div>
    <div>المدفوع: {paid_val:.2f} ج.م</div>
    <div>الباقي: {change_val:.2f} ج.م</div>
    <div class="divider"></div>
    <div style="text-align: center; font-size: 10px;">شكراً لتسوقكم معنا!</div>
  </div>
</body>
</html>
"""

    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة")
            return

        try:
            paid = float(self.paid_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "قيمة المدفوع غير صحيحة")
            return

        customer_id = self.customer_combo.currentData()
        if customer_id == -1:
            customer_id = None

        try:
            invoice_id, invoice_no, total, change_amount = self.db.create_invoice(
                items=self.cart,
                paid=paid,
                user_id=self.current_user["id"],
                customer_id=customer_id,
            )
            invoice = self.db.get_invoice_details(invoice_id)
            pdf_path = generate_invoice_pdf(invoice)

            # Trigger receipt printing
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setDocName(f"Receipt-{invoice_no}")
                dlg = QPrintDialog(printer, self)
                if dlg.exec_() == QDialog.Accepted:
                    doc = QTextDocument()
                    doc.setHtml(self._build_receipt_html(invoice))
                    doc.print_(printer)
            except Exception as pe:
                print(f"Print error: {pe}")

            QMessageBox.information(
                self,
                "نجاح",
                f"تم حفظ الفاتورة {invoice_no}\nالإجمالي: {total:.2f}\nالباقي: {change_amount:.2f}\nPDF: {pdf_path}",
            )

            self.clear_cart()
            self.paid_input.setText("0")
            self.refresh_dashboard()
            self.refresh_reports()
            self.stock_tab.refresh_table()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def add_customer(self):
        name = self.customer_name_input.text().strip()
        phone = self.customer_phone_input.text().strip()
        address = self.customer_address_input.text().strip()

        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم العميل مطلوب")
            return

        try:
            self.db.create_customer(name, phone, address)
            QMessageBox.information(self, "نجاح", "تم إضافة العميل")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))
            return

        self.customer_name_input.clear()
        self.customer_phone_input.clear()
        self.customer_address_input.clear()
        self.refresh_customers_table()
        self.refresh_customer_combo()

    def refresh_customers_table(self):
        customers = self.db.list_customers()
        self.customers_table.setRowCount(len(customers))

        for i, c in enumerate(customers):
            self.customers_table.setItem(i, 0, QTableWidgetItem(str(c["id"])))
            self.customers_table.setItem(i, 1, QTableWidgetItem(c["name"]))
            self.customers_table.setItem(i, 2, QTableWidgetItem(c["phone"] or ""))
            self.customers_table.setItem(i, 3, QTableWidgetItem(c["address"] or ""))
            self.customers_table.setItem(i, 4, QTableWidgetItem(str(c["points"])))
            self.customers_table.setItem(i, 5, QTableWidgetItem(c["last_visit"] or "-"))

        self.customers_table.resizeColumnsToContents()

    def refresh_customer_combo(self):
        self.customer_combo.clear()
        self.customer_combo.addItem("Walk-in", -1)
        for c in self.db.list_customers():
            self.customer_combo.addItem(f"{c['name']} ({c['phone'] or 'No Phone'})", c["id"])

    def refresh_dashboard(self):
        d = self.db.get_dashboard_summary()
        self.products_count_label.setText(str(d["products_count"]))
        self.customers_count_label.setText(str(d["customers_count"]))
        self.sales_today_label.setText(f"{d['sales_today']:.2f}")
        self.invoices_today_label.setText(str(d["invoices_today"]))

    def load_sales_report(self):
        start_date = self.sales_start_date.date().toString("yyyy-MM-dd")
        end_date = self.sales_end_date.date().toString("yyyy-MM-dd")

        rows = self.db.get_sales_report(start_date, end_date)
        self.sales_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.sales_table.setItem(i, 0, QTableWidgetItem(r["invoice_no"]))
            self.sales_table.setItem(i, 1, QTableWidgetItem(r["created_at"]))
            self.sales_table.setItem(i, 2, QTableWidgetItem(f"{r['total']:.2f}"))
            self.sales_table.setItem(i, 3, QTableWidgetItem(f"{r['paid']:.2f}"))
            self.sales_table.setItem(i, 4, QTableWidgetItem(f"{r['change_amount']:.2f}"))
            self.sales_table.setItem(i, 5, QTableWidgetItem(r.get("username") or "-"))
        self.sales_table.resizeColumnsToContents()

    def load_expiry_report(self):
        rows = self.db.get_expiry_report(days=30)
        self.expiry_table.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.expiry_table.setItem(i, 0, QTableWidgetItem(r["barcode"]))
            self.expiry_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.expiry_table.setItem(i, 2, QTableWidgetItem(str(r["stock_qty"])))
            self.expiry_table.setItem(i, 3, QTableWidgetItem(r["expiry_date"] or "-"))
            self.expiry_table.setItem(i, 4, QTableWidgetItem(r["expiry_status"]))

        self.expiry_table.resizeColumnsToContents()

    def load_login_history(self):
        rows = self.db.get_login_history(200)
        self.login_table.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.login_table.setItem(i, 0, QTableWidgetItem(r["username"]))
            self.login_table.setItem(i, 1, QTableWidgetItem(r["role"]))
            self.login_table.setItem(i, 2, QTableWidgetItem(r["login_at"]))
            self.login_table.setItem(i, 3, QTableWidgetItem(r["logout_at"] or "-"))
            self.login_table.setItem(i, 4, QTableWidgetItem(r["status"]))
            self.login_table.setItem(i, 5, QTableWidgetItem(str(r["id"])))

        self.login_table.resizeColumnsToContents()

    def refresh_reports(self):
        self.load_sales_report()
        self.load_expiry_report()
        self.load_login_history()

    def closeEvent(self, event):
        if self.login_history_id:
            self.db.log_logout(self.login_history_id)
        super().closeEvent(event)
