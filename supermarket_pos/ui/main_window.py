import os
from pathlib import Path
from PyQt5.QtCore import QDate, QSize, QSizeF, Qt
from datetime import datetime, date, timedelta
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QTextDocument
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo
from PyQt5.QtWidgets import (
    QCheckBox,
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
    QShortcut,
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

from ui.categories_tab import CategoriesTab
from ui.dashboard_tab import DashboardTab
from ui.invoices_admin_tab import InvoicesAdminTab
from ui.stock_window import StockWindow
from ui.user_admin_tab import UserAdminTab
from utils.invoice_pdf import generate_invoice_pdf
from licensing import LicenseCheckWorker, LicenseLockOverlay, LicenseManager
from sync import SyncWorker


class SquareProductCard(QFrame):
    """Redesigned and expanded Product Card widget for POS quick menu grid."""
    def __init__(self, product: dict, on_click_callback, parent=None):
        super().__init__(parent)
        self.product = product
        self.on_click_callback = on_click_callback
        self.setMinimumSize(155, 172)
        self.setObjectName("squareProductCard")
        self.setAttribute(Qt.WA_Hover, True)
        self._build_ui()

    def _build_ui(self):
        stock = float(self.product.get("stock_qty") or 0)
        is_out = stock <= 0
        self.setCursor(Qt.ForbiddenCursor if is_out else Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        name = self.product.get("name") or "-"
        price = float(self.product.get("default_price") or 0.0)
        cat = (self.product.get("category") or "أخرى").strip() or "أخرى"
        img_path = self.product.get("image_path")
        barcode = self.product.get("barcode") or "-"

        # --- Top: Thumbnail Image or Clean Default Placeholder Icon (Height: 80px) ---
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(80)
        self.icon_label.setObjectName("squareCardImageContainer")
        pixmap = self._get_card_pixmap(img_path, cat, width=138, height=76)
        self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # --- Middle: Product Name in bold, high-contrast text (font-size: 14px) ---
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setObjectName("squareCardTitle")
        self.name_label.setWordWrap(True)
        self.name_label.setText(name)
        self.name_label.setToolTip(f"{name}\nالباركود: {barcode}\nالتصنيف: {cat}\nالسعر: {price:.2f} ج.م")
        layout.addWidget(self.name_label, 1)

        # --- Bottom: Price Badge & Stock Tag styled with distinct soft pill backgrounds ---
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(6)

        self.price_label = QLabel(f"{price:.2f} ج.م")
        self.price_label.setObjectName("squareCardPrice")
        self.price_label.setAlignment(Qt.AlignCenter)

        if is_out:
            self.stock_label = QLabel("نفد")
            self.stock_label.setObjectName("squareCardStockOut")
        elif stock <= 5:
            self.stock_label = QLabel(f"{int(stock)} 📦")
            self.stock_label.setObjectName("squareCardStockLow")
        else:
            self.stock_label = QLabel(f"{int(stock)} 📦")
            self.stock_label.setObjectName("squareCardStockOk")

        self.stock_label.setAlignment(Qt.AlignCenter)

        badge_row.addWidget(self.price_label, 1)
        badge_row.addWidget(self.stock_label, 1)
        layout.addLayout(badge_row)

        self._apply_card_style(is_out)

    def _apply_card_style(self, is_out: bool):
        if is_out:
            self.setStyleSheet(
                """
                QFrame#squareProductCard {
                    background-color: #fef2f2;
                    border: 1.5px solid #fecaca;
                    border-radius: 12px;
                }
                QLabel#squareCardTitle {
                    font-weight: 700;
                    font-size: 14px;
                    color: #991b1b;
                    background: transparent;
                }
                QLabel#squareCardPrice {
                    font-weight: 800;
                    font-size: 12px;
                    color: #dc2626;
                    background: #fee2e2;
                    border: 1px solid #fca5a5;
                    border-radius: 6px;
                    padding: 3px 6px;
                }
                QLabel#squareCardStockOut {
                    font-weight: 800;
                    font-size: 11px;
                    color: #dc2626;
                    background: #fee2e2;
                    border: 1px solid #fca5a5;
                    border-radius: 6px;
                    padding: 3px 6px;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QFrame#squareProductCard {
                    background-color: #ffffff;
                    border: 1.5px solid #e2e8f0;
                    border-radius: 12px;
                }
                QFrame#squareProductCard:hover {
                    background-color: #f8fafc;
                    border: 1.5px solid #2563eb;
                }
                QFrame#squareProductCard:pressed {
                    background-color: #eff6ff;
                    border: 1.5px solid #1d4ed8;
                }
                QLabel#squareCardTitle {
                    font-weight: 700;
                    font-size: 14px;
                    color: #0f172a;
                    background: transparent;
                }
                QLabel#squareCardPrice {
                    font-weight: 800;
                    font-size: 12px;
                    color: #1d4ed8;
                    background: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 6px;
                    padding: 3px 6px;
                }
                QLabel#squareCardStockOk {
                    font-weight: 700;
                    font-size: 11px;
                    color: #047857;
                    background: #ecfdf5;
                    border: 1px solid #a7f3d0;
                    border-radius: 6px;
                    padding: 3px 6px;
                }
                QLabel#squareCardStockLow {
                    font-weight: 700;
                    font-size: 11px;
                    color: #b45309;
                    background: #fffbeb;
                    border: 1px solid #fde68a;
                    border-radius: 6px;
                    padding: 3px 6px;
                }
                """
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            stock = float(self.product.get("stock_qty") or 0)
            if stock <= 0:
                return
            if callable(self.on_click_callback):
                self.on_click_callback(self.product)
        super().mousePressEvent(event)

    def _get_card_pixmap(self, image_path: Optional[str], category: str, width: int = 138, height: int = 76) -> QPixmap:
        if image_path and os.path.isfile(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                return pm.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        pm = QPixmap(width, height)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#f1f5f9")))
        painter.setPen(QColor("#e2e8f0"))
        painter.drawRoundedRect(2, 2, width - 4, height - 4, 8, 8)

        icons = {
            "مشروبات": "🥤",
            "Drinks": "🥤",
            "أطعمة": "🍟",
            "Food": "🍟",
            "Snacks": "🍟",
            "مخبوزات": "🥐",
            "Bakery": "🥐",
            "منظفات": "🧼",
            "Cleaning": "🧼",
            "ألبان": "🥛",
            "Dairy": "🥛",
            "حلويات": "🍫",
            "Sweets": "🍫",
            "إلكترونيات": "🔌",
        }
        emoji = icons.get(category, "📦")
        font = painter.font()
        font.setPointSize(28)
        painter.setFont(font)
        painter.setPen(QColor("#334155"))
        painter.drawText(pm.rect(), Qt.AlignCenter, emoji)
        painter.end()
        return pm


class MainWindow(QMainWindow):
    def __init__(
        self,
        db,
        current_user,
        login_history_id=None,
        license_manager=None,
        store_name="سوبرماركت الخير",
    ):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self.login_history_id = login_history_id
        self.license_manager = license_manager or LicenseManager()
        self.store_name = store_name.strip() or "سوبرماركت الخير"
        self.license_worker = None
        self.license_overlay = None
        self.sync_worker = None
        self.current_product = None
        self.cart = []

        raw_role = (self.current_user.get("role") or "").strip().lower()
        role_map = {
            "owner": "owner",
            "مالك": "owner",
            "admin": "admin",
            "مدير": "admin",
            "saler": "saler",
            "seller": "saler",
            "بائع": "saler",
        }
        self.user_role = role_map.get(raw_role, raw_role)
        self.nav_buttons = {}
        self.sidebar_collapsed = False

        role_display_map = {
            "owner": "المالك",
            "admin": "المدير",
            "saler": "البائع",
        }
        role_display = role_display_map.get(self.user_role, current_user.get("role", "-"))

        self.setWindowTitle(
            f"نظام إدارة السوبرماركت — {self.store_name} - "
            f"{current_user['username']} ({role_display})"
        )
        self.setMinimumSize(1024, 680)

        # Keyboard shortcuts for Full Screen (F11) and Escape
        self.f11_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.f11_shortcut.activated.connect(self.toggle_full_screen)
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.esc_shortcut.activated.connect(self._exit_fullscreen_on_esc)

        self._build_shell()
        self._build_pages()
        self._apply_role_permissions()
        self._start_license_heartbeat()
        self._start_data_sync()

        # Launch window maximized by default for responsive screen support
        self.showMaximized()

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

    def _start_license_heartbeat(self):
        credentials = self.license_manager.stored_credentials()
        if not credentials:
            self._set_license_locked(True)
            return
        self.license_worker = LicenseCheckWorker(
            self.license_manager,
            credentials[0],
            credentials[1],
        )
        self.license_worker.checked.connect(
            lambda state: self._set_license_locked(state.status in {"expired", "blocked", "offline_expired"})
        )
        self.license_worker.start()

    def _start_data_sync(self):
        credentials = self.license_manager.stored_credentials()
        if not credentials:
            return
        self.sync_worker = SyncWorker(
            self.db,
            store_id=credentials[0],
            token=self.license_manager.stored_token(),
        )
        self.sync_worker.start()

    def _set_license_locked(self, locked):
        if locked:
            if self.license_overlay is None:
                self.license_overlay = LicenseLockOverlay(self)
            self.license_overlay.setGeometry(self.rect())
            self.license_overlay.show()
            self.license_overlay.raise_()
        elif self.license_overlay is not None:
            self.license_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.license_overlay is not None:
            self.license_overlay.setGeometry(self.rect())

    # ------------------------------------------------------------------
    # Full Screen Toggle Handler (F11 / Button)
    # ------------------------------------------------------------------
    def toggle_full_screen(self):
        """Toggle between maximized window mode and true full-screen mode (F11)."""
        if self.isFullScreen():
            self.showMaximized()
            if hasattr(self, 'fullscreen_btn'):
                self.fullscreen_btn.setText("⛶ ملء الشاشة (F11)")
                self.fullscreen_btn.setToolTip("تفعيل وضع ملء الشاشة (F11)")
        else:
            self.showFullScreen()
            if hasattr(self, 'fullscreen_btn'):
                self.fullscreen_btn.setText("🗗 نافذة عادية (F11)")
                self.fullscreen_btn.setToolTip("الخروج من ملء الشاشة (F11 أو Esc)")

    def _exit_fullscreen_on_esc(self):
        """Exit full-screen mode when Escape is pressed."""
        if self.isFullScreen():
            self.showMaximized()
            if hasattr(self, 'fullscreen_btn'):
                self.fullscreen_btn.setText("⛶ ملء الشاشة (F11)")
                self.fullscreen_btn.setToolTip("تفعيل وضع ملء الشاشة (F11)")

    def _on_categories_data_changed(self):
        """Triggered when categories are added, modified, or deleted in CategoriesTab."""
        try:
            if hasattr(self, 'stock_tab'):
                if hasattr(self.stock_tab, 'populate_category_dropdown'):
                    self.stock_tab.populate_category_dropdown()
                elif hasattr(self.stock_tab, '_refresh_categories_combo'):
                    self.stock_tab._refresh_categories_combo()
            self.load_products_side_panel()
            if hasattr(self, 'dashboard_tab'):
                self.dashboard_tab.refresh()
        except Exception:
            pass

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

        # Full-screen toggle button
        self.fullscreen_btn = QPushButton("⛶ ملء الشاشة (F11)")
        self.fullscreen_btn.setObjectName("fullscreenToggleBtn")
        self.fullscreen_btn.setProperty("variant", "outline")
        self.fullscreen_btn.setToolTip("تبديل وضع ملء الشاشة (F11)")
        self.fullscreen_btn.clicked.connect(self.toggle_full_screen)
        sidebar_layout.addWidget(self.fullscreen_btn)

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
        # RBAC Check: User Management is reserved exclusively for System Owner
        if key == "users" and self.user_role != "owner":
            QMessageBox.warning(
                self,
                "صلاحية غير كافية",
                "عذراً، هذه الصفحة مخصصة لمالك النظام فقط."
            )
            return

        if key not in self.nav_buttons:
            return

        for k, meta in self.nav_buttons.items():
            meta["button"].setChecked(k == key)

        self.pages.setCurrentIndex(self.nav_buttons[key]["index"])
        # when showing POS, reload product side-panel to reflect live inventory changes
        try:
            if key == 'pos':
                self.load_products_side_panel()
            elif key == 'categories' and hasattr(self, 'categories_tab'):
                self.categories_tab.refresh_categories()
            elif key == 'dashboard' and hasattr(self, 'dashboard_tab'):
                self.dashboard_tab.refresh()
            elif key == 'stock' and hasattr(self, 'stock_tab'):
                self.stock_tab.refresh_table()
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
        self.dashboard_tab = DashboardTab(self.db, self.store_name)
        self.customer_tab = self._build_customer_tab()
        self.stock_tab = StockWindow(self.db, current_user_role=self.user_role)
        self.categories_tab = CategoriesTab(self.db, current_user_role=self.user_role, on_categories_changed=self._on_categories_data_changed)
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
        self._add_nav_item("categories", "🏷️ الأقسام والفئات", self.categories_tab)
        self._add_nav_item("reports", "📈 التقارير", self.reports_tab)

        self.invoices_admin_tab = None
        self.user_admin_tab = None

        if self.user_role in {"admin", "owner"}:
            self.invoices_admin_tab = InvoicesAdminTab(self.db)
            self._add_nav_item("invoices", "👁️ الفواتير وسجل المبيعات", self.invoices_admin_tab)

        # Restrict User Management exclusively to Owner
        if self.user_role == "owner":
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
            # Total Products stat card -> Stock page navigation
            if hasattr(self.dashboard_tab, "card_total_products"):
                self.dashboard_tab.card_total_products.setCursor(Qt.PointingHandCursor)
                self.dashboard_tab.card_total_products.mousePressEvent = lambda event: self.switch_page("stock")

            # connect shortcut cards
            if hasattr(self.dashboard_tab, 'shortcut_cards'):
                for lbl, btn in self.dashboard_tab.shortcut_cards.items():
                    # Suppliers -> go to Customers page and select Suppliers tab
                    if lbl == 'Suppliers':
                        btn.clicked.connect(lambda _, mw=self: (mw.switch_page('customers'), mw.customer_tabs.setCurrentIndex(1) if hasattr(mw, 'customer_tabs') else None))
                    # Customers -> go to Customers page and select Customers tab
                    elif lbl == 'Customers':
                        btn.clicked.connect(lambda _, mw=self: (mw.switch_page('customers'), mw.customer_tabs.setCurrentIndex(0) if hasattr(mw, 'customer_tabs') else None))
                    # Categories shortcut -> navigate directly to Categories Management page
                    elif lbl == 'Categories':
                        btn.clicked.connect(lambda _, mw=self: mw.switch_page('categories'))
                    # Stock IN Today -> stock page
                    elif lbl == 'Stock IN Today':
                        btn.clicked.connect(lambda _, mw=self: mw.switch_page('stock'))
                    else:
                        # fallback
                        btn.clicked.connect(lambda _, mw=self: mw.switch_page('stock'))
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
        """Configure sidebar navigation and access permissions based on role."""
        if self.user_role in {"saler", "seller", "بائع"}:
            # Saler role: Read-only access to Stock, full access to POS and Customers
            if "stock" in self.nav_buttons:
                self.nav_buttons["stock"]["button"].setEnabled(True)
                self.nav_buttons["stock"]["button"].setVisible(True)
            if "reports" in self.nav_buttons:
                self.nav_buttons["reports"]["button"].setEnabled(False)
                self.nav_buttons["reports"]["button"].setVisible(False)
            if "dashboard" in self.nav_buttons:
                self.nav_buttons["dashboard"]["button"].setVisible(False)
            if "invoices" in self.nav_buttons:
                self.nav_buttons["invoices"]["button"].setVisible(False)
            if "users" in self.nav_buttons:
                self.nav_buttons["users"]["button"].setVisible(False)
                self.nav_buttons["users"]["button"].setEnabled(False)
            # Default landing page for Saler is POS
            try:
                self.switch_page("pos")
            except Exception:
                pass

        elif self.user_role in {"admin", "مدير"}:
            # Admin role: Full access except User Management
            if "users" in self.nav_buttons:
                self.nav_buttons["users"]["button"].setVisible(False)
                self.nav_buttons["users"]["button"].setEnabled(False)

        elif self.user_role in {"owner", "مالك"}:
            # Owner role: Full unrestricted access
            if "users" in self.nav_buttons:
                self.nav_buttons["users"]["button"].setVisible(True)
                self.nav_buttons["users"]["button"].setEnabled(True)

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
                mw = MainWindow(
                    self.db,
                    new_user,
                    new_login_history_id,
                    self.license_manager,
                    self.store_name,
                )
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
        root.setLayoutDirection(Qt.RightToLeft)
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
        self.product_label.setStyleSheet("color: #334155; font-weight: 600;")

        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("الكمية")
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("السعر اليدوي")

        # Step progression on Enter key:
        self.qty_input.returnPressed.connect(lambda: self.price_input.setFocus())
        self.price_input.returnPressed.connect(self.add_item_to_cart)

        self.add_btn = QPushButton("إضافة للسلة")
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(self.add_item_to_cart)

        scan_layout.addWidget(QLabel("QR / باركود (الخطوة 1):"), 0, 0)
        scan_layout.addWidget(self.barcode_input, 0, 1, 1, 3)
        scan_layout.addWidget(self.product_label, 1, 0, 1, 4)
        scan_layout.addWidget(QLabel("الكمية (الخطوة 2):"), 2, 0)
        scan_layout.addWidget(self.qty_input, 2, 1)
        scan_layout.addWidget(QLabel("السعر (الخطوة 3):"), 2, 2)
        scan_layout.addWidget(self.price_input, 2, 3)
        scan_layout.addWidget(self.add_btn, 3, 0, 1, 4)

        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels([
            "معرف المنتج",
            "الباركود",
            "اسم المنتج",
            "الكمية",
            "سعر الوحدة",
            "الإجمالي الفرعي",
        ])
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.itemChanged.connect(self._on_cart_item_changed)

        # Payment Section with separate Subtotal, Discount/Adjustment, and Final Total
        payment_box = QGroupBox("الدفع والفوترة")
        payment_layout = QFormLayout(payment_box)

        self.customer_combo = QComboBox()
        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet("font-weight: 700; color: #1e293b;")
        self.total_label = self.subtotal_label  # alias for backward compatibility

        self.discount_label = QLabel("0.00")
        self.discount_label.setStyleSheet("font-weight: 700; color: #dc2626;")

        # Editable final total (override / manual adjustment). Use QDoubleSpinBox for numeric entry.
        self.final_total_spin = QDoubleSpinBox()
        self.final_price_input = self.final_total_spin  # alias
        self.final_total_spin.setPrefix("")
        self.final_total_spin.setSuffix(" ج.م")
        self.final_total_spin.setDecimals(2)
        self.final_total_spin.setMaximum(9999999.99)
        self.final_total_spin.setValue(0.00)
        self.final_total_spin.setSingleStep(1.0)
        self.final_total_spin.setEnabled(False)  # Lock until cart has items
        self.final_total_spin.valueChanged.connect(self._on_final_total_changed)
        self._final_total_overridden = False

        # Receipt Mode Toggle Switch ("وضع الفاتورة / بدون فاتورة")
        self.receipt_toggle = QCheckBox("🖨️ وضع الفاتورة (طباعة تلقائية)")
        self.receipt_toggle.setChecked(True)
        self.receipt_toggle.setObjectName("receiptModeToggle")
        self.receipt_toggle.setCursor(Qt.PointingHandCursor)
        self.receipt_toggle.toggled.connect(self._on_receipt_toggle_changed)

        self.checkout_btn = QPushButton("إتمام البيع + طباعة الإيصال 🖨️")
        self.checkout_btn.setProperty("variant", "success")
        self.checkout_btn.clicked.connect(self.checkout)

        self.clear_btn = QPushButton("تفريغ السلة")
        self.clear_btn.setProperty("variant", "danger")
        self.clear_btn.clicked.connect(self.clear_cart)

        payment_layout.addRow("العميل:", self.customer_combo)
        payment_layout.addRow("المجموع الفرعي:", self.subtotal_label)
        payment_layout.addRow("الخصم / التسوية:", self.discount_label)
        payment_layout.addRow("الصافي النهائي:", self.final_total_spin)
        payment_layout.addRow("خيارات الطباعة:", self.receipt_toggle)

        payment_actions = QHBoxLayout()
        payment_actions.addWidget(self.checkout_btn)
        payment_actions.addWidget(self.clear_btn)
        payment_layout.addRow(payment_actions)

        layout.addWidget(scan_box)
        layout.addWidget(self.cart_table)
        layout.addWidget(payment_box)

        # Product side panel (right) with Full Arabic Localization (RTL)
        panel = QGroupBox("قائمة المنتجات السريعة")
        panel.setLayoutDirection(Qt.RightToLeft)
        panel.setMinimumWidth(380)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(10)

        self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText("بحث عن منتج (بالاسم أو الباركود)...")
        self.product_search_input.textChanged.connect(lambda txt: self._filter_products_side(txt))
        panel_layout.addWidget(self.product_search_input)

        # Dynamic Category Filter Tabs / Pills in a scrollable horizontal container
        self.category_scroll = QScrollArea()
        self.category_scroll.setFixedHeight(46)
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.category_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.category_scroll.setFrameShape(QFrame.NoFrame)
        self.category_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.category_pills_container = QWidget()
        self.category_pills_container.setStyleSheet("background: transparent;")
        self.category_pills_layout = QHBoxLayout(self.category_pills_container)
        self.category_pills_layout.setContentsMargins(0, 0, 0, 0)
        self.category_pills_layout.setSpacing(6)
        self.category_pills_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.category_scroll.setWidget(self.category_pills_container)

        panel_layout.addWidget(self.category_scroll)

        self.category_buttons = {}
        self.active_category = "الكل"

        # Multi-column Clean Grid Area for Products
        self.products_scroll = QScrollArea()
        self.products_scroll.setWidgetResizable(True)
        self.products_scroll.setFrameShape(QFrame.NoFrame)
        self.products_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.products_container = QWidget()
        self.products_container.setStyleSheet("background: transparent;")
        self.products_layout = QGridLayout(self.products_container)
        self.products_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.products_layout.setSpacing(12)
        self.products_layout.setContentsMargins(4, 4, 4, 4)
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

    def _refresh_pos_category_pills(self):
        """Dynamically generate category filter tabs/buttons based on categories present in the database."""
        try:
            db_cats = self.db.get_distinct_categories()
        except Exception:
            db_cats = ["مشروبات", "أطعمة", "مخبوزات", "منظفات", "أخرى"]

        # Ensure 'الكل' is always the first tab
        all_cats = ["الكل"] + [c for c in db_cats if c != "الكل"]

        # Clear existing buttons
        while self.category_pills_layout.count():
            item = self.category_pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self.category_buttons = {}
        if self.active_category not in all_cats:
            self.active_category = "الكل"

        for cat in all_cats:
            btn = QPushButton(cat)
            btn.setObjectName("categoryTabBtn")
            btn.setCheckable(True)
            btn.setChecked(cat == self.active_category)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat: self._on_category_pill_clicked(c))
            self.category_pills_layout.addWidget(btn)
            self.category_buttons[cat] = btn

        self.category_pills_layout.addStretch()

    def _on_category_pill_clicked(self, category: str):
        """Handle category tab click: update active state and filter products grid."""
        self.active_category = category
        for c, btn in self.category_buttons.items():
            btn.setChecked(c == category)
        search_txt = self.product_search_input.text() if hasattr(self, "product_search_input") else ""
        self._filter_products_side(search_txt, category)

    def load_products_side_panel(self):
        """Reload products from database and refresh dynamic category tabs and square cards grid."""
        try:
            products = self.db.list_products()
        except Exception:
            products = []

        self._all_products = products
        self._refresh_pos_category_pills()
        search_txt = self.product_search_input.text() if hasattr(self, "product_search_input") else ""
        self._filter_products_side(search_txt, getattr(self, "active_category", "الكل"))

    def _product_category(self, product: dict) -> str:
        """Extract product category string with fallback heuristics."""
        cat = (product.get("category") or "").strip()
        if cat:
            return cat

        name = (product.get("name") or "").lower()
        if any(k in name for k in ("عصير", "ماء", "مشروب", "كولا", "بيبسي", "حليب", "مياه", "شاي", "قهوة", "cola", "pepsi", "juice", "drink", "water", "milk", "tea", "coffee")):
            return "مشروبات"
        if any(k in name for k in ("خبز", "كيك", "فطائر", "معجنات", "توست", "كرواسون", "bread", "bakery", "bun", "cake", "toast")):
            return "مخبوزات"
        if any(k in name for k in ("شيبس", "بسكويت", "شوكولاتة", "سناك", "طعام", "أرز", "سكر", "زيت", "chips", "snack", "crisps", "cookie", "biscuit", "chocolate", "food", "rice", "oil")):
            return "أطعمة"
        if any(k in name for k in ("صابون", "مسحوق", "كلور", "منظف", "شامبو", "soap", "cleaner", "detergent", "shampoo")):
            return "منظفات"
        return "أخرى"

    def _get_product_pixmap(self, image_path: Optional[str] = None, category: str = "أخرى", size: int = 56) -> QPixmap:
        """Return product image pixmap or modern category fallback placeholder icon."""
        if image_path and os.path.isfile(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Fallback placeholder pixmap with category icon
        pm = QPixmap(size, size)
        pm.fill(QColor("#f8fafc"))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)

        # Card border
        painter.setPen(QColor("#e2e8f0"))
        painter.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)

        icons = {
            "مشروبات": "🥤",
            "Drinks": "🥤",
            "مخبوزات": "🥐",
            "Bakery": "🥐",
            "أطعمة": "🍟",
            "Food": "🍟",
            "Snacks": "🍟",
            "منظفات": "🧼",
            "Cleaning": "🧼",
            "ألبان": "🥛",
            "حلويات": "🍫",
        }
        emoji = icons.get(category, "📦")
        font = painter.font()
        font.setPointSize(int(size * 0.42))
        painter.setFont(font)
        painter.setPen(QColor("#475569"))
        painter.drawText(pm.rect(), Qt.AlignCenter, emoji)
        painter.end()
        return pm

    def _render_products(self, products: list):
        """Render product cards in a clean responsive grid layout with explicit 12px spacing."""
        while self._products_layout.count():
            it = self._products_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not products:
            empty_box = QFrame()
            empty_box.setStyleSheet("background: #f8fafc; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 24px;")
            el = QVBoxLayout(empty_box)
            empty_lbl = QLabel("لا توجد منتجات مطابقة لهذا التصنيف أو البحث 🔍")
            empty_lbl.setStyleSheet("color: #64748b; font-size: 14px; font-weight: 700;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            el.addWidget(empty_lbl)
            self._products_layout.addWidget(empty_box, 0, 0, 1, 2)
            return

        viewport_w = self.products_scroll.viewport().width() if hasattr(self, "products_scroll") else 380
        # Calculate columns adaptively: Card min-width ~155px + 12px spacing
        cols = max(2, min(4, int((viewport_w - 8) / 175))) if viewport_w > 200 else 2

        for idx, p in enumerate(products):
            row = idx // cols
            col = idx % cols
            card = SquareProductCard(p, on_click_callback=self._select_product)
            self._products_layout.addWidget(card, row, col)

    def _filter_products_side(self, text: str = "", category: Optional[str] = None):
        """Filter product side panel items by active category tab and search query."""
        if category is not None:
            self.active_category = category
        cat_filter = getattr(self, "active_category", "الكل")

        txt = (text or "").strip().lower()
        filtered = []
        for p in getattr(self, "_all_products", []):
            name = (p.get("name") or "").lower()
            barcode = (p.get("barcode") or "").lower()
            cat = self._product_category(p)
            if cat_filter != "الكل" and cat != cat_filter:
                continue
            if txt and txt not in name and txt not in barcode and txt not in cat.lower():
                continue
            filtered.append(p)

        # update category button check states
        for c, btn in getattr(self, "category_buttons", {}).items():
            btn.setChecked(c == cat_filter)

        self._render_products(filtered)

    def _add_product_to_cart(self, product: dict):
        """Legacy helper preserved for compatibility. Prefer using _select_product which enforces the 3-step workflow."""
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
        """Open a standardized 3-step selection dialog:
        1. Step 1 (QR/Barcode): Product & Barcode details + Image preview (Read-only)
        2. Step 2 (Quantity): Initial focus with quick +/- controls
        3. Step 3 (Unit Price): Price confirmation before adding to cart
        """
        dlg = QDialog(self)
        dlg.setWindowTitle(f"إضافة منتج للسلة - {product.get('name', '')}")
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.setModal(True)
        dlg.setMinimumWidth(460)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # --- STEP 1: Product info, Barcode/QR, and Image Preview (Read-only) ---
        step1_box = QGroupBox("🏷️ الخطوة 1: بيانات المنتج والباركود (QR / Barcode)")
        step1_inner = QHBoxLayout(step1_box)
        step1_inner.setSpacing(12)

        # Image thumbnail preview in Step 1
        cat = self._product_category(product)
        img_path = product.get("image_path")
        pixmap = self._get_product_pixmap(img_path, category=cat, size=68)
        img_lbl = QLabel()
        img_lbl.setPixmap(pixmap)
        img_lbl.setFixedSize(70, 70)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc;")
        step1_inner.addWidget(img_lbl)

        step1_layout = QFormLayout()
        step1_layout.setHorizontalSpacing(12)
        step1_layout.setVerticalSpacing(6)

        prod_name_lbl = QLabel(product.get("name") or "-")
        prod_name_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #0f172a;")

        barcode_lbl = QLabel(product.get("barcode") or "-")
        barcode_lbl.setStyleSheet("font-family: monospace; font-size: 13px; color: #475569; background: #f1f5f9; padding: 3px 8px; border-radius: 4px;")

        stock_avail = float(product.get("stock_qty") or 0)
        stock_lbl = QLabel(f"{int(stock_avail)} وحدة متاحة")
        stock_lbl.setStyleSheet("color: #059669; font-weight: 700;")

        step1_layout.addRow("المنتج:", prod_name_lbl)
        step1_layout.addRow("الباركود / QR:", barcode_lbl)
        step1_layout.addRow("المخزون المتاح:", stock_lbl)

        step1_inner.addLayout(step1_layout, 1)
        layout.addWidget(step1_box)

        # --- STEP 2: Quantity with +/- Quick Adjustments ---
        step2_box = QGroupBox("🔢 الخطوة 2: تحديد الكمية (Quantity)")
        step2_layout = QVBoxLayout(step2_box)
        step2_layout.setSpacing(8)

        qty_control_layout = QHBoxLayout()
        minus_btn = QPushButton("➖")
        minus_btn.setFixedWidth(42)
        minus_btn.setProperty("variant", "outline")

        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(max(1, int(stock_avail)))
        qty_spin.setValue(1)
        qty_spin.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px;")

        plus_btn = QPushButton("➕")
        plus_btn.setFixedWidth(42)
        plus_btn.setProperty("variant", "outline")

        qty_control_layout.addWidget(minus_btn)
        qty_control_layout.addWidget(qty_spin, 1)
        qty_control_layout.addWidget(plus_btn)
        step2_layout.addLayout(qty_control_layout)
        layout.addWidget(step2_box)

        # --- STEP 3: Unit Price Modification & Confirmation ---
        step3_box = QGroupBox("💰 الخطوة 3: سعر الوحدة والتأكيد (Unit Price)")
        step3_layout = QFormLayout(step3_box)
        step3_layout.setHorizontalSpacing(12)
        step3_layout.setVerticalSpacing(8)

        default_price = float(product.get("default_price") or 0.0)
        price_spin = QDoubleSpinBox()
        price_spin.setDecimals(2)
        price_spin.setMaximum(9999999.99)
        price_spin.setValue(default_price)
        price_spin.setSuffix(" ج.م")
        price_spin.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px;")

        subtotal_lbl = QLabel(f"{default_price:.2f} ج.م")
        subtotal_lbl.setStyleSheet("font-size: 16px; font-weight: 900; color: #059669;")

        step3_layout.addRow("سعر الوحدة:", price_spin)
        step3_layout.addRow("الإجمالي الفرعي:", subtotal_lbl)
        layout.addWidget(step3_box)

        # Real-time subtotal calculation
        def _recalc():
            sub = price_spin.value() * qty_spin.value()
            subtotal_lbl.setText(f"{sub:.2f} ج.م")

        qty_spin.valueChanged.connect(lambda _: _recalc())
        price_spin.valueChanged.connect(lambda _: _recalc())

        minus_btn.clicked.connect(lambda: qty_spin.setValue(max(1, qty_spin.value() - 1)))
        plus_btn.clicked.connect(lambda: qty_spin.setValue(min(int(stock_avail), qty_spin.value() + 1)))

        # Sequential focus progression: Step 2 (Qty) -> Step 3 (Price) -> Add
        qty_spin.editingFinished.connect(lambda: price_spin.setFocus())

        # Action buttons
        actions = QHBoxLayout()
        add_btn = QPushButton("🛒 إضافة للسلة")
        add_btn.setProperty("variant", "success")
        add_btn.setDefault(True)
        add_btn.setStyleSheet("font-weight: 800; font-size: 14px; padding: 8px 16px;")

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setProperty("variant", "outline")

        actions.addStretch()
        actions.addWidget(add_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

        def _on_add():
            qty = int(qty_spin.value())
            price = float(price_spin.value())
            if qty <= 0:
                QMessageBox.warning(dlg, "خطأ", "الكمية يجب أن تكون أكبر من صفر")
                return
            if qty > stock_avail:
                QMessageBox.warning(dlg, "مخزون غير كافٍ", "الكمية المطلوبة أكبر من المتاح")
                return

            # merge with existing item if present or append new
            pid = product.get("id")
            for item in self.cart:
                if item.get("product_id") == pid:
                    item["manual_price"] = price
                    item["qty"] += qty
                    self.refresh_cart()
                    dlg.accept()
                    return

            self.cart.append({
                "product_id": pid,
                "barcode": product.get("barcode"),
                "name": product.get("name"),
                "qty": qty,
                "base_price": default_price,
                "manual_price": price,
            })
            self.refresh_cart()
            dlg.accept()

        add_btn.clicked.connect(_on_add)
        cancel_btn.clicked.connect(dlg.reject)

        # Set initial focus directly to Step 2 (Quantity) for rapid entry
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, lambda: (qty_spin.setFocus(), qty_spin.selectAll()))

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
        # expose tabs for external switching
        self.customer_tabs = tabs

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
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على المنتج بالباركود المدخل")
            self.barcode_input.selectAll()
            self.barcode_input.setFocus()
            return

        self.current_product = product
        self.product_label.setText(
            f"المنتج: {product['name']} | متاح: {product['stock_qty']} | السعر: {product['default_price']:.2f} ج.م"
        )
        self.price_input.setText(f"{float(product['default_price']):.2f}")
        self.qty_input.setText("1")
        # Step 2: focus on Quantity input directly
        self.qty_input.setFocus()
        self.qty_input.selectAll()

    def add_item_to_cart(self):
        if not self.current_product:
            QMessageBox.warning(self, "تنبيه", "يرجى مسح الباركود أو تحديد المنتج أولاً")
            return

        try:
            qty = float(self.qty_input.text().strip())
            price = float(self.price_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الكمية والسعر يجب أن يكونا رقمين صحيحين")
            return

        if qty <= 0 or price < 0:
            QMessageBox.warning(self, "خطأ", "الكمية يجب أن تكون أكبر من صفر")
            return

        already_in_cart = sum(
            item["qty"] for item in self.cart if item["product_id"] == self.current_product["id"]
        )
        if already_in_cart + qty > float(self.current_product["stock_qty"]):
            QMessageBox.warning(self, "مخزون غير كافٍ", "الكمية المطلوبة أكبر من المتاح في المخزن")
            return

        pid = self.current_product["id"]
        merged = False
        for item in self.cart:
            if item.get("product_id") == pid:
                item["qty"] += qty
                item["manual_price"] = price
                merged = True
                break

        if not merged:
            self.cart.append(
                {
                    "product_id": self.current_product["id"],
                    "barcode": self.current_product["barcode"],
                    "name": self.current_product["name"],
                    "qty": qty,
                    "base_price": float(self.current_product.get("default_price") or price),
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
        # Update cart table rows and totals without altering individual unit prices
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(self.cart))
        subtotal = 0.0

        for row, item in enumerate(self.cart):
            row_subtotal = item["qty"] * item["manual_price"]
            subtotal += row_subtotal

            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item["product_id"])))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item["barcode"]))
            self.cart_table.setItem(row, 2, QTableWidgetItem(item["name"]))

            qty_item = QTableWidgetItem(str(item["qty"]))
            qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 3, qty_item)

            price_item = QTableWidgetItem(f"{item['manual_price']:.2f}")
            price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)
            self.cart_table.setItem(row, 4, price_item)

            subtotal_item = QTableWidgetItem(f"{row_subtotal:.2f}")
            subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 5, subtotal_item)

        self.subtotal_label.setText(f"{subtotal:.2f}")

        # Dynamically enable/disable final total price input based on cart contents
        if hasattr(self, 'final_total_spin'):
            has_items = len(self.cart) > 0
            self.final_total_spin.setEnabled(has_items)
            if not has_items:
                self._final_total_overridden = False
                self.final_total_spin.blockSignals(True)
                self.final_total_spin.setValue(0.00)
                self.final_total_spin.blockSignals(False)
                if hasattr(self, 'discount_label'):
                    self.discount_label.setText("0.00")
            elif not getattr(self, '_final_total_overridden', False):
                self.final_total_spin.blockSignals(True)
                self.final_total_spin.setValue(subtotal)
                self.final_total_spin.blockSignals(False)
                if hasattr(self, 'discount_label'):
                    self.discount_label.setText("0.00")
            else:
                final_val = float(self.final_total_spin.value())
                adjustment = round(subtotal - final_val, 2)
                if hasattr(self, 'discount_label'):
                    self.discount_label.setText(f"{adjustment:.2f}")

        self.cart_table.resizeColumnsToContents()
        self.cart_table.blockSignals(False)

    def clear_cart(self):
        self.cart = []
        self._final_total_overridden = False
        self.refresh_cart()

    def _on_receipt_toggle_changed(self, checked: bool):
        """Handle receipt mode toggle switch: updates button label and tooltips."""
        if checked:
            self.receipt_toggle.setText("🖨️ وضع الفاتورة (طباعة تلقائية)")
            self.receipt_toggle.setToolTip("سيتم حفظ العملية وإرسال إيصال الفاتورة للطباعة فوراً")
            self.checkout_btn.setText("إتمام البيع + طباعة الإيصال 🖨️")
        else:
            self.receipt_toggle.setText("🚫 بدون فاتورة (حفظ فقط)")
            self.receipt_toggle.setToolTip("سيتم حفظ العملية في المخزون وقاعدة البيانات بدون طباعة إيصال")
            self.checkout_btn.setText("إتمام البيع (حفظ فقط) 💾")

    def _build_receipt_html(self, invoice: dict) -> str:
        """Generate full-width 80mm thermal receipt HTML template with edge-to-edge page scaling."""
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
        discount_val = float(invoice.get("discount", 0.0) or 0.0)
        total_val = float(invoice.get("total", 0.0) or 0.0)
        paid_val = float(invoice.get("paid", 0.0) or 0.0)
        change_val = float(invoice.get("change_amount", 0.0) or 0.0)
        cashier_name = invoice.get("username") or "-"
        customer_name = invoice.get("customer_name") or "عميل مباشر"
        inv_no = invoice.get("invoice_no", "-")
        created_at = invoice.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        html = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <style>
    @page {{
      margin: 0;
      size: auto;
    }}
    body {{
      width: 100%;
      margin: 0;
      padding: 4px;
      font-family: 'Segoe UI', Tahoma, 'Tajawal', Arial, sans-serif;
      font-size: 12px;
      color: #000000;
      line-height: 1.35;
      background: #ffffff;
    }}
    .receipt {{
      width: 100%;
      margin: 0;
      padding: 0;
      text-align: right;
      box-sizing: border-box;
    }}
    .header {{
      text-align: center;
      margin-bottom: 6px;
    }}
    .store-name {{
      font-size: 16px;
      font-weight: 900;
      margin: 0 0 2px 0;
    }}
    .store-sub {{
      font-size: 10px;
      color: #222;
      margin: 0 0 2px 0;
    }}
    .divider {{
      border-top: 1px dashed #000000;
      margin: 5px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .meta-table td {{
      font-size: 11px;
      padding: 1px 0;
    }}
    table.items-table {{
      width: 100%;
      margin: 4px 0;
    }}
    table.items-table th {{
      border-bottom: 1px solid #000000;
      border-top: 1px solid #000000;
      padding: 4px 2px;
      font-size: 11px;
      font-weight: bold;
    }}
    table.items-table td {{
      padding: 4px 2px;
      font-size: 11px;
    }}
    .total-box {{
      margin-top: 4px;
    }}
    .total-box td {{
      padding: 2px 0;
      font-size: 12px;
    }}
    .footer {{
      text-align: center;
      font-size: 10px;
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <div class="receipt">
    <div class="header">
      <div class="store-name">🛒 سوبرماركت الفتح</div>
      <div class="store-sub">سجل تجاري: 1029384756 | هاتف: 01012345678</div>
      <div class="store-sub">إيصال مبيعات إلكتروني معتمد</div>
    </div>

    <div class="divider"></div>

    <table class="meta-table">
      <tr>
        <td><strong>رقم الفاتورة:</strong> {inv_no}</td>
      </tr>
      <tr>
        <td><strong>التاريخ:</strong> {created_at}</td>
      </tr>
      <tr>
        <td><strong>الكاشير:</strong> {cashier_name} | <strong>العميل:</strong> {customer_name}</td>
      </tr>
    </table>

    <div class="divider"></div>

    <table class="items-table">
      <thead>
        <tr>
          <th style="text-align: right; width: 45%;">الصنف</th>
          <th style="text-align: center; width: 15%;">الكمية</th>
          <th style="text-align: center; width: 20%;">السعر</th>
          <th style="text-align: left; width: 20%;">الإجمالي</th>
        </tr>
      </thead>
      <tbody>
        {rows_str}
      </tbody>
    </table>

    <div class="divider"></div>

    <div class="total-box">
      <table>
        <tr>
          <td>المجموع الفرعي:</td>
          <td style="text-align: left;">{subtotal_val:.2f} ج.م</td>
        </tr>
        {f'<tr><td>الخصم / التسوية:</td><td style="text-align: left; color: red;">- {discount_val:.2f} ج.م</td></tr>' if discount_val > 0 else ''}
        <tr style="font-weight: 900; font-size: 13px;">
          <td style="border-top: 1px dashed #000000; padding-top: 3px;">الصافي الإجمالي:</td>
          <td style="border-top: 1px dashed #000000; text-align: left; padding-top: 3px;">{total_val:.2f} ج.م</td>
        </tr>
        <tr>
          <td>المدفوع:</td>
          <td style="text-align: left;">{paid_val:.2f} ج.م</td>
        </tr>
        <tr>
          <td>المتبقي:</td>
          <td style="text-align: left;">{change_val:.2f} ج.م</td>
        </tr>
      </table>
    </div>

    <div class="divider"></div>

    <div class="footer">
      <div style="font-weight: bold; margin-bottom: 2px;">شكراً لتسوقكم معنا! نتمنى لكم يوماً سعيداً</div>
      <div style="color: #444; font-size: 9px;">البضاعة المباعة ترد وتستبدل خلال 14 يوماً بموجب الفاتورة</div>
      <div style="color: #666; font-size: 8px; margin-top: 3px;">*** إيصال معتمد لنقاط البيع ***</div>
    </div>
  </div>
</body>
</html>
"""
        return html

    def print_receipt_directly(self, invoice_or_html, receipt_html: str = None):
        """Direct silent printing to default system printer without opening QPrintDialog.
        Bypasses system print dialog, sets zero page margins and 80mm thermal receipt size,
        and scales document text width edge-to-edge across thermal paper.
        """
        try:
            if isinstance(invoice_or_html, dict):
                invoice = invoice_or_html
                html_content = receipt_html if receipt_html is not None else self._build_receipt_html(invoice)
                doc_name = f"Receipt-{invoice.get('invoice_no', 'INV')}"
            else:
                html_content = str(invoice_or_html)
                doc_name = "Thermal-Receipt"

            default_printer_info = QPrinterInfo.defaultPrinter()
            if not default_printer_info.isNull():
                printer = QPrinter(default_printer_info, QPrinter.HighResolution)
            else:
                available = QPrinterInfo.availablePrinters()
                if available:
                    printer = QPrinter(available[0], QPrinter.HighResolution)
                else:
                    printer = QPrinter(QPrinter.HighResolution)

            printer.setDocName(doc_name)
            printer.setFullPage(True)
            # Set 80mm thermal receipt dimensions with zero margins
            printer.setPaperSize(QSizeF(80, 297), QPrinter.Millimeter)
            printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)

            doc = QTextDocument()
            # Scale document width to the printable page width
            page_width = printer.pageRect(QPrinter.Point).width()
            if page_width > 0:
                doc.setTextWidth(page_width)
            doc.setHtml(html_content)
            doc.print_(printer)
        except Exception as pe:
            print(f"Receipt printing notice: {pe}")

    def _print_receipt(self, invoice: dict, receipt_html: str = None):
        """Backward-compatible alias pointing to direct silent printing."""
        self.print_receipt_directly(invoice, receipt_html)

    def checkout(self):
        """Payment completion handler: saves invoice, triggers direct receipt printing, and resets session."""
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة، يرجى إضافة منتجات أولاً")
            return

        computed_subtotal = sum(item['qty'] * item['manual_price'] for item in self.cart)
        final_total = float(self.final_total_spin.value()) if hasattr(self, 'final_total_spin') else computed_subtotal
        
        # Calculate discount/adjustment while keeping individual unit prices intact
        if getattr(self, '_final_total_overridden', False):
            discount = round(computed_subtotal - final_total, 2)
            total = final_total
        else:
            discount = 0.0
            total = computed_subtotal

        paid = total
        customer_id = self.customer_combo.currentData()
        if customer_id == -1:
            customer_id = None

        try:
            # 1. Process transaction and save invoice to database
            invoice_id, invoice_no, final_amt, change_amount = self.db.create_invoice(
                items=self.cart,
                paid=paid,
                user_id=self.current_user["id"],
                customer_id=customer_id,
                discount=discount,
                total=total,
            )
            invoice = self.db.get_invoice_details(invoice_id)
            
            # 2. Generate backup PDF in reports directory
            pdf_path = generate_invoice_pdf(invoice)

            # 3. Check Receipt Mode Toggle
            is_print_enabled = self.receipt_toggle.isChecked() if hasattr(self, 'receipt_toggle') else True
            receipt_html = self._build_receipt_html(invoice)

            if is_print_enabled:
                # Direct silent printing without dialog
                self.print_receipt_directly(invoice, receipt_html)

                QMessageBox.information(
                    self,
                    "تمت العملية بنجاح",
                    f"✅ تم تأكيد البيع وإصدار الفاتورة رقم: {invoice_no}\n\n"
                    f"🖨️ تم إرسال الإيصال إلى الطابعة مباشرة.\n\n"
                    f"• الصافي: {final_amt:.2f} ج.م\n"
                    f"• المدفوع: {paid:.2f} ج.م\n"
                    f"• المتبقي: {change_amount:.2f} ج.م\n"
                    f"• نسخة PDF: {pdf_path}",
                )
            else:
                QMessageBox.information(
                    self,
                    "تم الحفظ بنجاح",
                    f"✅ تم حفظ العملية بدون طباعة\n\n"
                    f"• رقم الفاتورة: {invoice_no}\n"
                    f"• الصافي: {final_amt:.2f} ج.م\n"
                    f"• المدفوع: {paid:.2f} ج.م\n"
                    f"• نسخة PDF: {pdf_path}",
                )

            # 5. Reset/Refresh POS screen session for next customer
            self.reset_pos_session()

            # 6. Refresh remaining dashboard, reports, stock, and invoice admin tabs
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
            QMessageBox.critical(self, "خطأ أثناء إتمام الدفع", str(e))

    def _on_cart_item_changed(self, item):
        try:
            row = item.row()
            col = item.column()
            # col 4 is unit price
            if col == 4:
                text = item.text().strip().replace(',', '.')
                try:
                    val = float(text)
                except ValueError:
                    QMessageBox.warning(self, "خطأ", "السعر يجب أن يكون رقمًا")
                    self.refresh_cart()
                    return
                if 0 <= row < len(self.cart):
                    self.cart[row]['manual_price'] = val
                    self.refresh_cart()
        except Exception:
            pass

    def _on_final_total_changed(self, value: float):
        """Handler when cashier manually edits the final total amount.
        Keeps individual item prices strictly UNCHANGED and records difference as discount/adjustment."""
        try:
            computed_subtotal = sum(i['qty'] * i['manual_price'] for i in self.cart)
            final_total = float(value)
            if len(self.cart) == 0:
                return

            if abs(final_total - computed_subtotal) < 0.001:
                self._final_total_overridden = False
                if hasattr(self, 'discount_label'):
                    self.discount_label.setText("0.00")
            else:
                self._final_total_overridden = True
                adjustment = round(computed_subtotal - final_total, 2)
                if hasattr(self, 'discount_label'):
                    self.discount_label.setText(f"{adjustment:.2f}")
        except Exception:
            pass

    def reset_pos_session(self):
        """Clear cart, reset totals and final total override, reload products, and focus barcode input."""
        try:
            self.cart = []
            self._final_total_overridden = False
            self.refresh_cart()
        except Exception:
            pass

        try:
            if hasattr(self, 'final_total_spin'):
                self._final_total_overridden = False
                self.final_total_spin.blockSignals(True)
                self.final_total_spin.setValue(0.00)
                self.final_total_spin.setEnabled(False)
                self.final_total_spin.blockSignals(False)
            if hasattr(self, 'discount_label'):
                self.discount_label.setText("0.00")
        except Exception:
            pass

        try:
            self.load_products_side_panel()
        except Exception:
            pass

        try:
            self.barcode_input.setFocus()
            self.barcode_input.selectAll()
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
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait(2000)
        if self.license_worker and self.license_worker.isRunning():
            self.license_worker.stop()
            self.license_worker.wait(2000)
        if self.login_history_id:
            self.db.log_logout(self.login_history_id)
        super().closeEvent(event)
