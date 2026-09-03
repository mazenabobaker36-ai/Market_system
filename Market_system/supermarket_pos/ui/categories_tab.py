from datetime import datetime
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class CategoriesTab(QWidget):
    """Dedicated Categories Management Page (إدارة الأقسام / الفئات)."""

    def __init__(self, db, current_user_role: str = "admin", on_categories_changed=None):
        super().__init__()
        self.db = db
        self.current_user_role = (current_user_role or "").strip().lower()
        self.on_categories_changed = on_categories_changed
        self.editing_category_id: Optional[int] = None
        self._all_categories = []

        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh_categories()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("🏷️ إدارة الأقسام والفئات (Categories Management)")
        title.setObjectName("pageTitleLabel")
        subtitle = QLabel("إضافة وتعديل وحذف أقسام وتصنيفات المنتجات وتنظيم المخزون ونقاط البيع")
        subtitle.setObjectName("pageSubtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_row.addLayout(title_box)
        header_row.addStretch()

        self.new_cat_btn = QPushButton("+ إضافة فئة جديدة")
        self.new_cat_btn.setProperty("variant", "primary")
        self.new_cat_btn.setToolTip("تفريغ النموذج لإضافة فئة جديدة")
        self.new_cat_btn.clicked.connect(self._clear_form)
        header_row.addWidget(self.new_cat_btn)

        root_layout.addLayout(header_row)

        # Search Bar Card
        search_card = QFrame()
        search_card.setObjectName("pageCard")
        sl = QHBoxLayout(search_card)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث في الأقسام والفئات بالاسم أو الوصف...")
        self.search_input.textChanged.connect(self._filter_categories)

        search_btn = QPushButton("بحث")
        search_btn.setProperty("variant", "primary")
        search_btn.clicked.connect(self._filter_categories)

        clear_search_btn = QPushButton("مسح")
        clear_search_btn.setProperty("variant", "outline")
        clear_search_btn.clicked.connect(lambda: (self.search_input.clear(), self._filter_categories()))

        sl.addWidget(self.search_input, 1)
        sl.addWidget(search_btn)
        sl.addWidget(clear_search_btn)
        root_layout.addWidget(search_card)

        # Add / Edit Category Form
        self.form_box = QGroupBox("إضافة / تعديل فئة أو قسم")
        form_layout = QGridLayout(self.form_box)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم القسم أو الفئة (مثال: مشروبات، أجهزة، خضروات...)")
        self.name_input.returnPressed.connect(self.save_category)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("وصف مختصر للقسم أو ملاحظات إضافية (اختياري)...")
        self.desc_input.returnPressed.connect(self.save_category)

        form_layout.addWidget(QLabel("اسم الفئة / القسم:"), 0, 0)
        form_layout.addWidget(self.name_input, 0, 1)
        form_layout.addWidget(QLabel("الوصف / الملاحظات:"), 0, 2)
        form_layout.addWidget(self.desc_input, 0, 3)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("حفظ الفئة")
        self.save_btn.setProperty("variant", "success")
        self.save_btn.clicked.connect(self.save_category)

        self.clear_btn = QPushButton("مسح الحقول")
        self.clear_btn.setProperty("variant", "outline")
        self.clear_btn.clicked.connect(self._clear_form)

        self.refresh_btn = QPushButton("تحديث الجدول 🔄")
        self.refresh_btn.setProperty("variant", "outline")
        self.refresh_btn.clicked.connect(self.refresh_categories)

        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.refresh_btn)

        form_layout.addLayout(btn_row, 1, 0, 1, 4)
        root_layout.addWidget(self.form_box)

        # Categories Table Card
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "المعرف (ID)",
            "اسم الفئة / القسم",
            "الوصف",
            "عدد المنتجات المرتبطة",
            "الإجراءات",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(1, 160)

        root_layout.addWidget(self.table, 1)

        self._apply_role_permissions()

    def _apply_role_permissions(self):
        """Apply RBAC permissions: Saler has read-only access."""
        is_saler = self.current_user_role in {"saler", "seller", "بائع"}
        self.form_box.setVisible(not is_saler)
        self.form_box.setEnabled(not is_saler)
        self.new_cat_btn.setVisible(not is_saler)

    def refresh_categories(self):
        """Reload all categories with product counts from database."""
        try:
            self._all_categories = self.db.list_categories()
        except Exception:
            self._all_categories = []
        self._filter_categories()

    def _filter_categories(self):
        """Filter category table rows based on search bar text."""
        query = (self.search_input.text() or "").strip().lower()
        filtered = [
            c for c in self._all_categories
            if not query
            or query in (c.get("name") or "").lower()
            or query in (c.get("description") or "").lower()
            or query in str(c.get("id", ""))
        ]
        self._render_table(filtered)

    def _render_table(self, categories_list):
        """Populate categories table with styled cells and action buttons."""
        self.table.setRowCount(len(categories_list))
        is_saler = self.current_user_role in {"saler", "seller", "بائع"}

        for row_idx, cat in enumerate(categories_list):
            cat_id = cat.get("id")
            name = cat.get("name") or "-"
            desc = cat.get("description") or "-"
            prod_count = int(cat.get("product_count", 0))

            # Column 0: ID
            id_item = QTableWidgetItem(str(cat_id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, id_item)

            # Column 1: Name (bold with distinct color)
            name_item = QTableWidgetItem(name)
            font = name_item.font()
            font.setBold(True)
            name_item.setFont(font)
            name_item.setForeground(QBrush(QColor("#0f172a")))
            self.table.setItem(row_idx, 1, name_item)

            # Column 2: Description
            desc_item = QTableWidgetItem(desc)
            desc_item.setForeground(QBrush(QColor("#475569")))
            self.table.setItem(row_idx, 2, desc_item)

            # Column 3: Product Count Badge
            badge_item = QTableWidgetItem(f"{prod_count} منتج")
            badge_item.setTextAlignment(Qt.AlignCenter)
            if prod_count > 0:
                badge_item.setForeground(QBrush(QColor("#059669")))
                font_b = badge_item.font()
                font_b.setBold(True)
                badge_item.setFont(font_b)
            else:
                badge_item.setForeground(QBrush(QColor("#94a3b8")))
            self.table.setItem(row_idx, 3, badge_item)

            # Column 4: Action Buttons (Edit / Delete)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignCenter)

            if not is_saler:
                edit_btn = QPushButton("تعديل")
                edit_btn.setObjectName("actionEditBtn")
                edit_btn.setProperty("variant", "primary")
                edit_btn.setToolTip("تعديل اسم ووصف الفئة")
                edit_btn.clicked.connect(lambda _, c=cat: self._populate_for_edit(c))
                action_layout.addWidget(edit_btn)

                del_btn = QPushButton("حذف")
                del_btn.setObjectName("actionDeleteBtn")
                del_btn.setProperty("variant", "danger")
                del_btn.setToolTip("حذف الفئة ونقل منتجاتها إلى قسم أخرى")
                del_btn.clicked.connect(lambda _, c=cat: self._delete_category(c))
                action_layout.addWidget(del_btn)
            else:
                ro_lbl = QLabel("عرض فقط")
                ro_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
                action_layout.addWidget(ro_lbl)

            self.table.setCellWidget(row_idx, 4, action_widget)

    def _populate_for_edit(self, cat: dict):
        """Populate category data into form for editing."""
        self.editing_category_id = cat.get("id")
        self.name_input.setText(cat.get("name") or "")
        self.desc_input.setText(cat.get("description") or "")
        self.save_btn.setText("تحديث الفئة")
        self.name_input.setFocus()
        self.name_input.selectAll()

    def _clear_form(self):
        """Clear form fields and reset to Add mode."""
        self.editing_category_id = None
        self.name_input.clear()
        self.desc_input.clear()
        self.save_btn.setText("حفظ الفئة")
        self.name_input.setFocus()

    def save_category(self):
        """Save a new category or update an existing one."""
        if self.current_user_role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لإدارة الأقسام.")
            return

        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()

        if not name:
            QMessageBox.warning(self, "بيانات ناقصة", "يرجى إدخال اسم الفئة أو القسم.")
            self.name_input.setFocus()
            return

        try:
            if self.editing_category_id:
                self.db.update_category(self.editing_category_id, name, desc)
                QMessageBox.information(self, "تم التحديث", f"تم تحديث الفئة '{name}' وتحديث المنتجات المرتبطة بها بنجاح.")
            else:
                self.db.create_category(name, desc)
                QMessageBox.information(self, "تمت الإضافة", f"تمت إضافة الفئة الجديدة '{name}' بنجاح.")

            self._clear_form()
            self.refresh_categories()

            # Trigger global update callback if provided
            if callable(self.on_categories_changed):
                try:
                    self.on_categories_changed()
                except Exception:
                    pass

        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def _delete_category(self, cat: dict):
        """Delete a category with confirmation and product re-assignment warning."""
        if self.current_user_role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لحذف الأقسام.")
            return

        cat_id = cat.get("id")
        name = cat.get("name")
        prod_count = int(cat.get("product_count", 0))

        msg = f"هل أنت متأكد من حذف الفئة '{name}'؟"
        if prod_count > 0:
            msg += f"\n\n⚠️ تنبيه: يوجد ({prod_count}) منتج مرتبط بهذه الفئة. سيتم إعادة تصنيف هذه المنتجات تلقائياً إلى 'أخرى'."

        reply = QMessageBox.question(
            self,
            "تأكيد حذف الفئة",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.db.delete_category(cat_id)
            QMessageBox.information(self, "تم الحذف", f"تم حذف الفئة '{name}' بنجاح.")
            if self.editing_category_id == cat_id:
                self._clear_form()
            self.refresh_categories()

            # Trigger global update callback
            if callable(self.on_categories_changed):
                try:
                    self.on_categories_changed()
                except Exception:
                    pass

        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))
