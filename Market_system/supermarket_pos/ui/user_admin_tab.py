from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class UserAdminTab(QWidget):
    def __init__(self, db, current_user):
        super().__init__()
        self.db = db
        self.current_user = current_user
        self._build_ui()
        self.refresh_users()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("User Management")
        title.setObjectName("pageTitleLabel")
        sub = QLabel("إدارة حسابات المستخدمين وصلاحياتهم")
        sub.setObjectName("pageSubtitleLabel")
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(sub)

        # نموذج إضافة مستخدم
        add_box = QGroupBox("إضافة مستخدم جديد")
        add_form = QFormLayout(add_box)
        add_form.setHorizontalSpacing(10)
        add_form.setVerticalSpacing(6)

        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("اسم المستخدم أو البريد")

        self.new_role = QComboBox()
        # Restrict role options: Owner creation is not allowed via UI to enforce single-owner policy
        self.new_role.addItems(["admin", "saler"])

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText("كلمة المرور")

        self.add_user_btn = QPushButton("إضافة المستخدم")
        self.add_user_btn.setProperty("variant", "success")
        self.add_user_btn.clicked.connect(self.add_user)
        # Override connection with a robust handler that passes password correctly
        try:
            self.add_user_btn.clicked.disconnect()
        except Exception:
            pass
        self.add_user_btn.clicked.connect(self._add_user_handler)

        add_form.addRow("اسم المستخدم:", self.new_username)
        add_form.addRow("الدور:", self.new_role)
        add_form.addRow("كلمة المرور:", self.new_password)
        add_form.addRow(self.add_user_btn)

        # جدول المستخدمين
        self.users_table = QTableWidget(0, 5)
        self.users_table.setMinimumHeight(200)
        self.users_table.setHorizontalHeaderLabels([
            "المعرف",
            "اسم المستخدم",
            "الدور",
            "الحالة",
            "تاريخ الإنشاء",
        ])
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.itemSelectionChanged.connect(self.load_selected_user)

        # تعديل مستخدم
        edit_box = QGroupBox("تعديل الحساب المحدد")
        edit_form = QFormLayout(edit_box)
        edit_form.setHorizontalSpacing(10)
        edit_form.setVerticalSpacing(6)

        self.edit_user_id = QLabel("-")
        self.edit_username = QLineEdit()

        self.edit_role = QComboBox()
        # Editing role: disallow assigning Owner through UI
        self.edit_role.addItems(["admin", "saler"])

        self.edit_active = QCheckBox("الحساب نشط")

        self.update_btn = QPushButton("حفظ التعديلات")
        self.update_btn.setProperty("variant", "primary")
        self.update_btn.clicked.connect(self.update_user)

        self.reset_password_input = QLineEdit()
        self.reset_password_input.setEchoMode(QLineEdit.Password)
        self.reset_password_input.setPlaceholderText("كلمة مرور جديدة")

        self.reset_password_btn = QPushButton("تحديث كلمة المرور")
        self.reset_password_btn.setProperty("variant", "primary")
        self.reset_password_btn.clicked.connect(self.reset_password)

        self.delete_btn = QPushButton("حذف المستخدم")
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.clicked.connect(self.delete_user)

        edit_form.addRow("المعرف:", self.edit_user_id)
        edit_form.addRow("اسم المستخدم:", self.edit_username)
        edit_form.addRow("الدور:", self.edit_role)
        edit_form.addRow("الحالة:", self.edit_active)
        edit_form.addRow(self.update_btn)
        edit_form.addRow("إعادة تعيين كلمة المرور:", self.reset_password_input)
        edit_form.addRow(self.reset_password_btn)
        edit_form.addRow(self.delete_btn)

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "muted")

        root.addWidget(add_box)
        root.addWidget(self.users_table)
        root.addWidget(edit_box)
        root.addWidget(self.status_label)

    def _selected_user_id(self):
        selected = self.users_table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        item = self.users_table.item(row, 0)
        if not item:
            return None
        return int(item.text())

    def refresh_users(self):
        rows = self.db.list_users_admin()
        self.users_table.setRowCount(len(rows))

        role_map = {"Owner": "owner", "Admin": "admin", "Saler": "saler"}

        for i, row in enumerate(rows):
            self.users_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))

            user_item = QTableWidgetItem(row["username"])
            user_item.setForeground(QBrush(QColor("#1d4ed8")))
            self.users_table.setItem(i, 1, user_item)

            self.users_table.setItem(i, 2, QTableWidgetItem(role_map.get(row["role"], row["role"])))

            is_active = row["is_active"]
            status_item = QTableWidgetItem("نشط" if is_active else "موقوف")
            status_item.setForeground(QBrush(QColor("#059669" if is_active else "#b91c1c")))
            status_item.setBackground(QBrush(QColor("#d1fae5" if is_active else "#fee2e2")))
            self.users_table.setItem(i, 3, status_item)

            self.users_table.setItem(i, 4, QTableWidgetItem(row["created_at"]))

        self.users_table.resizeColumnsToContents()
        if rows:
            self.users_table.selectRow(0)

    def load_selected_user(self):
        user_id = self._selected_user_id()
        if user_id is None:
            return

        row = self.users_table.currentRow()
        self.edit_user_id.setText(str(user_id))
        self.edit_username.setText(self.users_table.item(row, 1).text())
        self.edit_role.setCurrentText(self.users_table.item(row, 2).text())
        self.edit_active.setChecked(self.users_table.item(row, 3).text() == "نشط")

    def add_user(self):
        # Legacy/placeholder method retained for compatibility but disabled.
        # Use _add_user_handler bound to the button which supplies the password properly.
        self._status_error("الطريقة القديمة لإضافة المستخدم غير متاحة")

    def _add_user_handler(self):
        username = self.new_username.text().strip()
        role = self.new_role.currentText()
        password = self.new_password.text().strip()

        if not username:
            self._status_error("يرجى إدخال اسم المستخدم")
            return
        if not password:
            self._status_error("يرجى إدخال كلمة المرور")
            return

        try:
            # Defensive check: ensure only one Owner exists in DB
            if role.strip().lower() in ('owner', 'مالك'):
                with self.db._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) as c FROM Users WHERE role = 'Owner'")
                    if cur.fetchone()[0] > 0:
                        raise ValueError("Error: Only one Owner account is allowed in the system.")

            # Use DB manager API which handles hashing and insertion
            self.db.create_user_admin(username=username, role=role, password=password)
            self.new_username.clear()
            self.new_password.clear()
            self.refresh_users()
            self._status_ok("تمت إضافة المستخدم بنجاح")

        except Exception as e:
            self._status_error(str(e))

    def update_user(self):
        user_id = self._selected_user_id()
        if user_id is None:
            self._status_error("يرجى اختيار مستخدم")
            return

        try:
            role = self.edit_role.currentText()
            # Defensive: prevent assigning Owner role if an Owner already exists and it's not this user
            if role.strip().lower() in ('owner', 'مالك'):
                with self.db._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM Users WHERE role = 'Owner'")
                    row = cur.fetchone()
                    if row and int(row['id']) != int(user_id):
                        raise ValueError("Error: Only one Owner account is allowed in the system.")

            self.db.update_user_admin(
                user_id=user_id,
                username=self.edit_username.text(),
                role=self.edit_role.currentText(),
                is_active=self.edit_active.isChecked(),
            )
            self.refresh_users()
            self._status_ok("تم حفظ التعديلات")
        except Exception as e:
            self._status_error(str(e))

    def reset_password(self):
        user_id = self._selected_user_id()
        if user_id is None:
            self._status_error("يرجى اختيار مستخدم")
            return

        try:
            self.db.reset_user_password_admin(user_id, self.reset_password_input.text())
            self.reset_password_input.clear()
            self._status_ok("تم تحديث كلمة المرور")
        except Exception as e:
            self._status_error(str(e))

    def delete_user(self):
        user_id = self._selected_user_id()
        if user_id is None:
            self._status_error("يرجى اختيار مستخدم")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا المستخدم؟ لا يمكن التراجع.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            # Prevent deleting currently logged-in user
            if self.current_user and int(user_id) == int(self.current_user.get("id")):
                raise ValueError("لا يمكن حذف الحساب المستخدم حاليًا")

            # Use DB manager helper which handles checks and commits
            current_id = self.current_user.get('id') if self.current_user else None
            self.db.delete_user_admin(int(user_id), current_user_id=current_id)

            self.refresh_users()
            self._status_ok("تم حذف المستخدم")
        except Exception as e:
            self._status_error(str(e))

    def _status_ok(self, msg: str):
        self.status_label.setStyleSheet("color:#198754; font-weight:700;")
        self.status_label.setText(msg)

    def _status_error(self, msg: str):
        self.status_label.setStyleSheet("color:#dc3545; font-weight:700;")
        self.status_label.setText(msg)
