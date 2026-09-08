import csv
import json
from io import BytesIO

import qrcode
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDateEdit,
    QFileDialog,
    QFrame,
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

from ui.invoice_view_dialog import InvoiceViewDialog


class RefundDialog(QDialog):
    """Confirmation dialog showing the invoice before a full refund."""

    def __init__(self, invoice, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إرجاع الفاتورة / استرداد")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setModal(True)
        self.resize(560, 440)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"رقم الفاتورة: {invoice.get('invoice_no', '-') }"))
        layout.addWidget(QLabel(f"العميل: {invoice.get('customer_name') or 'عميل مباشر'}"))
        layout.addWidget(QLabel(f"التاريخ: {invoice.get('created_at', '-')}"))
        layout.addWidget(QLabel(f"الإجمالي القابل للاسترداد: {float(invoice.get('total') or 0):.2f} ج.م"))

        items_table = QTableWidget(0, 4)
        items_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "سعر الوحدة", "الإجمالي الفرعي"])
        items_table.verticalHeader().setVisible(False)
        items_table.horizontalHeader().setStretchLastSection(True)
        items = invoice.get("items", [])
        items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            items_table.setItem(row, 0, QTableWidgetItem(item.get("name") or "-"))
            items_table.setItem(row, 1, QTableWidgetItem(str(item.get("qty", 0))))
            items_table.setItem(row, 2, QTableWidgetItem(f"{float(item.get('manual_price') or 0):.2f}"))
            items_table.setItem(row, 3, QTableWidgetItem(f"{float(item.get('subtotal') or 0):.2f}"))
        layout.addWidget(items_table)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        confirm = buttons.addButton("تأكيد الاسترجاع", QDialogButtonBox.AcceptRole)
        confirm.setProperty("variant", "danger")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class InvoicesAdminTab(QWidget):
    def __init__(self, db, current_user_role="admin", on_refund=None):
        super().__init__()
        self.db = db
        self.current_user_role = (current_user_role or "").strip().lower()
        self.is_saler = self.current_user_role in {"saler", "seller", "بائع"}
        self._date_filter_active = False
        self.on_refund = on_refund
        self._build_ui()
        self.refresh_invoices()

    def _build_ui(self):
        # Split layout: Left = Invoice List, Right = Receipt Preview
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Left: Invoice list and search
        left_wrapper = QWidget()
        left_layout = QVBoxLayout(left_wrapper)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_title = QLabel("الفواتير وسجل المبيعات")
        left_title.setObjectName("pageTitleLabel")

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("تصفية برقم الفاتورة...")
        self.search_input.setObjectName("invoiceSearchInput")
        self.search_input.textChanged.connect(self.refresh_invoices)

        self.view_btn = QPushButton("عرض الفاتورة")
        self.view_btn.setProperty("variant", "primary")
        self.view_btn.setObjectName("invoiceViewBtn")
        self.view_btn.clicked.connect(self.open_selected_invoice)

        self.export_btn = QPushButton("📥 تصدير السجل")
        self.export_btn.setProperty("variant", "outline")
        self.export_btn.clicked.connect(self.export_invoices)

        search_row.addWidget(self.search_input)
        search_row.addWidget(self.view_btn)
        search_row.addWidget(self.export_btn)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("من تاريخ:"))
        self.start_date_edit = QDateEdit(QDate(2000, 1, 1))
        self.start_date_edit.setCalendarPopup(True)
        date_row.addWidget(self.start_date_edit)
        date_row.addWidget(QLabel("إلى تاريخ:"))
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        date_row.addWidget(self.end_date_edit)
        self.apply_date_btn = QPushButton("تطبيق التاريخ")
        self.apply_date_btn.setProperty("variant", "primary")
        self.apply_date_btn.clicked.connect(self._apply_date_filter)
        date_row.addWidget(self.apply_date_btn)

        if self.is_saler:
            self.start_date_edit.setDate(QDate.currentDate().addDays(-1))
            self.end_date_edit.setDate(QDate.currentDate())
            for control in (self.start_date_edit, self.end_date_edit, self.apply_date_btn):
                control.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.export_btn.setVisible(False)

        # Columns visually: Cashier | Total | Date/Time | Invoice No
        # Internally keep invoice_no at column 0 to preserve selection logic; _selected_invoice_id
        # will search the row for the item with UserRole data to remain robust.
        # Left table: Invoices list
        self.invoices_table = QTableWidget(0, 6)
        self.invoices_table.setHorizontalHeaderLabels([
            "اسم الكاشير", "إجمالي المبلغ", "التاريخ/الوقت", "رقم الفاتورة", "الحالة", "الإجراءات"
        ])
        self.invoices_table.verticalHeader().setVisible(False)
        self.invoices_table.verticalHeader().setDefaultSectionSize(32)
        inv_head = self.invoices_table.horizontalHeader()
        inv_head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.invoices_table.setSelectionMode(QTableWidget.SingleSelection)
        self.invoices_table.itemSelectionChanged.connect(self._on_invoice_selected)
        # double click opens invoice view
        self.invoices_table.doubleClicked.connect(lambda *_: self.open_selected_invoice())

        left_layout.addWidget(left_title)
        left_layout.addLayout(search_row)
        left_layout.addLayout(date_row)
        left_layout.addWidget(self.invoices_table)

        # Right: Receipt details card
        right_wrapper = QWidget()
        right_layout = QVBoxLayout(right_wrapper)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_title = QLabel("بطاقة الفاتورة")
        preview_title.setObjectName("pageTitleLabel")

        self.preview_card = QFrame()
        self.preview_card.setObjectName("invoicePreviewCard")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setSpacing(10)
        preview_layout.setContentsMargins(14, 14, 14, 14)

        # QR box centered
        self.qr_label = QLabel("لا يوجد رمز QR")
        self.qr_label.setObjectName("qrPreview")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumHeight(200)

        # Metadata block
        meta_block = QWidget()
        meta_layout = QVBoxLayout(meta_block)
        meta_layout.setSpacing(6)

        self.lbl_invoice_no = QLabel("رقم الفاتورة: -")
        self.lbl_datetime = QLabel("التاريخ/الوقت: -")
        self.lbl_cashier = QLabel("الكاشير: -")
        self.lbl_total = QLabel("الإجمالي: -")
        self.lbl_paid = QLabel("المدفوع: -")
        self.lbl_change = QLabel("الباقي: -")

        for w in [self.lbl_invoice_no, self.lbl_datetime, self.lbl_cashier, self.lbl_total, self.lbl_paid, self.lbl_change]:
            w.setProperty("role", "muted")

        meta_layout.addWidget(self.lbl_invoice_no)
        meta_layout.addWidget(self.lbl_datetime)
        meta_layout.addWidget(self.lbl_cashier)
        meta_layout.addWidget(self.lbl_total)
        meta_layout.addWidget(self.lbl_paid)
        meta_layout.addWidget(self.lbl_change)

        details_title = QLabel("تفاصيل الأصناف")
        details_title.setObjectName("sectionTitleLabel")

        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["الصنف", "الكمية", "السعر", "الإجمالي الفرعي"])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(45)

        items_head = self.items_table.horizontalHeader()
        items_head.setSectionResizeMode(0, QHeaderView.Stretch)          # Product Name (maximum space)
        items_head.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Quantity
        items_head.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Unit Price
        items_head.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Subtotal Price
        self.items_table.setColumnWidth(0, 140)
        self.items_table.setColumnWidth(2, 75)
        self.items_table.setColumnWidth(3, 85)

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
        self.items_table.setMinimumHeight(240)

        preview_layout.addWidget(self.qr_label)
        preview_layout.addWidget(meta_block)
        preview_layout.addWidget(details_title)
        preview_layout.addWidget(self.items_table)

        right_layout.addWidget(preview_title)
        right_layout.addWidget(self.preview_card)

        # Add to root: left list (2/3), right preview (1/3)
        root.addWidget(left_wrapper, 2)
        root.addWidget(right_wrapper, 1)

    def refresh_invoices(self):
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        rows = self.db.list_invoices_admin(
            self.search_input.text(),
            role=self.current_user_role,
            start_date=start_date if self._date_filter_active and not self.is_saler else None,
            end_date=end_date if self._date_filter_active and not self.is_saler else None,
        )
        self.invoices_table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            # Visual order requested: Cashier | Total | Date/Time | Invoice No
            cashier_item = QTableWidgetItem(row.get("cashier_name") or "-")
            total_item = QTableWidgetItem(f"{row['total']:.2f}")
            datetime_item = QTableWidgetItem(row["created_at"])
            invoice_no_item = QTableWidgetItem(row["invoice_no"])  # carries invoice id in UserRole
            invoice_no_item.setData(Qt.UserRole, row["id"])
            status = row.get("status") or "Completed"
            is_refunded = status in {"Refunded", "مرتجعة", "Partially Refunded", "مرتجعة جزئياً"}
            status_label = QLabel("مرتجعة" if is_refunded else "مكتملة")
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet(
                "QLabel { color: #ffffff; background: #dc2626; border-radius: 9px; padding: 3px 8px; font-weight: 700; }"
                if is_refunded
                else "QLabel { color: #166534; background: #dcfce7; border-radius: 9px; padding: 3px 8px; font-weight: 700; }"
            )

            # Place items in columns 0..5 mapping to visual layout
            # Column 0: Cashier
            # Column 1: Total
            # Column 2: Date/Time
            # Column 3: Invoice No (stores id)
            self.invoices_table.setItem(i, 0, cashier_item)
            self.invoices_table.setItem(i, 1, total_item)
            self.invoices_table.setItem(i, 2, datetime_item)
            self.invoices_table.setItem(i, 3, invoice_no_item)
            self.invoices_table.setCellWidget(i, 4, status_label)

            refund_btn = QPushButton("🔄 استرجاع")
            refund_btn.setProperty("variant", "danger")
            refund_btn.setCursor(Qt.PointingHandCursor)
            refund_btn.clicked.connect(lambda _, invoice_id=row["id"]: self.refund_invoice(invoice_id))
            if is_refunded or self.is_saler:
                refund_btn.setEnabled(False)
                refund_btn.setVisible(False)
            self.invoices_table.setCellWidget(i, 5, refund_btn)

        self.invoices_table.resizeColumnsToContents()

        if rows:
            self.invoices_table.selectRow(0)
        else:
            self._clear_preview()

    def _apply_date_filter(self):
        self._date_filter_active = True
        self.refresh_invoices()

    def _clear_preview(self):
        self.qr_label.setText("لا يوجد رمز QR")
        self.qr_label.setPixmap(QPixmap())
        self.lbl_invoice_no.setText("رقم الفاتورة: -")
        self.lbl_datetime.setText("التاريخ/الوقت: -")
        self.lbl_cashier.setText("الكاشير: -")
        self.lbl_total.setText("الإجمالي: -")
        self.lbl_paid.setText("المدفوع: -")
        self.lbl_change.setText("الباقي: -")
        self.items_table.setRowCount(0)

    def _selected_invoice_id(self):
        selected = self.invoices_table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        # Search the row for an item that carries the stored invoice id in UserRole.
        for col in range(self.invoices_table.columnCount()):
            item = self.invoices_table.item(row, col)
            if item is None:
                continue
            val = item.data(Qt.UserRole)
            if val is not None:
                return val
        # Fallback: try column 0 as before
        item0 = self.invoices_table.item(row, 0)
        return item0.data(Qt.UserRole) if item0 is not None else None

    def _on_invoice_selected(self):
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            return

        invoice = self.db.get_invoice_details(int(invoice_id))
        self._render_preview(invoice)

    def refund_invoice(self, invoice_id):
        if self.is_saler:
            QMessageBox.warning(self, "صلاحية غير كافية", "حساب البائع للعرض فقط ولا يمكنه استرجاع الفواتير.")
            return
        invoice = self.db.get_invoice_details(int(invoice_id))
        if not invoice or invoice.get("status") in {"Refunded", "مرتجعة", "Partially Refunded", "مرتجعة جزئياً"}:
            QMessageBox.information(self, "تنبيه", "تم استرجاع هذه الفاتورة مسبقاً")
            return

        dialog = RefundDialog(invoice, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            result = self.db.refund_invoice(int(invoice_id), role=self.current_user_role)
            QMessageBox.information(
                self,
                "تم الاسترجاع",
                "تم إتمام عملية الاسترجاع وإعادة المنتجات إلى المخزون بنجاح",
            )
            self.refresh_invoices()
            if callable(self.on_refund):
                self.on_refund(result)
        except Exception as exc:
            QMessageBox.critical(self, "خطأ في الاسترجاع", str(exc))

    def export_invoices(self):
        if self.is_saler:
            QMessageBox.warning(self, "صلاحية غير كافية", "لا يملك البائع صلاحية تصدير سجل الفواتير.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "تصدير سجل الفواتير", "سجل_الفواتير.csv", "CSV (*.csv)"
        )
        if not path:
            return
        rows = self.db.list_invoices_admin(
            self.search_input.text(),
            role=self.current_user_role,
            start_date=(self.start_date_edit.date().toString("yyyy-MM-dd") if self._date_filter_active else None),
            end_date=(self.end_date_edit.date().toString("yyyy-MM-dd") if self._date_filter_active else None),
        )
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output)
                writer.writerow(["رقم الفاتورة", "الكاشير", "التاريخ", "الإجمالي", "الحالة"])
                for row in rows:
                    writer.writerow([
                        row.get("invoice_no", "-"), row.get("cashier_name", "-"),
                        row.get("created_at", "-"), row.get("total", 0),
                        "مرتجعة" if row.get("status") == "Refunded" else "مكتملة",
                    ])
            QMessageBox.information(self, "تم التصدير", "تم تصدير سجل الفواتير بنجاح.")
        except OSError as exc:
            QMessageBox.critical(self, "خطأ في التصدير", str(exc))

    def open_selected_invoice(self):
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار فاتورة أولًا")
            return

        invoice = self.db.get_invoice_details(int(invoice_id))
        dialog = InvoiceViewDialog(invoice, self)
        dialog.exec_()

    def _render_preview(self, invoice):
        self.lbl_invoice_no.setText(f"رقم الفاتورة: {invoice['invoice_no']}")
        self.lbl_datetime.setText(f"التاريخ/الوقت: {invoice['created_at']}")
        self.lbl_cashier.setText(f"الكاشير: {invoice.get('username') or '-'}")
        self.lbl_total.setText(f"الإجمالي: {invoice['total']:.2f}")
        self.lbl_paid.setText(f"المدفوع: {invoice['paid']:.2f}")
        self.lbl_change.setText(f"الباقي: {invoice['change_amount']:.2f}")

        qr_data = invoice.get("qr_data") or ""
        pixmap = self._build_qr_pixmap(qr_data)
        if pixmap is None:
            self.qr_label.setText("رمز QR غير متاح")
            self.qr_label.setPixmap(QPixmap())
        else:
            self.qr_label.setText("")
            self.qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        items = invoice.get("items", [])
        self.items_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.items_table.setItem(i, 0, QTableWidgetItem(item.get("name") or "-"))
            qty_item = QTableWidgetItem(str(item.get("qty", 0)))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i, 1, qty_item)

            price_item = QTableWidgetItem(f"{float(item.get('manual_price', 0)):.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 2, price_item)

            sub_item = QTableWidgetItem(f"{float(item.get('subtotal', 0)):.2f}")
            sub_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 3, sub_item)

    def _build_qr_pixmap(self, qr_data: str):
        try:
            if not qr_data:
                return None

            # Ensure stored data is valid JSON payload or plain text.
            try:
                parsed = json.loads(qr_data)
                payload = json.dumps(parsed, ensure_ascii=False)
            except Exception:
                payload = qr_data

            qr_img = qrcode.make(payload)
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")

            qimage = QImage()
            ok = qimage.loadFromData(buffer.getvalue(), "PNG")
            if not ok:
                return None

            return QPixmap.fromImage(qimage)
        except Exception:
            return None
