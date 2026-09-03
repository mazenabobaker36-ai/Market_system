from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.login_history_id = None
        self.setWindowTitle("Retail POS - تسجيل الدخول")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setObjectName("loginDialog")
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("loginCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 28, 28, 28)
        cl.setSpacing(16)

        brand = QLabel("🛒 Retail POS")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet(
            "font-size: 22px; font-weight: 900; color: #2563eb;"
            " background: transparent; border-radius: 0;"
        )

        subtitle = QLabel("سجل الدخول للوصول إلى لوحة التحكم")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            "font-size: 13px; color: #64748b;"
            " background: transparent; border-radius: 0;"
        )

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("اسم المستخدم")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("كلمة المرور")
        self.password_input.returnPressed.connect(self.handle_login)

        form.addRow("اسم المستخدم:", self.username_input)
        form.addRow("كلمة المرور:", self.password_input)

        login_btn = QPushButton("تسجيل الدخول")
        login_btn.setProperty("variant", "primary")
        login_btn.clicked.connect(self.handle_login)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setProperty("variant", "outline")
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(login_btn)

        cl.addWidget(brand)
        cl.addWidget(subtitle)
        cl.addSpacing(6)
        cl.addLayout(form)
        cl.addSpacing(4)
        cl.addLayout(btn_row)

        outer.addWidget(card)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return

        user = self.db.validate_user(username, password)
        if not user:
            self.db.log_failed_login(username)
            QMessageBox.critical(self, "فشل", "بيانات الدخول غير صحيحة")
            return

        self.user = user
        self.login_history_id = self.db.log_login(user)
        self.accept()
