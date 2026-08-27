from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QBoxLayout,
)


class DashboardTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Make the whole dashboard scrollable and RTL
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        body.setLayoutDirection(Qt.RightToLeft)  # enforce RTL flow
        root = QVBoxLayout(body)
        root.setContentsMargins(16, 16, 16, 16)
        # Increase spacing so bottom cards don't touch the window edge
        root.setSpacing(18)

        # Page header (Arabic)
        welcome_row = QHBoxLayout()
        welcome_lbl = QLabel("لوحة التحكم")
        welcome_lbl.setObjectName("pageTitleLabel")
        refresh_btn = QPushButton("تحديث")
        refresh_btn.setProperty("variant", "outline")
        refresh_btn.clicked.connect(self.refresh)
        welcome_row.addWidget(welcome_lbl)
        welcome_row.addStretch()
        welcome_row.addWidget(refresh_btn)
        root.addLayout(welcome_row)

        # ── Top stat cards ──────────────────────────────
        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(12)
        top_grid.setVerticalSpacing(0)

        c1, self.products_value = self._stat_card(
            "📦", "إجمالي المنتجات", "0", "عرض المخزون ←", "products"
        )
        c1.setCursor(Qt.PointingHandCursor)
        # expose total products stat card so MainWindow can wire navigation
        self.card_total_products = c1

        c2, self.sales_value = self._stat_card(
            "💵", "مبيعات اليوم", "0.00 $", "فاتورة", "sales"
        )
        c3, self.low_stock_value = self._stat_card(
            "⚠️", "تنبيه نقص المخزون", "0", "يحتاج إعادة طلب", "low_stock"
        )
        c4, self.invoices_value = self._stat_card(
            "🗑", "المنتجات المنتهية / النفاد", "0", "مطلوب إجراء", "out_of_stock"
        )

        # Improve contrast and readability for stat cards
        try:
            c1.setStyleSheet(
                'QFrame { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; } '
                'QFrame:hover { background: #f8fafc; border: 1.5px solid #3b82f6; } '
                'QLabel { color: #1e293b; } QLabel#statValueLabel { color: #1e293b; }'
            )
        except Exception:
            pass
        try:
            c2.setStyleSheet('QFrame { background: #ffffff; border-radius: 12px; } QLabel { color: #1e293b; } QLabel#statValueLabel { color: #1e293b; }')
        except Exception:
            pass
        try:
            c3.setStyleSheet('QFrame { background: #fffbeb; border-radius: 12px; } QLabel { color: #1e293b; } QLabel#statValueLabel { color: #1e293b; }')
        except Exception:
            pass
        try:
            c4.setStyleSheet('QFrame { background: #fef2f2; border-radius: 12px; } QLabel { color: #1e293b; } QLabel#statValueLabel { color: #1e293b; }')
        except Exception:
            pass

        top_grid.addWidget(c1, 0, 0)
        top_grid.addWidget(c2, 0, 1)
        top_grid.addWidget(c3, 0, 2)
        top_grid.addWidget(c4, 0, 3)
        for col in range(4):
            top_grid.setColumnStretch(col, 1)
        root.addLayout(top_grid)

        # ── Middle row: 3 columns ────────────────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        # Col 1: Recent Sales table
        sales_card = QFrame()
        sales_card.setObjectName("pageCard")
        sl = QVBoxLayout(sales_card)
        sl.setContentsMargins(14, 12, 14, 12)
        sl.setSpacing(8)

        sr_head = QHBoxLayout()
        sr_lbl = QLabel("أحدث المبيعات")
        sr_lbl.setObjectName("sectionTitleLabel")

        # View all sales button + new sale
        self.view_sales_btn = QPushButton("عرض الكل")
        self.view_sales_btn.setProperty("variant", "outline")
        self.new_sale_btn = QPushButton("+ عملية بيع جديدة")
        self.new_sale_btn.setProperty("variant", "primary")

        sr_head.addWidget(sr_lbl)
        sr_head.addStretch()
        sr_head.addWidget(self.view_sales_btn)
        sr_head.addWidget(self.new_sale_btn)

        self.recent_sales_table = QTableWidget(0, 3)
        self.recent_sales_table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "العميل", "الإجمالي"
        ])
        self.recent_sales_table.verticalHeader().setVisible(False)
        self.recent_sales_table.horizontalHeader().setStretchLastSection(True)
        try:
            self.recent_sales_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        except Exception:
            pass
        self.recent_sales_table.setShowGrid(False)
        self.recent_sales_table.setAlternatingRowColors(False)
        self.recent_sales_table.setMinimumHeight(200)
        # clearer row spacing for readability
        try:
            self.recent_sales_table.verticalHeader().setDefaultSectionSize(40)
        except Exception:
            pass

        sl.addLayout(sr_head)
        sl.addWidget(self.recent_sales_table)

        # Col 2: Inventory summary
        inv_card = QFrame()
        inv_card.setObjectName("pageCard")
        il = QVBoxLayout(inv_card)
        il.setContentsMargins(14, 12, 14, 12)
        il.setSpacing(8)

        inv_title = QLabel("توزيع المخزون")
        inv_title.setObjectName("sectionTitleLabel")

        self.inv_in_stock = QLabel("0")
        self.inv_low_stock = QLabel("0")
        self.inv_expired = QLabel("0")

        il.addWidget(inv_title)
        il.addSpacing(6)

        for label_txt, color, val_lbl, bg in [
            ("متوفر", "#10b981", self.inv_in_stock, "#d1fae5"),
            ("منخفض", "#f59e0b", self.inv_low_stock, "#fef3c7"),
            ("نفد", "#ef4444", self.inv_expired, "#fee2e2"),
        ]:
            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"QFrame {{ background: {bg}; border-radius: 8px; padding: 2px; }}"
            )
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(10, 8, 10, 8)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent; border-radius: 0;")
            lbl = QLabel(label_txt)
            lbl.setStyleSheet(f"color: {color}; font-weight: 700; background: transparent; border-radius: 0;")
            val_lbl.setStyleSheet(
                f"color: {color}; font-weight: 800; font-size: 16px; background: transparent; border-radius: 0;")
            rl.addWidget(dot)
            rl.addWidget(lbl)
            rl.addStretch()
            rl.addWidget(val_lbl)
            il.addWidget(row_frame)

        il.addStretch()

        # Col 3: Recent Activity feed
        act_card = QFrame()
        act_card.setObjectName("pageCard")
        al = QVBoxLayout(act_card)
        al.setContentsMargins(14, 12, 14, 12)
        al.setSpacing(8)

        ah = QHBoxLayout()
        act_title = QLabel("سجل النشاط الأخير")
        act_title.setObjectName("sectionTitleLabel")
        view_all = QPushButton("عرض الكل")
        view_all.setProperty("variant", "outline")
        self.view_all_btn = view_all
        ah.addWidget(act_title)
        ah.addStretch()
        ah.addWidget(view_all)

        self.activity_list_layout = QVBoxLayout()
        self.activity_list_layout.setSpacing(6)

        al.addLayout(ah)
        al.addLayout(self.activity_list_layout)
        al.addStretch()

        mid_row.addWidget(sales_card, 5)
        mid_row.addWidget(inv_card, 3)
        mid_row.addWidget(act_card, 4)
        root.addLayout(mid_row)

        # ── Bottom shortcut cards ────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Keep internal keys in English for MainWindow wiring; display labels in Arabic
        AR = {
            'Suppliers': 'الموردون',
            'Customers': 'العملاء',
            'Categories': 'الفئات / الأقسام',
            'Stock IN Today': 'الوارد اليوم',
        }

        shortcut_data = [
            ("🚚", 'Suppliers', "4", "#f0f9ff", "#0369a1"),
            ("👥", 'Customers', "0", "#f0fdf4", "#166534"),
            ("🏷️", 'Categories', "0", "#fffbeb", "#92400e"),
            ("📥", 'Stock IN Today', "0", "#fdf4ff", "#6b21a8"),
        ]
        self.shortcut_labels = {}
        self.shortcut_cards = {}
        for icon, key, val, bg, color in shortcut_data:
            # display label is Arabic translation
            display = AR.get(key, key)
            card, val_lbl = self._shortcut_card(icon, display, val, bg, color)
            self.shortcut_labels[key] = val_lbl
            self.shortcut_cards[key] = card
            bottom_row.addWidget(card, 1)

        # ensure bottom row has min height so cards are not cut off
        bottom_wrapper = QFrame()
        br_l = QVBoxLayout(bottom_wrapper)
        br_l.setContentsMargins(0, 4, 0, 4)
        br_l.addLayout(bottom_row)
        bottom_wrapper.setMinimumHeight(110)

        root.addWidget(bottom_wrapper)
        root.addStretch()

        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Stat card builder
    # ------------------------------------------------------------------
    def _stat_card(self, icon, title, value, sub, variant):
        card = QFrame()
        card.setProperty("card", "stat")
        card.setProperty("cardVariant", variant)

        ly = QVBoxLayout(card)
        ly.setContentsMargins(16, 14, 16, 14)
        ly.setSpacing(4)

        top_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("statTitleLabel")
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("statIconLabel")
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        top_row.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValueLabel")

        sub_lbl = QLabel(sub)
        sub_lbl.setObjectName("statSubLabel")

        ly.addLayout(top_row)
        ly.addWidget(val_lbl)
        ly.addWidget(sub_lbl)

        return card, val_lbl

    # ------------------------------------------------------------------
    # Shortcut card builder
    # ------------------------------------------------------------------
    def _shortcut_card(self, icon, label_txt, value, bg, color):
        # Use a QPushButton so it can be clicked and connected from parent
        card_btn = QPushButton()
        card_btn.setObjectName("shortcutCard")
        card_btn.setStyleSheet(f"QPushButton#shortcutCard {{ background: #ffffff; border: 1px solid #e8edf5; border-radius: 10px; padding: 12px; text-align: right; }}")
        card_btn.setFlat(True)

        ly = QHBoxLayout(card_btn)
        ly.setContentsMargins(14, 12, 14, 12)
        ly.setSpacing(12)

        icon_box = QLabel(icon)
        # slightly larger icon container for visual balance
        icon_box.setFixedSize(56, 56)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(
            f"QLabel {{ background: {bg}; border-radius: 12px; "
            f"font-size: 22px; border: none; }}"
        )

        txt_col = QVBoxLayout()
        txt_col.setSpacing(4)
        lbl = QLabel(label_txt)
        lbl.setStyleSheet("color: #475569; font-size: 13px; font-weight: 700; background: transparent; border-radius: 0;")
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 800; background: transparent; border-radius: 0;")
        txt_col.addWidget(lbl)
        txt_col.addWidget(val_lbl)

        ly.addWidget(icon_box)
        ly.addLayout(txt_col)
        ly.addStretch()

        # enforce consistent action card height to avoid clipping
        try:
            card_btn.setMinimumHeight(85)
            card_btn.setMaximumHeight(100)
        except Exception:
            pass

        return card_btn, val_lbl

    # ------------------------------------------------------------------
    # Activity item builder
    # ------------------------------------------------------------------
    def _build_activity_item(self, icon, text, time_txt):
        frame = QFrame()
        frame.setObjectName("activityItem")
        ly = QHBoxLayout(frame)
        ly.setContentsMargins(8, 6, 8, 6)
        ly.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(24)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 14px; background: transparent; border-radius: 0;")

        col = QVBoxLayout()
        col.setSpacing(2)
        txt_lbl = QLabel(text)
        txt_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; background: transparent; border-radius: 0;")
        time_lbl = QLabel(time_txt)
        time_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border-radius: 0;")
        col.addWidget(txt_lbl)
        col.addWidget(time_lbl)

        ly.addWidget(icon_lbl)
        ly.addLayout(col)
        return frame

    # ------------------------------------------------------------------
    # Refresh / data
    # ------------------------------------------------------------------
    def refresh(self):
        summary = self.db.get_dashboard_summary()
        self.products_value.setText(str(summary["products_count"]))
        self.sales_value.setText(f"{summary['sales_today']:.2f} $")
        self.invoices_value.setText(str(summary.get("invoices_today", 0)))

        expiry_rows = self.db.get_expiry_report(days=60)
        expired_count = sum(1 for r in expiry_rows if r.get("expiry_status") == "EXPIRED")
        near_count = sum(1 for r in expiry_rows if r.get("expiry_status") == "NEAR_EXPIRY")
        all_products = self.db.list_products()
        # Count unique available products with stock_qty > 0 (excluding 0 stock)
        try:
            available_items_count = self.db.get_available_products_count()
        except Exception:
            available_items_count = sum(1 for p in all_products if float(p.get("stock_qty", 0) or 0) > 0)

        # count of products with low stock (<=5 and >0)
        low_stock_count = sum(1 for p in all_products if 0 < float(p.get("stock_qty", 0) or 0) <= 5)
        # count of out of stock products (stock_qty == 0)
        out_of_stock_count = sum(1 for p in all_products if float(p.get("stock_qty", 0) or 0) <= 0)

        self.low_stock_value.setText(str(near_count + expired_count))
        # show count of unique available items in stock (distinct active products where stock > 0)
        self.inv_in_stock.setText(str(available_items_count))
        # show number of low-stock product SKUs
        self.inv_low_stock.setText(str(low_stock_count))
        self.inv_expired.setText(str(expired_count if expired_count > 0 else out_of_stock_count))

        # update suppliers count on dashboard
        try:
            suppliers = self.db.list_suppliers()
            if "Suppliers" in self.shortcut_labels:
                self.shortcut_labels["Suppliers"].setText(str(len(suppliers)))
        except Exception:
            pass

        sales_rows = self.db.get_sales_report("2000-01-01", "2999-12-31")[:6]
        self.recent_sales_table.setRowCount(len(sales_rows))
        for i, row in enumerate(sales_rows):
            inv_item = QTableWidgetItem(row.get("invoice_no", "-"))
            inv_item.setForeground(QBrush(QColor("#1d4ed8")))
            self.recent_sales_table.setItem(i, 0, inv_item)
            self.recent_sales_table.setItem(i, 1, QTableWidgetItem("عميل مباشر"))
            total_item = QTableWidgetItem(f"{row.get('total', 0):.2f} $")
            total_item.setForeground(QBrush(QColor("#059669")))
            self.recent_sales_table.setItem(i, 2, total_item)
        self.recent_sales_table.resizeColumnsToContents()

        # Clear and rebuild activity feed
        while self.activity_list_layout.count():
            item = self.activity_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        logs = self.db.get_login_history(6)
        icons = {"SUCCESS": "🔓", "FAILED": "🔐"}
        for l in logs:
            action = "سجل الدخول" if l.get("status") == "SUCCESS" else "محاولة فاشلة"
            frame = self._build_activity_item(
                icons.get(l.get("status", ""), "🔔"),
                f"{l.get('username', '-')} — {action}",
                l.get("login_at", "-"),
            )
            self.activity_list_layout.addWidget(frame)

        # Shortcut card updates
        customers = self.db.list_customers()
        if "Customers" in self.shortcut_labels:
            self.shortcut_labels["Customers"].setText(str(len(customers)))
        if "Categories" in self.shortcut_labels:
            try:
                cats_count = summary.get("categories_count")
                if cats_count is None:
                    cats_count = len(self.db.list_categories())
            except Exception:
                cats_count = len(self.db.get_distinct_categories())
            self.shortcut_labels["Categories"].setText(str(cats_count))
        if "Stock IN Today" in self.shortcut_labels:
            self.shortcut_labels["Stock IN Today"].setText(str(summary["products_count"]))
