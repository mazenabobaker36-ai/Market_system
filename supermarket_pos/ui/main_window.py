from PyQt5.QtCore import QDate, Qt
from datetime import datetime, date, timedelta
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QDialog,
    QSpinBox,
    QTabWidget,
)

from ui.dashboard_tab import DashboardTab
from ui.invoices_admin_tab import InvoicesAdminTab
from ui.stock_window import StockWindow
from ui.user_admin_tab import UserAdminTab
from utils.invoice_pdf import generate_invoice_pdf


class MainWindow(QMainWindow):
    def __init__(self, db, current_user, login_history_id=None):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.login_history_id = login_history_id
        self.current_product = None
        self.cart = []

        self.user_role = (self.current_user.get("role") or "").strip().lower()
        self.nav_buttons = {}
        self.sidebar_collapsed = False

        role_display_map = {
            "owner": "المالك",
            "admin": "المدير",
            "saler": "البائع",
        }
        role_display = role_display_map.get(self.user_role, current_user.get("role", "-"))

        self.setWindowTitle(f"نظام السوبرماركت - المستخدم: {current_user['username']} ({role_display})")
        self.resize(1360, 860)

        self._build_shell()
        self._build_pages()
        self._apply_role_permissions()

        # load customers/suppliers data
        try:
            self.load_customers()
        except Exception:
            pass
        try:
            self.load_suppliers()
        except Exception:
            pass
        # populate customer combo used in POS
        try:
            self.refresh_customer_combo()
        except Exception:
            pass

        self.refresh_reports()

    # ------------------------------------------------------------------
    # Shell / Sidebar
    # ------------------------------------------------------------------
    def _build_shell(self):
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(260)
        self.sidebar.setMaximumWidth(260)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(8)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("☰ القائمة")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.toggle_btn.setObjectName("sidebarToggleBtn")

        self.brand_label = QLabel("🛒 Supermarket POS")
        self.brand_label.setObjectName("pageTitleLabel")

        sidebar_layout.addWidget(self.toggle_btn)
        sidebar_layout.addWidget(self.brand_label)

        self.menu_container = QVBoxLayout()
        self.menu_container.setSpacing(6)
        sidebar_layout.addLayout(self.menu_container)
        sidebar_layout.addStretch()

        self.profile_badge = QLabel(
            f"👤 {self.current_user.get('username', '-')}\n{self.current_user.get('role', '-')}"
        )
        self.profile_badge.setObjectName("profileBadge")
        self.profile_badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sidebar_layout.addWidget(self.profile_badge)

        # Logout button and footer info
        self.logout_btn = QPushButton("تسجيل الخروج")
        self.logout_btn.setProperty("variant", "danger")
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        footer_lbl = QLabel("● System Online")
        footer_lbl.setObjectName("sidebarFooterLabel")
        sidebar_layout.addWidget(footer_lbl)

        # Content area
        self.content = QFrame()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(12, 12, 12, 12)

        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content, 1)

    def _add_nav_item(self, key: str, title: str, widget: QWidget):
        index = self.pages.addWidget(widget)

        btn = QPushButton(title)
        btn.setCheckable(True)
        btn.setObjectName("navMenuBtn")
        btn.clicked.connect(lambda: self.switch_page(key))

        self.menu_container.addWidget(btn)
        self.nav_buttons[key] = {"button": btn, "index": index, "title": title}

    def switch_page(self, key: str):
        if key not in self.nav_buttons:
            return

        for k, meta in self.nav_buttons.items():
            meta["button"].setChecked(k == key)

        self.pages.setCurrentIndex(self.nav_buttons[key]["index"])
        # when showing POS, reload product side-panel to reflect live inventory changes
        try:
            if key == 'pos':
                self.load_products_side_panel()
        except Exception:
            pass

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        width = 84 if self.sidebar_collapsed else 260
        self.sidebar.setMinimumWidth(width)
        self.sidebar.setMaximumWidth(width)

        for meta in self.nav_buttons.values():
            text = "•" if self.sidebar_collapsed else meta["title"]
            meta["button"].setText(text)

        self.brand_label.setText("🛒" if self.sidebar_collapsed else "🛒 Supermarket POS")
        self.toggle_btn.setText("☰" if self.sidebar_collapsed else "☰ القائمة")
        self.profile_badge.setVisible(not self.sidebar_collapsed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # سلوك قريب من off-canvas على الشاشات الصغيرة
        if self.width() < 980 and not self.sidebar_collapsed:
            self.toggle_sidebar()
        elif self.width() >= 980 and self.sidebar_collapsed:
            self.toggle_sidebar()

    # ------------------------------------------------------------------
    # Build pages
    # ------------------------------------------------------------------
    def _build_pages(self):
        self.pos_tab = self._build_pos_tab()
        self.dashboard_tab = DashboardTab(self.db)
        self.customer_tab = self._build_customer_tab()
        self.stock_tab = StockWindow(self.db, current_user_role=self.user_role)
        self.reports_tab = self._build_reports_tab()

        self._add_nav_item("pos", "🧾 نقطة البيع", self.pos_tab)
        # Ensure POS product list refreshes when inventory changes
        try:
            if hasattr(self.stock_tab, 'save_btn'):
                self.stock_tab.save_btn.clicked.connect(lambda: self.load_products_side_panel())
            if hasattr(self.stock_tab, 'refresh_btn'):
                self.stock_tab.refresh_btn.clicked.connect(lambda: self.load_products_side_panel())
        except Exception:
            pass
        self._add_nav_item("dashboard", "📊 لوحة التحكم", self.dashboard_tab)
        self._add_nav_item("customers", "👥 العملاء", self.customer_tab)
        self._add_nav_item("stock", "📦 المخزون", self.stock_tab)
        self._add_nav_item("reports", "📈 التقارير", self.reports_tab)

        self.invoices_admin_tab = None
        self.user_admin_tab = None

        if self.user_role in {"admin", "owner"}:
            self.invoices_admin_tab = InvoicesAdminTab(self.db)
            self._add_nav_item("invoices", "👁️ الفواتير وسجل المبيعات", self.invoices_admin_tab)

            self.user_admin_tab = UserAdminTab(self.db, self.current_user)
            self._add_nav_item("users", "🛡️ إدارة المستخدمين", self.user_admin_tab)

        # Hook dashboard quick links to invoices/reports pages
        target_tab = "invoices" if self.invoices_admin_tab else "reports"
        try:
            # Recent Activity -> Reports (Activity Logs)
            if hasattr(self.dashboard_tab, "view_all_btn"):
                self.dashboard_tab.view_all_btn.clicked.connect(lambda: self.switch_page('reports'))

            # Recent Sales -> Invoices (Sales History)
            if hasattr(self.dashboard_tab, "view_sales_btn"):
                self.dashboard_tab.view_sales_btn.clicked.connect(lambda: self.switch_page('invoices' if self.invoices_admin_tab else 'reports'))

            # new sale should go to POS
            if hasattr(self.dashboard_tab, "new_sale_btn"):
                self.dashboard_tab.new_sale_btn.clicked.connect(lambda: self.switch_page('pos'))

            # connect recent sales double-click to open invoice view
            self.dashboard_tab.recent_sales_table.doubleClicked.connect(self._open_invoice_from_sales_table)

            # connect reports sales table double-click as well
            if hasattr(self, 'sales_table'):
                self.sales_table.doubleClicked.connect(self._open_invoice_from_sales_table)

            # connect shortcut cards
            if hasattr(self.dashboard_tab, 'shortcut_cards'):
                for lbl, btn in self.dashboard_tab.shortcut_cards.items():
                    # Suppliers & Customers -> customers page
                    if lbl in ('Customers', 'Suppliers'):
                        btn.clicked.connect(lambda _, t='customers': self.switch_page(t))
                    # Categories and stock-related shortcuts -> inventory page
                    elif lbl in ('Categories', 'Stock IN Today'):
                        btn.clicked.connect(lambda _, t='stock': self.switch_page(t))
                    else:
                        # fallback
                        btn.clicked.connect(lambda _, t='stock': self.switch_page(t))
        except Exception:
            pass

        # Ensure invoices table double-click also opens dialog (for admin)
        if self.invoices_admin_tab:
            try:
                self.invoices_admin_tab.invoices_table.doubleClicked.connect(lambda *_: self.invoices_admin_tab.open_selected_invoice())
            except Exception:
                pass

        self.switch_page("pos")

    def _open_invoice_from_sales_table(self, index):
        # index: QModelIndex from double click
        row = index.row()
        try:
            invoice_no_item = self.dashboard_tab.recent_sales_table.item(row, 0)
            if not invoice_no_item:
                return
            invoice_no = invoice_no_item.text()
            # find invoice id via admin list helper
            matches = self.db.list_invoices_admin(invoice_no)
            if not matches:
                QMessageBox.warning(self, "تنبيه", "تعذر العثور على الفاتورة")
                return
            invoice_id = matches[0]["id"]
            invoice = self.db.get_invoice_details(int(invoice_id))
            from ui.invoice_view_dialog import InvoiceViewDialog
            dialog = InvoiceViewDialog(invoice, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _open_invoice_by_invoice_no(self, invoice_no: str):
        matches = self.db.list_invoices_admin(invoice_no)
        if not matches:
            QMessageBox.warning(self, "تنبيه", "تعذر العثور على الفاتورة")
            return
        invoice_id = matches[0]["id"]
        invoice = self.db.get_invoice_details(int(invoice_id))
        from ui.invoice_view_dialog import InvoiceViewDialog
        dialog = InvoiceViewDialog(invoice, self)
        dialog.exec_()

    def _apply_role_permissions(self):
        if self.user_role == "saler":
            # Prevent saler from accessing dashboard and admin sections
            if "stock" in self.nav_buttons:
                self.nav_buttons["stock"]["button"].setEnabled(False)
            if "reports" in self.nav_buttons:
                self.nav_buttons["reports"]["button"].setEnabled(False)
            if "dashboard" in self.nav_buttons:
                # hide dashboard from saler
                self.nav_buttons["dashboard"]["button"].setVisible(False)
            # default landing page for saler should be POS
            try:
                self.switch_page("pos")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Logout Handler
    # ------------------------------------------------------------------
    def handle_logout(self):
        reply = QMessageBox.question(
            self,
            "تأكيد تسجيل الخروج",
            "هل أنت متأكد أنك تريد تسجيل الخروج؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            # record logout time if available
            if getattr(self, 'login_history_id', None):
                try:
                    self.db.log_logout(self.login_history_id)
                except Exception:
                    pass
        except Exception:
            pass

        # close current window and show login dialog
        try:
            from ui.login_dialog import LoginDialog
            self.hide()
            dlg = LoginDialog(self.db)
            if dlg.exec_() == QDialog.Accepted:
                # open a new main window for the new user
                new_user = dlg.user
                new_login_history_id = dlg.login_history_id
                mw = MainWindow(self.db, new_user, new_login_history_id)
                mw.show()
                self.close()
            else:
                # user cancelled login -> exit app
                self.close()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    # ------------------------------------------------------------------
    # POS PAGE
    # ------------------------------------------------------------------
    def _build_pos_tab(self):
        # Main POS container with a right-side product quick-selection panel
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Main area (left) - scanner, cart, payment
        pos_container = QWidget()
        layout = QVBoxLayout(pos_container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        scan_box = QGroupBox("مسح رمز QR / الباركود")
        scan_layout = QGridLayout(scan_box)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("امسح الباركود/QR ثم اضغط Enter")
        self.barcode_input.returnPressed.connect(self.on_scan_barcode)

        self.product_label = QLabel("المنتج: -")

        self.qty_input = QLineEdit("1")
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("السعر اليدوي")
        self.price_input.returnPressed.connect(self.add_item_to_cart)

        self.add_btn = QPushButton("إضافة للسلة")
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(self.add_item_to_cart)

        scan_layout.addWidget(QLabel("QR/باركود:"), 0, 0)
        scan_layout.addWidget(self.barcode_input, 0, 1, 1, 3)
        scan_layout.addWidget(self.product_label, 1, 0, 1, 4)
        scan_layout.addWidget(QLabel("الكمية:"), 2, 0)
        scan_layout.addWidget(self.qty_input, 2, 1)
        scan_layout.addWidget(QLabel("السعر:"), 2, 2)
        scan_layout.addWidget(self.price_input, 2, 3)
        scan_layout.addWidget(self.add_btn, 3, 0, 1, 4)

        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels([
            "معرف المنتج",
            "الباركود",
            "الاسم",
            "الكمية",
            "السعر",
            "الإجمالي",
        ])
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.verticalHeader().setVisible(False)
        # allow inline editing for price column; handle changes
        self.cart_table.itemChanged.connect(self._on_cart_item_changed)

        payment_box = QGroupBox("الدفع")
        payment_layout = QFormLayout(payment_box)

        self.customer_combo = QComboBox()
        self.total_label = QLabel("0.00")

        # Editable final total (override / discount). Use QDoubleSpinBox for numeric entry.
        self.final_total_spin = QDoubleSpinBox()
        self.final_total_spin.setPrefix("")
        self.final_total_spin.setSuffix("")
        self.final_total_spin.setDecimals(2)
        self.final_total_spin.setMaximum(9999999.99)
        self.final_total_spin.setValue(0.00)
        self.final_total_spin.setSingleStep(0.5)
        self.final_total_spin.valueChanged.connect(self._on_final_total_changed)
        self._final_total_overridden = False

        # Simplified payment flow: no paid/change inputs - finalizing sale uses final_total_spin
        self.checkout_btn = QPushButton("إتمام البيع")
        self.checkout_btn.setProperty("variant", "success")
        self.checkout_btn.clicked.connect(self.checkout)

        self.clear_btn = QPushButton("تفريغ السلة")
        self.clear_btn.setProperty("variant", "danger")
        self.clear_btn.clicked.connect(self.clear_cart)

        payment_layout.addRow("العميل:", self.customer_combo)
        payment_layout.addRow("الإجمالي (محسوب):", self.total_label)
        payment_layout.addRow("الإجمالي النهائي:", self.final_total_spin)

        payment_actions = QHBoxLayout()
        payment_actions.addWidget(self.checkout_btn)
        payment_actions.addWidget(self.clear_btn)
        payment_layout.addRow(payment_actions)

        layout.addWidget(scan_box)
        layout.addWidget(self.cart_table)
        layout.addWidget(payment_box)

        # Product side panel (right)
        panel = QGroupBox("المنتجات")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(8)

        self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText("بحث عن منتج...")
        self.product_search_input.textChanged.connect(lambda txt: self._filter_products_side(txt))
        panel_layout.addWidget(self.product_search_input)

        # simple category pills
        pills_row = QHBoxLayout()
        self.category_buttons = {}
        categories = ["All", "Drinks", "Snacks", "Bakery", "General"]
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            if cat == "All":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=cat: self._filter_products_side(self.product_search_input.text(), category=c))
            pills_row.addWidget(btn)
            self.category_buttons[cat] = btn
        panel_layout.addLayout(pills_row)

        self.products_scroll = QScrollArea()
        self.products_scroll.setWidgetResizable(True)
        self.products_container = QWidget()
        self.products_layout = QGridLayout(self.products_container)
        self.products_layout.setAlignment(Qt.AlignTop)
        self.products_layout.setSpacing(8)
        self.products_scroll.setWidget(self.products_container)

        panel_layout.addWidget(self.products_scroll)

        root_layout.addWidget(pos_container, 3)
        root_layout.addWidget(panel, 2)

        # store references
        self._products_panel = panel
        self._products_layout = self.products_layout
        self._products_container = self.products_container

        # initial load
        self.load_products_side_panel()

        return root

    def load_products_side_panel(self):
        # Load all products and render side panel (safe guard if DB error)
        try:
            products = self.db.list_products()
        except Exception:
            products = []

        # Only show available products (stock > 0)
        available = [p for p in products if float(p.get('stock_qty', 0)) > 0]
        self._all_products = products
        self._render_products(available)

    def _product_category(self, product: dict) -> str:
        name = (product.get("name") or "").lower()
        if any(k in name for k in ("milk", "cola", "pepsi", "juice", "drink", "water")):
            return "Drinks"
        if any(k in name for k in ("bread", "bakery", "bun", "cake")):
            return "Bakery"
        if any(k in name for k in ("chips", "snack", "crisps", "cookie")):
            return "Snacks"
        return "General"

    def _render_products(self, products: list):
        # clear layout
        while self._products_layout.count():
            it = self._products_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        cols = 2
        for idx, p in enumerate(products):
            row = idx // cols
            col = idx % cols
            name = p.get("name")
            price = float(p.get("default_price") or 0.0)
            stock = float(p.get("stock_qty") or 0)

            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(False)
            btn.setSizePolicy(btn.sizePolicy().Expanding, btn.sizePolicy().Fixed)
            text = f"{name}\n{price:.2f} | المخزون: {int(stock)}"
            btn.setText(text)
            btn.setProperty("product_id", p.get("id"))
            btn.setToolTip(name)

            if stock <= 0:
                btn.setEnabled(False)
                btn.setStyleSheet("background:#fff1f2; color:#7f1d1d;")
                btn.setText(text + "\n(نفد المخزون)")
            else:
                # Open selection dialog instead of adding directly
                btn.clicked.connect(lambda _, prod=p: self._select_product(prod))

            self._products_layout.addWidget(btn, row, col)

    def _filter_products_side(self, text: str = "", category: str = "All"):
        txt = (text or "").strip().lower()
        filtered = []
        for p in getattr(self, "_all_products", []):
            name = (p.get("name") or "").lower()
            cat = self._product_category(p)
            if category and category != "All" and cat != category:
                continue
            if txt and txt not in name and txt not in (p.get("barcode") or ""):
                continue
            filtered.append(p)

        # update pill checked states
        for c, btn in self.category_buttons.items():
            btn.setChecked(c == category)

        self._render_products(filtered)

    def _add_product_to_cart(self, product: dict):
        """Legacy helper preserved for compatibility. Prefer using _select_product which shows the pre-add dialog."""
        # keep behavior for programmatic adds
        if float(product.get("stock_qty", 0)) <= 0:
            QMessageBox.warning(self, "خارج المخزون", "المنتج غير متوفر حالياً")
            return

        pid = product.get("id")
        for item in self.cart:
            if item.get("product_id") == pid:
                if item["qty"] + 1 > float(product.get("stock_qty", 0)):
                    QMessageBox.warning(self, "مخزون غير كافٍ", "الكمية المطلوبة أكبر من المتاح")
                    return
                item["qty"] += 1
                self.refresh_cart()
                return

        base_price = float(product.get("default_price") or 0.0)
        self.cart.append({
            "product_id": pid,
            "barcode": product.get("barcode"),
            "name": product.get("name"),
            "qty": 1,
            "base_price": base_price,
            "manual_price": base_price,
        })
        self.refresh_cart()

    def _select_product(self, product: dict):
        """Open a selection dialog allowing price/qty edit before adding to cart."""
        dlg = QDialog(self)
        dlg.setWindowTitle("إضافة منتج")
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)

        # Product info (read-only)
        info_layout = QFormLayout()
        info_layout.addRow(QLabel("المنتج:"), QLabel(product.get("name") or "-"))
        info_layout.addRow(QLabel("الباركود:"), QLabel(product.get("barcode") or "-"))
        layout.addLayout(info_layout)

        # Price and quantity controls
        control_layout = QHBoxLayout()
        price_spin = QDoubleSpinBox()
        price_spin.setDecimals(2)
        price_spin.setMaximum(9999999.99)
        price_spin.setValue(float(product.get("default_price") or 0.0))
        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(int(float(product.get("stock_qty") or 0)))
        qty_spin.setValue(1)
        control_layout.addWidget(QLabel("السعر:"))
        control_layout.addWidget(price_spin)
        control_layout.addWidget(QLabel("الكمية:"))
        control_layout.addWidget(qty_spin)
        layout.addLayout(control_layout)

        # Subtotal display
        subtotal_lbl = QLabel(f"{price_spin.value() * qty_spin.value():.2f}")
        subtotal_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(QLabel("المجموع:"))
        layout.addWidget(subtotal_lbl)

        def _recalc():
            subtotal_lbl.setText(f"{price_spin.value() * qty_spin.value():.2f}")

        price_spin.valueChanged.connect(lambda _: _recalc())
        qty_spin.valueChanged.connect(lambda _: _recalc())

        # Action buttons
        actions = QHBoxLayout()
        add_btn = QPushButton("إضافة للفـاتورة")
        add_btn.setProperty("variant", "success")
        cancel_btn = QPushButton("إلغاء")
        actions.addStretch()
        actions.addWidget(add_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

        def _on_add():
            qty = int(qty_spin.value())
            price = float(price_spin.value())
            stock_avail = float(product.get("stock_qty") or 0)
            if qty <= 0:
                QMessageBox.warning(dlg, "خطأ", "الكمية يجب أن تكون أكبر من صفر")
                return
            if qty > stock_avail:
                QMessageBox.warning(dlg, "مخزون غير كافٍ", "الكمية المطلوبة أكبر من المتاح")
                return

            # merge with existing item if present
            pid = product.get("id")
            for item in self.cart:
                if item.get("product_id") == pid:
                    # if prices differ, override with the new price
                    if item.get("manual_price") != price:
                        item["manual_price"] = price
                    item["qty"] += qty
                    self.refresh_cart()
                    dlg.accept()
                    return

            # not present - add new entry
            self.cart.append({
                "product_id": pid,
                "barcode": product.get("barcode"),
                "name": product.get("name"),
                "qty": qty,
                "base_price": float(product.get("default_price") or 0.0),
                "manual_price": price,
            })
            # reset any final total override
            self._final_total_overridden = False
            self.refresh_cart()
            dlg.accept()

        add_btn.clicked.connect(_on_add)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec_()

    def _build_customer_tab(self):
        # Tabbed container: Customers and Suppliers
        root = QWidget()
        root.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6,6,6,6)
        layout.setSpacing(8)

        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.RightToLeft)

        # --- Customers Tab ---
        cust_tab = QWidget()
        cust_tab.setLayoutDirection(Qt.RightToLeft)
        cl = QVBoxLayout(cust_tab)
        cl.setSpacing(8)

        hdr_row = QHBoxLayout()
        title = QLabel("إدارة العملاء")
        title.setObjectName("sectionTitleLabel")
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        self.btn_add_customer_new = QPushButton("+ إضافة عميل جديد")
        self.btn_add_customer_new.setProperty("variant", "primary")
        self.btn_add_customer_new.clicked.connect(lambda: self._clear_customer_form())
        hdr_row.addWidget(self.btn_add_customer_new)
        cl.addLayout(hdr_row)

        search_row = QHBoxLayout()
        self.customer_search_input = QLineEdit()
        self.customer_search_input.setPlaceholderText("بحث عن عميل (بالاسم أو رقم الهاتف)...")
        self.customer_search_input.textChanged.connect(self._filter_customers_table)
        search_row.addWidget(self.customer_search_input)
        cl.addLayout(search_row)

        # Customer form
        self.customer_form_box = QGroupBox("نموذج العميل")
        self.customer_form_box.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(self.customer_form_box)
        self.customer_name_input = QLineEdit()
        self.customer_phone_input = QLineEdit()
        self.customer_email_input = QLineEdit()
        self.customer_notes_input = QLineEdit()
        form.addRow("اسم العميل:", self.customer_name_input)
        form.addRow("رقم الهاتف:", self.customer_phone_input)
        form.addRow("البريد الإلكتروني:", self.customer_email_input)
        form.addRow("ملاحظات / الرصيد:", self.customer_notes_input)

        btns = QHBoxLayout()
        self.customer_save_btn = QPushButton("حفظ العميل")
        self.customer_save_btn.setProperty("variant", "success")
        self.customer_save_btn.clicked.connect(self.save_customer)
        self.customer_edit_btn = QPushButton("تعديل")
        self.customer_edit_btn.setProperty("variant", "primary")
        self.customer_edit_btn.clicked.connect(self._populate_customer_for_edit)
        self.customer_clear_btn = QPushButton("مسح الحقول")
        self.customer_clear_btn.setProperty("variant", "outline")
        self.customer_clear_btn.clicked.connect(self._clear_customer_form)
        btns.addWidget(self.customer_save_btn)
        btns.addWidget(self.customer_edit_btn)
        btns.addWidget(self.customer_clear_btn)
        form.addRow(btns)

        cl.addWidget(self.customer_form_box)

        # Customers table
        self.customers_table = QTableWidget(0, 6)
        self.customers_table.setHorizontalHeaderLabels([
            "المعرف", "اسم العميل", "رقم الهاتف", "البريد الإلكتروني", "الملاحظات", "الإجراءات",
        ])
        self.customers_table.verticalHeader().setVisible(False)
        self.customers_table.horizontalHeader().setStretchLastSection(True)
        cl.addWidget(self.customers_table)

        tabs.addTab(cust_tab, "العملاء")

        # --- Suppliers Tab ---
        sup_tab = QWidget()
        sup_tab.setLayoutDirection(Qt.RightToLeft)
        sl = QVBoxLayout(sup_tab)
        sl.setSpacing(8)

        hdr_row2 = QHBoxLayout()
        title2 = QLabel("إدارة الموردين")
        title2.setObjectName("sectionTitleLabel")
        hdr_row2.addWidget(title2)
        hdr_row2.addStretch()
        self.btn_add_supplier_new = QPushButton("+ إضافة مورد جديد")
        self.btn_add_supplier_new.setProperty("variant", "primary")
        self.btn_add_supplier_new.clicked.connect(lambda: self._clear_supplier_form())
        hdr_row2.addWidget(self.btn_add_supplier_new)
        sl.addLayout(hdr_row2)

        search_row2 = QHBoxLayout()
        self.supplier_search_input = QLineEdit()
        self.supplier_search_input.setPlaceholderText("بحث عن مورد (بالاسم أو الشركة)...")
        self.supplier_search_input.textChanged.connect(self._filter_suppliers_table)
        search_row2.addWidget(self.supplier_search_input)
        sl.addLayout(search_row2)

        # Supplier form
        self.supplier_form_box = QGroupBox("نموذج المورد")
        self.supplier_form_box.setLayoutDirection(Qt.RightToLeft)
        sform = QFormLayout(self.supplier_form_box)
        self.supplier_company_input = QLineEdit()
        self.supplier_contact_input = QLineEdit()
        self.supplier_phone_input = QLineEdit()
        self.supplier_address_input = QLineEdit()
        self.supplier_category_input = QLineEdit()
        sform.addRow("اسم المورد / الشركة:", self.supplier_company_input)
        sform.addRow("اسم الشخص المسؤول:", self.supplier_contact_input)
        sform.addRow("رقم الهاتف:", self.supplier_phone_input)
        sform.addRow("العنوان:", self.supplier_address_input)
        sform.addRow("نوع البضاعة / المنتجات:", self.supplier_category_input)

        sbtns = QHBoxLayout()
        self.supplier_save_btn = QPushButton("حفظ المورد")
        self.supplier_save_btn.setProperty("variant", "success")
        self.supplier_save_btn.clicked.connect(self.save_supplier)
        self.supplier_edit_btn = QPushButton("تعديل")
        self.supplier_edit_btn.setProperty("variant", "primary")
        self.supplier_edit_btn.clicked.connect(self._populate_supplier_for_edit)
        self.supplier_clear_btn = QPushButton("مسح الحقول")
        self.supplier_clear_btn.setProperty("variant", "outline")
        self.supplier_clear_btn.clicked.connect(self._clear_supplier_form)
        sbtns.addWidget(self.supplier_save_btn)
        sbtns.addWidget(self.supplier_edit_btn)
        sbtns.addWidget(self.supplier_clear_btn)
        sform.addRow(sbtns)

        sl.addWidget(self.supplier_form_box)

        # Suppliers table
        self.suppliers_table = QTableWidget(0, 7)
        self.suppliers_table.setHorizontalHeaderLabels([
            "المعرف", "اسم المورد / الشركة", "جهة الاتصال", "رقم الهاتف", "العنوان", "المنتجات الموردة", "الإجراءات",
        ])
        self.suppliers_table.verticalHeader().setVisible(False)
        self.suppliers_table.horizontalHeader().setStretchLastSection(True)
        sl.addWidget(self.suppliers_table)

        tabs.addTab(sup_tab, "الموردون")

        layout.addWidget(tabs)

        # initial state
        self._editing_customer_id = None
        self._editing_supplier_id = None

        # load data
        self.load_customers()
        self.load_suppliers()

        return root

    def _build_reports_tab(self):
        # Convert the long reports page into a 3-tab interface for clarity
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.RightToLeft)

        # ----------------------- Tab 1: Expiry & Low Stock -----------------------
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_layout.setContentsMargins(8, 8, 8, 8)
        t1_layout.setSpacing(8)

        stock_box = QGroupBox("تقرير المنتجات المنتهية وقليلة المخزون")
        stock_layout = QVBoxLayout(stock_box)
        stock_btn = QPushButton("تحديث البيانات 🔄")
        stock_btn.setProperty("variant", "primary")
        stock_btn.clicked.connect(self.load_stock_report)
        stock_layout.addWidget(stock_btn)
        stock_layout.addSpacing(12)

        self.expiry_table = QTableWidget(0, 5)
        # improve table row height for readability
        try:
            self.expiry_table.verticalHeader().setDefaultSectionSize(40)
        except Exception:
            pass
        self.expiry_table.setHorizontalHeaderLabels([
            "الباركود", "اسم المنتج", "الكمية المتبقية", "تاريخ الانتهاء", "حالة المنتج",
        ])
        self.expiry_table.verticalHeader().setVisible(False)
        self.expiry_table.horizontalHeader().setStretchLastSection(True)
        self.expiry_table.setMinimumHeight(220)
        stock_layout.addWidget(self.expiry_table)

        t1_layout.addWidget(stock_box)
        t1_layout.addStretch()
        tabs.addTab(tab1, "المنتهية / منخفضة المخزون")

        # ----------------------- Tab 2: Login History ----------------------------
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        t2_layout.setContentsMargins(8, 8, 8, 8)
        t2_layout.setSpacing(8)

        login_box = QGroupBox("سجل دخول وخروج المستخدمين")
        login_layout = QVBoxLayout(login_box)
        login_btn = QPushButton("تحديث السجل 🔄")
        login_btn.setProperty("variant", "outline")
        login_btn.clicked.connect(self.load_login_logs)
        login_layout.addWidget(login_btn)
        login_layout.addSpacing(12)

        self.login_table = QTableWidget(0, 6)
        try:
            self.login_table.verticalHeader().setDefaultSectionSize(40)
        except Exception:
            pass
        self.login_table.setHorizontalHeaderLabels([
            "المعرف", "اسم المستخدم", "الدور / الصلاحية", "وقت الدخول", "وقت الخروج", "الحالة",
        ])
        self.login_table.verticalHeader().setVisible(False)
        self.login_table.horizontalHeader().setStretchLastSection(True)
        self.login_table.setMinimumHeight(220)
        login_layout.addWidget(self.login_table)

        t2_layout.addWidget(login_box)
        t2_layout.addStretch()
        tabs.addTab(tab2, "سجل الدخول")

        # ----------------------- Tab 3: Sales & Analytics -----------------------
        tab3 = QWidget()
        t3_layout = QVBoxLayout(tab3)
        t3_layout.setContentsMargins(8, 8, 8, 8)
        t3_layout.setSpacing(8)

        sales_box = QGroupBox("تقرير المبيعات والتحليلات")
        sales_layout = QVBoxLayout(sales_box)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("من تاريخ:"))
        self.sales_start_date = QDateEdit()
        self.sales_start_date.setCalendarPopup(True)
        self.sales_start_date.setDate(QDate.currentDate().addDays(-7))
        date_row.addWidget(self.sales_start_date)

        date_row.addWidget(QLabel("إلى تاريخ:"))
        self.sales_end_date = QDateEdit()
        self.sales_end_date.setCalendarPopup(True)
        self.sales_end_date.setDate(QDate.currentDate())
        date_row.addWidget(self.sales_end_date)

        load_sales_btn = QPushButton("تحميل تقرير المبيعات 📊")
        load_sales_btn.setProperty("variant", "primary")
        load_sales_btn.clicked.connect(self.load_sales_analytics_report)
        date_row.addWidget(load_sales_btn)

        sales_layout.addLayout(date_row)
        sales_layout.addSpacing(12)

        self.sales_table = QTableWidget(0, 4)
        try:
            self.sales_table.verticalHeader().setDefaultSectionSize(40)
        except Exception:
            pass
        self.sales_table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "التاريخ والوقت", "إجمالي الفاتورة", "اسم الكاشير",
        ])
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.horizontalHeader().setStretchLastSection(True)
        self.sales_table.setMinimumHeight(220)
        sales_layout.addWidget(self.sales_table)

        cards_row = QHBoxLayout()
        self.total_revenue_lbl = QLabel("إجمالي: 0.00 $")
        self.total_revenue_lbl.setObjectName("statValueLabel")
        cards_row.addWidget(self._summary_card("إجمالي المبيعات بالفترة", self.total_revenue_lbl))
        self.most_sold_lbl = QLabel("-")
        cards_row.addWidget(self._summary_card("الأكثر مبيعاً 🟢", self.most_sold_lbl))
        self.least_sold_lbl = QLabel("-")
        cards_row.addWidget(self._summary_card("الأقل مبيعاً 🔴", self.least_sold_lbl))

        sales_layout.addLayout(cards_row)

        t3_layout.addWidget(sales_box)
        t3_layout.addStretch()
        tabs.addTab(tab3, "المبيعات والتحليلات")

        # container
        container = QWidget()
        container.setLayoutDirection(Qt.RightToLeft)
        outer = QVBoxLayout(container)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.addWidget(tabs)
        return container

    def _summary_card(self, title: str, widget: QWidget):
        """Create a small summary card with title and a content widget."""
        box = QGroupBox()
        box.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(box)
        t = QLabel(title)
        t.setObjectName("smallCardTitle")
        layout.addWidget(t)
        widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        box.setFixedWidth(220)
        return box

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
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
        # update cart table rows and totals
        # block itemChanged while programmatically updating
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(self.cart))
        total = 0.0

        for row, item in enumerate(self.cart):
            subtotal = item["qty"] * item["manual_price"]
            total += subtotal

            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item["product_id"])))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item["barcode"]))
            self.cart_table.setItem(row, 2, QTableWidgetItem(item["name"]))

            qty_item = QTableWidgetItem(str(item["qty"]))
            qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 3, qty_item)

            price_item = QTableWidgetItem(f"{item['manual_price']:.2f}")
            price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)
            self.cart_table.setItem(row, 4, price_item)

            subtotal_item = QTableWidgetItem(f"{subtotal:.2f}")
            subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 5, subtotal_item)

        self.total_label.setText(f"{total:.2f}")
        self.cart_table.resizeColumnsToContents()
        self.cart_table.blockSignals(False)

    def clear_cart(self):
        self.cart = []
        self.refresh_cart()

    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة")
            return

        # Simplified payment: use final_total_spin value as paid amount and adjust cart prices if overridden
        computed_total = sum(item['qty'] * item['manual_price'] for item in self.cart)
        # if final total overridden, adjust item manual_price proportionally
        final_total = float(self.final_total_spin.value()) if hasattr(self, 'final_total_spin') else computed_total
        if computed_total > 0 and abs(final_total - computed_total) > 0.001:
            ratio = final_total / computed_total
            for item in self.cart:
                # apply ratio to base_price if present else current manual_price
                base = float(item.get('base_price', item.get('manual_price', 0.0)))
                item['manual_price'] = round(base * ratio, 2)
        paid = final_total
        change_amount = 0.0

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

            QMessageBox.information(
                self,
                "نجاح",
                "تم تأكيد الدفع بنجاح",
            )

            # After successful invoice creation, reset POS session and refresh views
            self.reset_pos_session()
            try:
                self.dashboard_tab.refresh()
            except Exception:
                pass
            self.refresh_reports()
            try:
                self.stock_tab.refresh_table()
            except Exception:
                pass
            if self.invoices_admin_tab:
                self.invoices_admin_tab.refresh_invoices()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _on_cart_item_changed(self, item):
        try:
            row = item.row()
            col = item.column()
            # columns: 0 id,1 barcode,2 name,3 qty,4 price,5 subtotal
            if col == 4:
                # price edited
                text = item.text().strip()
                text = text.replace(',', '.')
                try:
                    val = float(text)
                except ValueError:
                    QMessageBox.warning(self, "خطأ", "السعر يجب أن يكون رقمًا")
                    # revert to model value
                    self.refresh_cart()
                    return
                # update model
                if 0 <= row < len(self.cart):
                    self.cart[row]['manual_price'] = val
                    # update subtotal cell
                    subtotal = self.cart[row]['qty'] * val
                    self.cart_table.blockSignals(True)
                    self.cart_table.setItem(row, 5, QTableWidgetItem(f"{subtotal:.2f}"))
                    self.cart_table.blockSignals(False)
                    # update totals
                    total = sum(i['qty'] * i['manual_price'] for i in self.cart)
                    self.total_label.setText(f"{total:.2f}")
                    # editing an individual price clears any global final-total override
                    try:
                        self._final_total_overridden = False
                        if hasattr(self, 'final_total_spin'):
                            self.final_total_spin.blockSignals(True)
                            self.final_total_spin.setValue(total)
                            self.final_total_spin.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_final_total_changed(self, value: float):
        """Handler when cashier edits final total. Scale item prices proportionally to match new final total.
        If final total equals computed total, clear override flag."""
        try:
            computed_total = sum(i['qty'] * i['manual_price'] for i in self.cart)
            final_total = float(value)
            if computed_total <= 0:
                return
            if abs(final_total - computed_total) < 0.001:
                # no override
                self._final_total_overridden = False
                return
            # apply proportional scaling based on base_price if available
            ratio = final_total / computed_total
            for item in self.cart:
                base = float(item.get('base_price', item.get('manual_price', 0.0)))
                item['manual_price'] = round(base * ratio, 2)
            self._final_total_overridden = True
            # refresh display
            self.refresh_cart()
        except Exception:
            pass

    def reset_pos_session(self):
        """Clear cart, reset totals and final total override, reload products, and focus barcode input."""
        try:
            self.cart = []
            self.refresh_cart()
        except Exception:
            pass

        # reset final total spin
        try:
            if hasattr(self, 'final_total_spin'):
                self._final_total_overridden = False
                self.final_total_spin.blockSignals(True)
                self.final_total_spin.setValue(0.00)
                self.final_total_spin.blockSignals(False)
        except Exception:
            pass

        # reload products side panel to reflect updated stock
        try:
            self.load_products_side_panel()
        except Exception:
            pass

        # reset focus to barcode input
        try:
            self.barcode_input.setFocus()
            self.barcode_input.selectAll()
        except Exception:
            pass

    def add_customer(self):
        # kept for compatibility: delegate to save_customer
        self.save_customer()


    def load_customers(self):
        try:
            rows = self.db.list_customers()
        except Exception:
            rows = []
        self._all_customers = rows
        # apply current search filter
        query = (getattr(self, 'customer_search_input', None).text().strip().lower()) if hasattr(self, 'customer_search_input') else ''
        filtered = [r for r in rows if not query or query in (r.get('name') or '').lower() or query in (r.get('phone') or '').lower()]
        self.customers_table.setRowCount(len(filtered))
        for i, r in enumerate(filtered):
            self.customers_table.setItem(i, 0, QTableWidgetItem(str(r.get('id'))))
            self.customers_table.setItem(i, 1, QTableWidgetItem(r.get('name') or '-'))
            self.customers_table.setItem(i, 2, QTableWidgetItem(r.get('phone') or '-'))
            self.customers_table.setItem(i, 3, QTableWidgetItem(r.get('email') or '-'))
            self.customers_table.setItem(i, 4, QTableWidgetItem(r.get('notes') or '-'))

            # actions
            btns = QWidget()
            hb = QHBoxLayout(btns)
            hb.setContentsMargins(0,0,0,0)
            edit = QPushButton('تعديل')
            edit.setProperty('variant','primary')
            edit.clicked.connect(lambda _, cid=r.get('id'): self._edit_customer(cid))
            delete = QPushButton('حذف')
            delete.setProperty('variant','danger')
            delete.clicked.connect(lambda _, cid=r.get('id'): self.delete_customer(cid))
            hb.addWidget(edit)
            hb.addWidget(delete)
            self.customers_table.setCellWidget(i, 5, btns)
        self.customers_table.resizeColumnsToContents()

    def _filter_customers_table(self, text: str = ''):
        # simple filter wrapper
        self.load_customers()

    def _clear_customer_form(self):
        self.customer_name_input.clear()
        self.customer_phone_input.clear()
        self.customer_email_input.clear()
        self.customer_notes_input.clear()
        self._editing_customer_id = None
        self.customer_save_btn.setText('حفظ العميل')

    def _edit_customer(self, customer_id: int):
        # populate form for edit
        cust = next((c for c in getattr(self, '_all_customers', []) if c.get('id') == customer_id), None)
        if not cust:
            QMessageBox.warning(self, 'خطأ', 'العميل غير موجود')
            return
        self._editing_customer_id = customer_id
        self.customer_name_input.setText(cust.get('name') or '')
        self.customer_phone_input.setText(cust.get('phone') or '')
        self.customer_email_input.setText(cust.get('email') or '')
        self.customer_notes_input.setText(cust.get('notes') or '')
        self.customer_save_btn.setText('تحديث')

    def _populate_customer_for_edit(self):
        # populate edit form based on currently selected table row
        sel = getattr(self, 'customers_table').selectedIndexes()
        if not sel:
            QMessageBox.warning(self, 'اختيار', 'يرجى تحديد صف للتعديل')
            return
        row = sel[0].row()
        try:
            cid = int(self.customers_table.item(row, 0).text())
        except Exception:
            QMessageBox.warning(self, 'خطأ', 'تعذر تحديد معرف العميل')
            return
        self._edit_customer(cid)

    def save_customer(self):
        name = self.customer_name_input.text().strip()
        phone = self.customer_phone_input.text().strip()
        email = self.customer_email_input.text().strip()
        notes = self.customer_notes_input.text().strip()
        if not name:
            QMessageBox.warning(self, 'تنبيه', 'اسم العميل مطلوب')
            return
        try:
            if self._editing_customer_id:
                self.db.update_customer(self._editing_customer_id, name, phone, email, notes)
                QMessageBox.information(self, 'نجاح', 'تم تحديث بيانات العميل')
            else:
                self.db.create_customer(name, phone, email, notes)
                QMessageBox.information(self, 'نجاح', 'تم إضافة العميل')
        except Exception as e:
            QMessageBox.critical(self, 'خطأ', str(e))
            return
        self._clear_customer_form()
        self.load_customers()
        self.refresh_customer_combo()

    def delete_customer(self, customer_id: int = None):
        if not customer_id:
            # try selected row
            sel = self.customers_table.selectedIndexes()
            if not sel:
                QMessageBox.warning(self, 'اختيار', 'يرجى تحديد صف للحذف')
                return
            row = sel[0].row()
            customer_id = int(self.customers_table.item(row, 0).text())
        reply = QMessageBox.question(self, 'تأكيد الحذف', 'هل أنت متأكد من حذف هذا العميل؟', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.db.delete_customer(customer_id)
            QMessageBox.information(self, 'تم الحذف', 'تم حذف العميل بنجاح')
            self.load_customers()
            self.refresh_customer_combo()
        except Exception as e:
            QMessageBox.critical(self, 'خطأ', str(e))

    def load_suppliers(self):
        try:
            rows = self.db.list_suppliers()
        except Exception:
            rows = []
        self._all_suppliers = rows
        query = (getattr(self, 'supplier_search_input', None).text().strip().lower()) if hasattr(self, 'supplier_search_input') else ''
        filtered = [r for r in rows if not query or query in (r.get('company_name') or '').lower() or query in (r.get('contact_person') or '').lower()]
        self.suppliers_table.setRowCount(len(filtered))
        for i, r in enumerate(filtered):
            self.suppliers_table.setItem(i, 0, QTableWidgetItem(str(r.get('id'))))
            self.suppliers_table.setItem(i, 1, QTableWidgetItem(r.get('company_name') or '-'))
            self.suppliers_table.setItem(i, 2, QTableWidgetItem(r.get('contact_person') or '-'))
            self.suppliers_table.setItem(i, 3, QTableWidgetItem(r.get('phone') or '-'))
            self.suppliers_table.setItem(i, 4, QTableWidgetItem(r.get('address') or '-'))
            self.suppliers_table.setItem(i, 5, QTableWidgetItem(r.get('category_supplied') or '-'))
            # actions
            btns = QWidget()
            hb = QHBoxLayout(btns)
            hb.setContentsMargins(0,0,0,0)
            edit = QPushButton('تعديل')
            edit.setProperty('variant','primary')
            edit.clicked.connect(lambda _, sid=r.get('id'): self._edit_supplier(sid))
            delete = QPushButton('حذف')
            delete.setProperty('variant','danger')
            delete.clicked.connect(lambda _, sid=r.get('id'): self.delete_supplier(sid))
            hb.addWidget(edit)
            hb.addWidget(delete)
            self.suppliers_table.setCellWidget(i, 6, btns)
        self.suppliers_table.resizeColumnsToContents()

    def _filter_suppliers_table(self, text: str = ''):
        self.load_suppliers()

    def _clear_supplier_form(self):
        self.supplier_company_input.clear()
        self.supplier_contact_input.clear()
        self.supplier_phone_input.clear()
        self.supplier_address_input.clear()
        self.supplier_category_input.clear()
        self._editing_supplier_id = None
        self.supplier_save_btn.setText('حفظ المورد')

    def _edit_supplier(self, supplier_id: int):
        sup = next((s for s in getattr(self, '_all_suppliers', []) if s.get('id') == supplier_id), None)
        if not sup:
            QMessageBox.warning(self, 'خطأ', 'المورد غير موجود')
            return
        self._editing_supplier_id = supplier_id
        self.supplier_company_input.setText(sup.get('company_name') or '')
        self.supplier_contact_input.setText(sup.get('contact_person') or '')
        self.supplier_phone_input.setText(sup.get('phone') or '')
        self.supplier_address_input.setText(sup.get('address') or '')
        self.supplier_category_input.setText(sup.get('category_supplied') or '')
        self.supplier_save_btn.setText('تحديث')

    def _populate_supplier_for_edit(self):
        sel = getattr(self, 'suppliers_table').selectedIndexes()
        if not sel:
            QMessageBox.warning(self, 'اختيار', 'يرجى تحديد صف للتعديل')
            return
        row = sel[0].row()
        try:
            sid = int(self.suppliers_table.item(row, 0).text())
        except Exception:
            QMessageBox.warning(self, 'خطأ', 'تعذر تحديد المعرف')
            return
        self._edit_supplier(sid)

    def save_supplier(self):
        name = self.supplier_company_input.text().strip()
        contact = self.supplier_contact_input.text().strip()
        phone = self.supplier_phone_input.text().strip()
        address = self.supplier_address_input.text().strip()
        category = self.supplier_category_input.text().strip()
        if not name:
            QMessageBox.warning(self, 'تنبيه', 'اسم المورد مطلوب')
            return
        try:
            if self._editing_supplier_id:
                self.db.update_supplier(self._editing_supplier_id, name, contact, phone, address, category)
                QMessageBox.information(self, 'نجاح', 'تم تحديث بيانات المورد')
            else:
                self.db.create_supplier(name, contact, phone, address, category)
                QMessageBox.information(self, 'نجاح', 'تم إضافة المورد')
        except Exception as e:
            QMessageBox.critical(self, 'خطأ', str(e))
            return
        self._clear_supplier_form()
        self.load_suppliers()

    def delete_supplier(self, supplier_id: int = None):
        if not supplier_id:
            sel = self.suppliers_table.selectedIndexes()
            if not sel:
                QMessageBox.warning(self, 'اختيار', 'يرجى تحديد صف للحذف')
                return
            row = sel[0].row()
            supplier_id = int(self.suppliers_table.item(row, 0).text())
        reply = QMessageBox.question(self, 'تأكيد الحذف', 'هل أنت متأكد من حذف هذا المورد؟', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.db.delete_supplier(supplier_id)
            QMessageBox.information(self, 'تم الحذف', 'تم حذف المورد بنجاح')
            self.load_suppliers()
        except Exception as e:
            QMessageBox.critical(self, 'خطأ', str(e))

    def refresh_customer_combo(self):
        try:
            self.customer_combo.clear()
        except Exception:
            return
        # default cash/no-customer option
        self.customer_combo.addItem('نقدي', -1)
        try:
            rows = self.db.list_customers()
            for c in rows:
                display = f"{c.get('name')} ({c.get('phone') or '-'})"
                self.customer_combo.addItem(display, c.get('id'))
        except Exception:
            pass

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
            # Status cell: show colored badge
            status_text = r.get("expiry_status", "-")
            status_lbl = QLabel(status_text)
            if status_text == "NEAR_EXPIRY":
                status_lbl.setObjectName("statusBadgeYellow")
            elif status_text == "EXPIRED":
                status_lbl.setObjectName("statusBadgeRed")
            else:
                status_lbl.setObjectName("statusBadgeGreen")
            status_lbl.setAlignment(Qt.AlignCenter)
            self.expiry_table.setItem(i, 0, QTableWidgetItem(r["barcode"]))
            self.expiry_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.expiry_table.setItem(i, 2, QTableWidgetItem(str(r["stock_qty"])))
            self.expiry_table.setItem(i, 3, QTableWidgetItem(r["expiry_date"] or "-"))
            self.expiry_table.setCellWidget(i, 4, status_lbl)

        self.expiry_table.resizeColumnsToContents()

    def load_stock_report(self):
        # Load all products and compute status based on stock and expiry
        try:
            products = self.db.list_products()
        except Exception:
            products = []

        self.expiry_table.setRowCount(len(products))
        today = date.today()
        for i, p in enumerate(products):
            barcode = p.get('barcode') or ''
            name = p.get('name') or ''
            stock_qty = float(p.get('stock_qty') or 0)
            expiry = p.get('expiry_date') or None

            # determine status
            status_text = 'سليم'
            bg_color = '#ffffff'
            status_badge = 'OK'
            try:
                if expiry:
                    exp_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                    if exp_date < today or stock_qty <= 0:
                        status_text = 'نفد / منتهي'
                        bg_color = '#fef2f2'
                        status_badge = 'نفد / منتهي'
                    elif (exp_date - today).days <= 7 or stock_qty <= 5:
                        status_text = 'قريب الانتهاء / مخزون منخفض'
                        bg_color = '#fffbeb'
                        status_badge = 'قريب الانتهاء'
                    else:
                        status_text = 'سليم'
                        bg_color = '#ffffff'
                        status_badge = 'سليم'
                else:
                    if stock_qty <= 0:
                        status_text = 'نفد / منتهي'
                        bg_color = '#fef2f2'
                        status_badge = 'نفد / منتهي'
                    elif stock_qty <= 5:
                        status_text = 'قليل المخزون'
                        bg_color = '#fffbeb'
                        status_badge = 'قليل'
                    else:
                        status_text = 'سليم'
                        bg_color = '#ffffff'
                        status_badge = 'سليم'
            except Exception:
                status_text = 'سليم'
                bg_color = '#ffffff'
                status_badge = 'سليم'

            items = [
                QTableWidgetItem(barcode),
                QTableWidgetItem(name),
                QTableWidgetItem(str(int(stock_qty)) if stock_qty.is_integer() else str(stock_qty)),
                QTableWidgetItem(expiry or '-'),
                QTableWidgetItem(status_text),
            ]
            for col, it in enumerate(items):
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.expiry_table.setItem(i, col, it)
                it.setBackground(QBrush(QColor(bg_color)))

        self.expiry_table.resizeColumnsToContents()

    def load_login_logs(self):
        rows = self.db.get_login_history(500)
        self.login_table.setRowCount(len(rows))

        role_map = {
            "Owner": "المالك",
            "Admin": "المدير",
            "Saler": "البائع",
            "UNKNOWN": "غير معروف",
        }

        for i, r in enumerate(rows):
            self.login_table.setItem(i, 0, QTableWidgetItem(str(r.get('id'))))
            self.login_table.setItem(i, 1, QTableWidgetItem(r.get('username') or '-'))
            self.login_table.setItem(i, 2, QTableWidgetItem(role_map.get(r.get('role'), r.get('role'))))
            self.login_table.setItem(i, 3, QTableWidgetItem(r.get('login_at') or '-'))
            self.login_table.setItem(i, 4, QTableWidgetItem(r.get('logout_at') or '-'))

            status = r.get('status') or ''
            status_text = 'ناجح' if status == 'SUCCESS' else 'فشل' if status == 'FAILED' else status
            status_lbl = QLabel(status_text)
            if status_text == 'ناجح':
                status_lbl.setStyleSheet('background:#dcfce7; color:#166534; padding:4px; border-radius:6px;')
            else:
                status_lbl.setStyleSheet('background:#fee2e2; color:#991b1b; padding:4px; border-radius:6px;')
            status_lbl.setAlignment(Qt.AlignCenter)
            self.login_table.setCellWidget(i, 5, status_lbl)

        self.login_table.resizeColumnsToContents()

    def load_sales_analytics_report(self):
        # Date range
        start = self.sales_start_date.date().toString('yyyy-MM-dd')
        end = self.sales_end_date.date().toString('yyyy-MM-dd')

        # Load sales rows
        rows = self.db.get_sales_report(start, end)
        self.sales_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.sales_table.setItem(i, 0, QTableWidgetItem(r.get('invoice_no')))
            self.sales_table.setItem(i, 1, QTableWidgetItem(r.get('created_at')))
            self.sales_table.setItem(i, 2, QTableWidgetItem(f"{r.get('total',0):.2f} $"))
            self.sales_table.setItem(i, 3, QTableWidgetItem(r.get('username') or '-'))
        self.sales_table.resizeColumnsToContents()

        # Analytics: total revenue
        with self.db._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(SUM(total),0) AS s FROM Invoices WHERE DATE(created_at) BETWEEN DATE(?) AND DATE(?)",
                (start, end),
            )
            total = cur.fetchone()[0] or 0.0

            # most/least sold items
            cur.execute(
                """
                SELECT p.name, SUM(ii.qty) as qty_sold
                FROM Invoice_Items ii
                JOIN Products p ON p.id = ii.product_id
                JOIN Invoices i ON i.id = ii.invoice_id
                WHERE DATE(i.created_at) BETWEEN DATE(?) AND DATE(?)
                GROUP BY p.id
                ORDER BY qty_sold DESC
                """,
                (start, end),
            )
            sold = cur.fetchall()

        self.total_revenue_lbl.setText(f"{total:.2f} $")
        if sold:
            top = sold[0]
            self.most_sold_lbl.setText(f"{top[0]} — {int(top[1])}")
            bottom = sold[-1]
            self.least_sold_lbl.setText(f"{bottom[0]} — {int(bottom[1])}")
        else:
            self.most_sold_lbl.setText("-")
            self.least_sold_lbl.setText("-")

    def refresh_reports(self):
        # refresh all report sections
        self.load_stock_report()
        self.load_login_logs()
        # default sales analytics to last 7 days
        self.sales_start_date.setDate(QDate.currentDate().addDays(-7))
        self.sales_end_date.setDate(QDate.currentDate())
        self.load_sales_analytics_report()

    def closeEvent(self, event):
        if self.login_history_id:
            self.db.log_logout(self.login_history_id)
        super().closeEvent(event)
