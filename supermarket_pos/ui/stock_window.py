import os
import shutil
import time
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QDate, QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCT_IMAGES_DIR = BASE_DIR / "assets" / "product_images"
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class StockWindow(QWidget):
    def __init__(self, db, current_user_role=None):
        super().__init__()
        self.db = db
        # role: 'Owner', 'Admin', 'Saler' (case-insensitive accepted)
        self.current_user_role = (current_user_role or '').strip().lower()
        self.editing_product_id = None
        self.selected_image_path: Optional[str] = None
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Page header
        header_row = QHBoxLayout()
        page_title = QLabel("إدارة المخزون والمنتجات")
        page_title.setObjectName("pageTitleLabel")

        # Excel instructions and bulk import buttons
        self.excel_info_btn = QPushButton("ℹ️ تعليمات وتنسيق Excel")
        self.excel_info_btn.setProperty("variant", "outline")
        self.excel_info_btn.setToolTip("عرض هيكل الأعمدة وقواعد التنسيق وتحميل نموذج Excel جاهز")
        self.excel_info_btn.clicked.connect(self.show_excel_instructions)

        self.import_excel_btn = QPushButton("📥 استيراد من ملف Excel")
        self.import_excel_btn.setProperty("variant", "outline")
        self.import_excel_btn.setToolTip("استيراد المنتجات والكميات دفعة واحدة من ملف Excel")
        self.import_excel_btn.clicked.connect(self.import_from_excel)

        self.add_btn = QPushButton("+ إضافة منتج جديد")
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(lambda: (self._clear_form(), self.barcode_input.setFocus()))

        header_row.addWidget(page_title)
        header_row.addStretch()
        header_row.addWidget(self.excel_info_btn)
        header_row.addWidget(self.import_excel_btn)
        header_row.addWidget(self.add_btn)
        root_layout.addLayout(header_row)

        # Search and filter bar (active and functional for all roles including Saler)
        filter_frame = QFrame()
        filter_frame.setObjectName("pageCard")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث بالاسم أو الباركود...")
        self.search_input.textChanged.connect(self.filter_table)

        self.filter_btn = QPushButton("تصفية")
        self.filter_btn.setProperty("variant", "primary")
        self.filter_btn.clicked.connect(self.filter_table)

        self.search_clear_btn = QPushButton("مسح")
        self.search_clear_btn.setProperty("variant", "outline")
        self.search_clear_btn.clicked.connect(self._clear_search)

        fl.addWidget(self.search_input, 3)
        fl.addWidget(self.filter_btn)
        fl.addWidget(self.search_clear_btn)
        root_layout.addWidget(filter_frame)

        # Add / update form (Grid with Category & Image Upload Preview)
        self.form_box = QGroupBox("إدخال شحنة جديدة / تحديث مخزون")
        grid = QGridLayout(self.form_box)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("الباركود")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم المنتج")
        self.qty_input = QLineEdit("1")
        self.qty_input.setPlaceholderText("الكمية")
        self.price_input = QLineEdit("0")
        self.price_input.setPlaceholderText("السعر")
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate().addDays(30))

        # Dynamic Category Combobox (Editable: cashier/admin can pick or type custom category)
        cat_layout = QHBoxLayout()
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(4)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.NoInsert)
        if self.category_combo.lineEdit():
            self.category_combo.lineEdit().setPlaceholderText("اختر أو اكتب قسماً جديداً...")
        self._refresh_categories_combo()

        self.add_cat_quick_btn = QToolButton()
        self.add_cat_quick_btn.setText("➕")
        self.add_cat_quick_btn.setToolTip("إضافة فئة / قسم جديد مباشرة")
        self.add_cat_quick_btn.clicked.connect(self._quick_add_category)

        cat_layout.addWidget(self.category_combo, 1)
        cat_layout.addWidget(self.add_cat_quick_btn)

        # Layout: text input fields
        grid.addWidget(QLabel("باركود / QR:"), 0, 0)
        grid.addWidget(self.barcode_input, 0, 1)
        grid.addWidget(QLabel("اسم المنتج:"), 0, 2)
        grid.addWidget(self.name_input, 0, 3)

        grid.addWidget(QLabel("الكمية المضافة:"), 1, 0)
        grid.addWidget(self.qty_input, 1, 1)
        grid.addWidget(QLabel("السعر الافتراضي:"), 1, 2)
        grid.addWidget(self.price_input, 1, 3)

        grid.addWidget(QLabel("تاريخ الانتهاء:"), 2, 0)
        grid.addWidget(self.expiry_input, 2, 1)
        grid.addWidget(QLabel("التصنيف / القسم:"), 2, 2)
        grid.addLayout(cat_layout, 2, 3)

        # Image Upload Section (Thumbnail preview + Select/Remove buttons)
        img_container = QVBoxLayout()
        img_container.setAlignment(Qt.AlignCenter)
        img_container.setSpacing(4)

        self.image_preview_lbl = QLabel()
        self.image_preview_lbl.setFixedSize(80, 80)
        self.image_preview_lbl.setAlignment(Qt.AlignCenter)
        self.image_preview_lbl.setStyleSheet(
            "QLabel { border: 2px dashed #cbd5e1; border-radius: 8px; background: #f8fafc; color: #94a3b8; font-size: 11px; }"
        )
        self.image_preview_lbl.setText("لا توجد صورة\n📷")

        img_btn_row = QHBoxLayout()
        img_btn_row.setSpacing(4)

        self.select_image_btn = QPushButton("📁 اختيار صورة")
        self.select_image_btn.setProperty("variant", "outline")
        self.select_image_btn.setToolTip("اختيار صورة للمنتج (PNG, JPG, WEBP)")
        self.select_image_btn.clicked.connect(self._choose_image)

        self.remove_image_btn = QPushButton("✖")
        self.remove_image_btn.setProperty("variant", "danger")
        self.remove_image_btn.setToolTip("إزالة الصورة")
        self.remove_image_btn.setFixedWidth(28)
        self.remove_image_btn.clicked.connect(self._clear_image)

        img_btn_row.addWidget(self.select_image_btn)
        img_btn_row.addWidget(self.remove_image_btn)

        img_container.addWidget(self.image_preview_lbl, 0, Qt.AlignCenter)
        img_container.addLayout(img_btn_row)

        grid.addLayout(img_container, 0, 4, 3, 1)

        # Buttons row
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("حفظ الشحنة")
        self.save_btn.setProperty("variant", "success")
        self.save_btn.clicked.connect(self.save_stock)

        self.edit_btn = QPushButton("تعديل")
        self.edit_btn.setProperty("variant", "primary")
        self.edit_btn.clicked.connect(self.populate_selected_for_edit)

        self.delete_btn = QPushButton("حذف")
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.clicked.connect(self.delete_selected_item)

        self.form_clear_btn = QPushButton("مسح")
        self.form_clear_btn.setProperty("variant", "outline")
        self.form_clear_btn.clicked.connect(self._clear_form)

        self.refresh_btn = QPushButton("تحديث الجدول")
        self.refresh_btn.setProperty("variant", "outline")
        self.refresh_btn.clicked.connect(self.refresh_table)

        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.form_clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.refresh_btn)

        grid.addLayout(btn_row, 3, 0, 1, 5)
        root_layout.addWidget(self.form_box)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "BARCODE", "PRODUCT NAME", "CATEGORY", "STOCK", "PRICE", "EXPIRY",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root_layout.addWidget(self.table)

        self._all_products = []

        # connect table selection to edit helper
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        # apply role-based permissions
        self.apply_role_permissions()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_categories_combo()

    def _refresh_categories_combo(self):
        """Populate the dynamic drop-down with all existing unique categories from database."""
        try:
            cats = self.db.get_distinct_categories()
        except Exception:
            try:
                with self.db._connect() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT name FROM Categories WHERE name IS NOT NULL AND TRIM(name) != ''
                        UNION
                        SELECT DISTINCT category FROM Products WHERE category IS NOT NULL AND TRIM(category) != ''
                        """
                    )
                    cats = [r[0].strip() for r in cur.fetchall() if r[0] and r[0].strip()]
            except Exception:
                cats = ["مشروبات", "أطعمة", "مخبوزات", "منظفات", "ألبان", "حلويات", "أخرى"]

        if not hasattr(self, "category_combo"):
            return

        current = self.category_combo.currentText().strip()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(cats)

        # Set up auto-completer for smooth inline typing
        completer = QCompleter(cats, self.category_combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.category_combo.setCompleter(completer)

        if current and current in cats:
            self.category_combo.setCurrentText(current)
        elif current:
            self.category_combo.addItem(current)
            self.category_combo.setCurrentText(current)
        elif "أخرى" in cats:
            self.category_combo.setCurrentText("أخرى")
        elif cats:
            self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)

    def _quick_add_category(self):
        """Prompt cashier/admin to quickly create a new category directly from the stock page."""
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لإضافة أقسام جديدة.")
            return

        cat_name, ok = QInputDialog.getText(
            self,
            "إضافة قسم / فئة جديدة",
            "اسم القسم أو الفئة الجديدة:",
            QLineEdit.Normal,
            "",
        )
        if ok and cat_name.strip():
            name = cat_name.strip()
            try:
                self.db.create_category(name, f"قسم {name}")
                QMessageBox.information(self, "تمت الإضافة", f"تمت إضافة الفئة '{name}' بنجاح.")
            except Exception:
                pass
            self._refresh_categories_combo()
            self.category_combo.setCurrentText(name)

            # Reload POS side panel and categories tab if parent window exists
            try:
                p_win = self.window()
                if hasattr(p_win, "load_products_side_panel"):
                    p_win.load_products_side_panel()
                if hasattr(p_win, "categories_tab"):
                    p_win.categories_tab.refresh_categories()
            except Exception:
                pass

    def show_excel_instructions(self):
        dlg = ExcelInstructionDialog(self)
        dlg.exec_()

    def _choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختيار صورة المنتج",
            "",
            "Images (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if file_path:
            self.selected_image_path = file_path
            self._display_image_preview(file_path)

    def _clear_image(self):
        self.selected_image_path = None
        self.image_preview_lbl.clear()
        self.image_preview_lbl.setText("لا توجد صورة\n📷")

    def _display_image_preview(self, path: Optional[str]):
        if path and os.path.isfile(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview_lbl.setPixmap(scaled)
                return
        self.image_preview_lbl.clear()
        self.image_preview_lbl.setText("لا توجد صورة\n📷")

    def apply_role_permissions(self):
        """Apply RBAC rules: Owner/Admin full access; Saler strict read-only access."""
        role = (self.current_user_role or "").strip().lower()
        is_saler = role in {"saler", "seller", "بائع"}

        # Hide top data entry form and bulk import for saler
        if hasattr(self, "form_box"):
            self.form_box.setVisible(not is_saler)
            self.form_box.setEnabled(not is_saler)

        if hasattr(self, "excel_info_btn"):
            self.excel_info_btn.setVisible(not is_saler)
            self.excel_info_btn.setEnabled(not is_saler)

        if hasattr(self, "import_excel_btn"):
            self.import_excel_btn.setVisible(not is_saler)
            self.import_excel_btn.setEnabled(not is_saler)

        if hasattr(self, "add_btn"):
            self.add_btn.setVisible(not is_saler)
            self.add_btn.setEnabled(not is_saler)

        if hasattr(self, "save_btn"):
            self.save_btn.setVisible(not is_saler)
            self.save_btn.setEnabled(not is_saler)

        if hasattr(self, "edit_btn"):
            self.edit_btn.setVisible(not is_saler)
            self.edit_btn.setEnabled(not is_saler)

        if hasattr(self, "delete_btn"):
            self.delete_btn.setVisible(not is_saler)
            self.delete_btn.setEnabled(not is_saler)

        if hasattr(self, "form_clear_btn"):
            self.form_clear_btn.setVisible(not is_saler)
            self.form_clear_btn.setEnabled(not is_saler)

        # Inputs editable only for admins/owners
        editable = not is_saler
        self.barcode_input.setEnabled(editable)
        self.name_input.setEnabled(editable)
        self.qty_input.setEnabled(editable)
        self.price_input.setEnabled(editable)
        self.expiry_input.setEnabled(editable)
        if hasattr(self, "category_combo"):
            self.category_combo.setEnabled(editable)

        # Table is strictly read-only
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def _clear_search(self):
        self.search_input.clear()
        self.filter_table()

    def _clear_form(self):
        self.barcode_input.clear()
        self.name_input.clear()
        self.qty_input.setText("1")
        self.price_input.setText("0")
        self.expiry_input.setDate(QDate.currentDate().addDays(30))
        if hasattr(self, "category_combo"):
            self.category_combo.setCurrentText("أخرى")
        self.editing_product_id = None
        self._clear_image()
        self.save_btn.setText("حفظ الشحنة")
        self.apply_role_permissions()

    def _on_table_selection_changed(self):
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            if hasattr(self, "edit_btn"):
                self.edit_btn.setEnabled(False)
            if hasattr(self, "delete_btn"):
                self.delete_btn.setEnabled(False)
            return

        selected = self.table.selectedItems()
        if not selected:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def populate_selected_for_edit(self):
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            return

        sel = self.table.selectedIndexes()
        if not sel:
            QMessageBox.warning(self, "اختيار", "يرجى تحديد صف للتعديل")
            return
        row = sel[0].row()
        pid = self._row_id_map.get(row)
        if not pid:
            QMessageBox.warning(self, "خطأ", "تعذر تحديد المنتج")
            return

        prod = next((p for p in self._all_products if p.get('id') == pid), None)
        if not prod:
            QMessageBox.warning(self, "خطأ", "لا يوجد منتج")
            return

        self.editing_product_id = pid
        self.barcode_input.setText(prod.get('barcode') or "")
        self.name_input.setText(prod.get('name') or "")
        self.qty_input.setText(str(int(float(prod.get('stock_qty') or 0))))
        self.price_input.setText(f"{float(prod.get('default_price') or 0.0):.2f}")
        if hasattr(self, "category_combo"):
            self.category_combo.setCurrentText(prod.get("category") or "أخرى")

        if prod.get('expiry_date'):
            try:
                self.expiry_input.setDate(QDate.fromString(prod.get('expiry_date'), 'yyyy-MM-dd'))
            except Exception:
                pass

        # Load product image if present
        img = prod.get('image_path')
        self.selected_image_path = img
        self._display_image_preview(img)

        self.save_btn.setText("تحديث المنتج")

    def filter_table(self):
        query = self.search_input.text().strip().lower()
        filtered = [
            p for p in self._all_products
            if not query
            or query in p.get("name", "").lower()
            or query in p.get("barcode", "").lower()
            or query in p.get("category", "").lower()
        ]
        self._render_table(filtered)
        self._on_table_selection_changed()

    def save_stock(self):
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لتعديل المخزون.")
            return

        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        if not barcode or not name:
            QMessageBox.warning(self, "بيانات ناقصة", "يرجى إدخال الباركود واسم المنتج")
            return
        try:
            qty = float(self.qty_input.text().strip())
            default_price = float(self.price_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "قيمة غير صحيحة", "الكمية والسعر يجب أن يكونا رقمين")
            return

        expiry_date = self.expiry_input.date().toString("yyyy-MM-dd")
        category = self.category_combo.currentText().strip() or "أخرى" if hasattr(self, "category_combo") else "أخرى"

        # Auto-create category in Categories table if newly typed
        if category and category != "أخرى":
            try:
                self.db.create_category(category, f"قسم {category}")
            except Exception:
                pass

        # Process image saving if a new external image was selected
        final_image_path = self.selected_image_path
        if self.selected_image_path and os.path.isfile(self.selected_image_path):
            src = Path(self.selected_image_path)
            # If not already inside PRODUCT_IMAGES_DIR, copy it
            if not str(src.resolve()).startswith(str(PRODUCT_IMAGES_DIR.resolve())):
                ext = src.suffix or ".png"
                safe_bc = "".join(c for c in barcode if c.isalnum() or c in ("-", "_")) or "prod"
                dest_filename = f"{safe_bc}_{int(time.time())}{ext}"
                dest_path = PRODUCT_IMAGES_DIR / dest_filename
                try:
                    shutil.copyfile(str(src), str(dest_path))
                    final_image_path = str(dest_path)
                    self.selected_image_path = final_image_path
                except Exception as e:
                    print(f"Warning: Failed to copy image: {e}")

        try:
            if self.editing_product_id:
                with self.db._connect() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE Products
                        SET barcode = ?, name = ?, stock_qty = ?, default_price = ?, expiry_date = ?, image_path = ?, category = ?
                        WHERE id = ?
                        """,
                        (barcode, name, qty, default_price, expiry_date, final_image_path, category, int(self.editing_product_id)),
                    )
            else:
                self.db.add_or_update_product(
                    barcode, name, qty, default_price, expiry_date, image_path=final_image_path, category=category
                )

            QMessageBox.information(self, "نجاح", "تم حفظ الشحنة وتحديث المخزون")
            self.refresh_table()
            self._refresh_categories_combo()
            self._clear_form()

            # Notify parent main window to reload POS side panel and categories tab
            try:
                p_win = self.window()
                if hasattr(p_win, "load_products_side_panel"):
                    p_win.load_products_side_panel()
                if hasattr(p_win, "categories_tab"):
                    p_win.categories_tab.refresh_categories()
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def import_from_excel(self):
        """Bulk Product Import via Excel File (.xlsx / .xls) with comprehensive validation."""
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لاستيراد المنتجات.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "استيراد المنتجات من ملف Excel",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if not file_path:
            return

        try:
            import pandas as pd
            df = pd.read_excel(file_path)
        except Exception:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheet = wb.active
                data = list(sheet.iter_rows(values_only=True))
                if not data or len(data) < 2:
                    QMessageBox.warning(self, "ملف فارغ", "الملف لا يحتوي على بيانات صالحة")
                    return
                import pandas as pd
                headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(data[0])]
                df = pd.DataFrame(data[1:], columns=headers)
            except Exception as e:
                QMessageBox.critical(self, "خطأ في قراءة الملف", f"تعذر قراءة ملف Excel:\n{str(e)}")
                return

        # Normalize column names for flexible matching
        col_map = {}
        for col in df.columns:
            c_clean = str(col).strip().lower()
            if c_clean in ["barcode", "الباركود", "باركود", "كود", "رمز", "code"]:
                col_map["barcode"] = col
            elif c_clean in ["product_name", "name", "product name", "اسم المنتج", "الاسم", "اسم_المنتج", "المنتج", "title"]:
                col_map["name"] = col
            elif c_clean in ["price", "default_price", "unit_price", "السعر", "سعر البيع", "سعر_الوحدة", "سعر", "price_unit"]:
                col_map["price"] = col
            elif c_clean in ["stock_qty", "stock", "quantity", "qty", "الكمية", "المخزون", "كمية المخزون", "count"]:
                col_map["stock_qty"] = col
            elif c_clean in ["expiry_date", "expiry", "expire_date", "تاريخ الانتهاء", "تاريخ_الانتهاء", "الصلاحية", "exp_date"]:
                col_map["expiry_date"] = col
            elif c_clean in ["category", "التصنيف", "القسم", "الفئة"]:
                col_map["category"] = col

        if "barcode" not in col_map or "name" not in col_map:
            QMessageBox.warning(
                self,
                "تنسيق غير صالح",
                "يجب أن يحتوي ملف Excel على عمودي الباركود (Barcode) واسم المنتج (Product_Name) على الأقل.\n\n"
                "الأعمدة المدعومة:\n[ Barcode | Product_Name | Category | Price | Stock_Qty | Expiry_Date ]",
            )
            return

        products_to_import = []
        import pandas as pd
        for _, row in df.iterrows():
            raw_barcode = row.get(col_map["barcode"])
            if pd.isna(raw_barcode) or not str(raw_barcode).strip():
                continue

            if isinstance(raw_barcode, float) and raw_barcode.is_integer():
                barcode = str(int(raw_barcode)).strip()
            else:
                barcode = str(raw_barcode).strip()

            raw_name = row.get(col_map["name"])
            if pd.isna(raw_name) or not str(raw_name).strip():
                continue
            name = str(raw_name).strip()

            category = "أخرى"
            if "category" in col_map and not pd.isna(row.get(col_map["category"])):
                category = str(row.get(col_map["category"])).strip() or "أخرى"

            # Price
            price = 0.0
            if "price" in col_map and not pd.isna(row.get(col_map["price"])):
                try:
                    price = float(row.get(col_map["price"]))
                except Exception:
                    price = 0.0

            # Stock
            stock = 0.0
            if "stock_qty" in col_map and not pd.isna(row.get(col_map["stock_qty"])):
                try:
                    stock = float(row.get(col_map["stock_qty"]))
                except Exception:
                    stock = 0.0

            # Expiry Date
            expiry = None
            if "expiry_date" in col_map and not pd.isna(row.get(col_map["expiry_date"])):
                try:
                    val = row.get(col_map["expiry_date"])
                    if hasattr(val, "strftime"):
                        expiry = val.strftime("%Y-%m-%d")
                    else:
                        expiry = str(val).strip()[:10]
                except Exception:
                    expiry = None

            products_to_import.append({
                "barcode": barcode,
                "name": name,
                "category": category,
                "default_price": price,
                "stock_qty": stock,
                "expiry_date": expiry,
            })

        if not products_to_import:
            QMessageBox.warning(self, "تنبيه", "لم يتم العثور على أي منتجات صالحة للاستيراد في الملف")
            return

        try:
            inserted, updated = self.db.bulk_import_products(products_to_import)
            total_processed = inserted + updated
            QMessageBox.information(
                self,
                "نجاح الاستيراد",
                f"تم استيراد {total_processed} منتج بنجاح إلى المخزون!\n(إضافة جديدة: {inserted} | تحديث مخزون: {updated})",
            )

            self.refresh_table()
            self._refresh_categories_combo()

            # Reload POS side panel
            try:
                p_win = self.window()
                if hasattr(p_win, "load_products_side_panel"):
                    p_win.load_products_side_panel()
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "خطأ أثناء الاستيراد", str(e))

    def refresh_table(self):
        self._all_products = self.db.list_products()
        self._render_table(self._all_products)
        self._refresh_categories_combo()
        self._on_table_selection_changed()
        self.apply_role_permissions()

    def _render_table(self, products):
        self._row_id_map = {}
        self.table.setRowCount(len(products))

        for row_idx, p in enumerate(products):
            self._row_id_map[row_idx] = p.get('id')
            stock_qty = float(p.get("stock_qty", 0))
            expiry = p.get("expiry_date") or "-"
            cat = p.get("category") or "أخرى"

            items = [
                QTableWidgetItem(str(p["id"])),
                QTableWidgetItem(p["barcode"]),
                QTableWidgetItem(p["name"]),
                QTableWidgetItem(cat),
                QTableWidgetItem(str(p["stock_qty"])),
                QTableWidgetItem(f"{float(p['default_price']):.2f} ج.م"),
                QTableWidgetItem(expiry),
            ]

            # If product has an image, attach a small thumbnail icon to the name cell
            img_path = p.get("image_path")
            if img_path and os.path.isfile(img_path):
                pm = QPixmap(img_path)
                if not pm.isNull():
                    items[2].setIcon(QIcon(pm.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, col, item)

            # Row color-coding based on stock availability
            if stock_qty == 0:
                bg = QBrush(QColor("#fef2f2"))
                fg = QBrush(QColor("#b91c1c"))
            elif stock_qty <= 5:
                bg = QBrush(QColor("#fffbeb"))
                fg = QBrush(QColor("#b45309"))
            else:
                bg = QBrush(QColor("#ffffff"))
                fg = QBrush(QColor("#334155"))

            for col in range(7):
                self.table.item(row_idx, col).setBackground(bg)
                self.table.item(row_idx, col).setForeground(fg)

        self.table.resizeColumnsToContents()
        self._on_table_selection_changed()
        self.apply_role_permissions()

    def delete_selected_item(self):
        """Delete currently selected product (Admin/Owner only)."""
        role = (self.current_user_role or "").strip().lower()
        if role in {"saler", "seller", "بائع"}:
            QMessageBox.warning(self, "صلاحية غير كافية", "عذراً، لا تملك صلاحية لحذف المنتجات.")
            return

        sel = self.table.selectedIndexes()
        if not sel:
            QMessageBox.warning(self, "اختيار", "يرجى تحديد صف للحذف")
            return
        row = sel[0].row()
        pid = self._row_id_map.get(row)
        if not pid:
            QMessageBox.warning(self, "خطأ", "تعذر تحديد المنتج للحذف")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "هل أنت متأكد من حذف المنتج المحدد؟ هذا الإجراء لا يمكن التراجع عنه.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            with self.db._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM Products WHERE id = ?", (pid,))
                if not cur.fetchone():
                    raise ValueError("المنتج غير موجود")
                cur.execute("DELETE FROM Products WHERE id = ?", (pid,))
            QMessageBox.information(self, "تم الحذف", "تم حذف المنتج بنجاح")
            self.refresh_table()
            self._clear_form()

            # Reload POS side panel
            try:
                p_win = self.window()
                if hasattr(p_win, "load_products_side_panel"):
                    p_win.load_products_side_panel()
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))


class ExcelInstructionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ℹ️ تعليمات وتنسيق استيراد ملف Excel")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(700, 580)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Header Title
        title = QLabel("📋 تعليمات وتنسيق ملف استيراد المنتجات (Excel Import Guide)")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title)

        desc = QLabel(
            "يمكنك إضافة وتحديث المنتجات والمخزون دفعة واحدة وبسرعة فائقة من خلال استيراد ملف Excel (.xlsx أو .xls).\n"
            "يرجى التأكد من مطابقة ترتيب وأسماء الأعمدة وقيم الحقول كما هو موضح أدناه:"
        )
        desc.setStyleSheet("color: #475569; font-size: 13px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Required Column Structure Banner (as requested in specifications)
        struct_box = QFrame()
        struct_box.setStyleSheet(
            "QFrame { background: #eff6ff; border: 1.5px solid #bfdbfe; border-radius: 8px; padding: 10px; }"
        )
        s_layout = QVBoxLayout(struct_box)
        s_layout.setContentsMargins(8, 6, 8, 6)
        s_layout.setSpacing(4)

        struct_title = QLabel("📌 هيكل الأعمدة المطلوب (Required Column Structure):")
        struct_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #1e40af;")
        
        struct_code = QLabel("[ Barcode  |  Product_Name  |  Category  |  Price  |  Stock_Qty  |  Expiry_Date ]")
        struct_code.setStyleSheet(
            "font-family: Consolas, monospace, 'Courier New'; font-size: 13px; font-weight: 900; color: #1d4ed8; background: #ffffff; padding: 6px 12px; border-radius: 6px; border: 1px solid #93c5fd;"
        )
        struct_code.setAlignment(Qt.AlignCenter)

        s_layout.addWidget(struct_title)
        s_layout.addWidget(struct_code)
        layout.addWidget(struct_box)

        # Table of Columns & Format Rules
        table = QTableWidget(6, 4)
        table.setHorizontalHeaderLabels(["اسم العمود (Excel)", "الاسم العربي", "نوع البيانات (Type)", "قواعد التنسيق والمثال (Rule & Example)"])
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)

        cols_data = [
            ("Barcode", "الباركود", "Unique String / Number (إلزامي)", "أرقام أو نصوص فريدة للباركود، مثل: 1000001 أو 628100123456"),
            ("Product_Name", "اسم المنتج", "String (إلزامي)", "نص الاسم التجاري للمنتج، مثل: Pepsi 330ml أو حليب كامل الدسم"),
            ("Category", "التصنيف", "String (اختياري)", "نص القسم أو التصنيف، مثل: Drinks / مشروبات، أطعمة، منظفات"),
            ("Price", "السعر", "Number / Decimal (إلزامي)", "رقم أو قيمة عشرية لسعر البيع الافتراضي، مثل: 1.50 أو 25.00"),
            ("Stock_Qty", "الكمية", "Integer (إلزامي)", "عدد صحيح يمثل رصيد المخزون، مثل: 50 أو 100"),
            ("Expiry_Date", "تاريخ الانتهاء", "Date (YYYY-MM-DD)", "تاريخ بصيغة سنة-شهر-يوم، مثل: 2026-12-31 أو 2027-06-30"),
        ]

        for r, row in enumerate(cols_data):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                if c == 0:
                    item.setForeground(QBrush(QColor("#2563eb")))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(r, c, item)

        table.resizeColumnsToContents()
        layout.addWidget(table)

        # Action Buttons: Download Template + Close
        btn_row = QHBoxLayout()
        sample_btn = QPushButton("📥 تحميل نموذج Excel تجريبي (.xlsx)")
        sample_btn.setProperty("variant", "primary")
        sample_btn.setStyleSheet("font-weight: bold; font-size: 13px; padding: 9px 18px;")
        sample_btn.setToolTip("توليد وتنزيل ملف Excel نموذجي يحتوي على جميع الأعمدة والبيانات التجريبية")
        sample_btn.clicked.connect(self._download_sample_template)

        close_btn = QPushButton("إغلاق")
        close_btn.setProperty("variant", "outline")
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(sample_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _download_sample_template(self):
        default_dir = str(Path.home() / "Downloads")
        if not os.path.exists(default_dir):
            default_dir = str(Path.home() / "Desktop")
        if not os.path.exists(default_dir):
            default_dir = str(Path.home())

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "📥 حفظ نموذج Excel تجريبي",
            os.path.join(default_dir, "قالب_استيراد_منتجات_نموذجي.xlsx"),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return

        try:
            import pandas as pd
            sample_data = {
                "Barcode": ["1000001", "1000002", "1000003", "1000004", "1000005"],
                "Product_Name": ["Pepsi 330ml", "عصير برتقال طبيعي 1 لتر", "خبز توست أبيض طازج", "شيبس بطاطس مقرمش", "سائل غسيل أطباق بالليمون"],
                "Category": ["مشروبات", "مشروبات", "مخبوزات", "أطعمة", "منظفات"],
                "Price": [1.50, 22.50, 18.00, 15.00, 32.00],
                "Stock_Qty": [50, 60, 25, 120, 40],
                "Expiry_Date": ["2026-12-31", "2026-10-31", "2026-09-15", "2027-01-20", "2028-05-01"],
            }
            df = pd.DataFrame(sample_data)
            df.to_excel(file_path, index=False)
            QMessageBox.information(
                self,
                "تم التحميل بنجاح",
                f"تم حفظ نموذج Excel التجريبي بنجاح في المسار:\n{file_path}\n\nيمكنك الآن تعبئة وتعديل بيانات المنتجات في الملف، ثم استيرادها إلى المخزون مباشرة بالضغط على 'استيراد من ملف Excel'.",
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر إنشاء الملف:\n{str(e)}")

