import json
from io import BytesIO

import qrcode
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
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


class InvoicesAdminTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
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

        search_row.addWidget(self.search_input)
        search_row.addWidget(self.view_btn)

        # Columns visually: Cashier | Total | Date/Time | Invoice No
        # Internally keep invoice_no at column 0 to preserve selection logic; _selected_invoice_id
        # will search the row for the item with UserRole data to remain robust.
        # Left table: Invoices list
        self.invoices_table = QTableWidget(0, 4)
        self.invoices_table.setHorizontalHeaderLabels(["اسم الكاشير", "إجمالي المبلغ", "التاريخ/الوقت", "رقم الفاتورة"])
        self.invoices_table.verticalHeader().setVisible(False)
        self.invoices_table.verticalHeader().setDefaultSectionSize(32)
        inv_head = self.invoices_table.horizontalHeader()
        inv_head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        inv_head.setSectionResizeMode(3, QHeaderView.Stretch)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.invoices_table.setSelectionMode(QTableWidget.SingleSelection)
        self.invoices_table.itemSelectionChanged.connect(self._on_invoice_selected)
        # double click opens invoice view
        self.invoices_table.doubleClicked.connect(lambda *_: self.open_selected_invoice())

        left_layout.addWidget(left_title)
        left_layout.addLayout(search_row)
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
        rows = self.db.list_invoices_admin(self.search_input.text())
        self.invoices_table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            # Visual order requested: Cashier | Total | Date/Time | Invoice No
            cashier_item = QTableWidgetItem(row.get("cashier_name") or "-")
            total_item = QTableWidgetItem(f"{row['total']:.2f}")
            datetime_item = QTableWidgetItem(row["created_at"])
            invoice_no_item = QTableWidgetItem(row["invoice_no"])  # will carry invoice id in UserRole
            invoice_no_item.setData(Qt.UserRole, row["id"])

            # Place items in columns 0..3 mapping to visual layout
            # Column 0: Cashier
            # Column 1: Total
            # Column 2: Date/Time
            # Column 3: Invoice No (stores id)
            self.invoices_table.setItem(i, 0, cashier_item)
            self.invoices_table.setItem(i, 1, total_item)
            self.invoices_table.setItem(i, 2, datetime_item)
            self.invoices_table.setItem(i, 3, invoice_no_item)

        self.invoices_table.resizeColumnsToContents()

        if rows:
            self.invoices_table.selectRow(0)
        else:
            self._clear_preview()

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
