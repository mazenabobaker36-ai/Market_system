from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .manager import LicenseManager, LicenseState
from .worker import LicenseCheckWorker


class ActivationDialog(QDialog):
    activated = pyqtSignal(object)

    def __init__(self, manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.worker = None
        self.setWindowTitle("تفعيل نظام السوبرماركت")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setObjectName("loginDialog")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        card = QFrame()
        card.setObjectName("loginCard")
        form = QFormLayout(card)
        form.setContentsMargins(28, 28, 28, 28)
        title = QLabel("🔐 تفعيل الترخيص")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #2563eb;")
        subtitle = QLabel("أدخل Store ID و License Key لتفعيل نقطة البيع")
        subtitle.setAlignment(Qt.AlignCenter)
        self.store_input = QLineEdit()
        self.store_input.setPlaceholderText("Store_ID")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("License_Key")
        self.key_input.returnPressed.connect(self.activate)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.activate_btn = QPushButton("تفعيل")
        self.activate_btn.setProperty("variant", "primary")
        self.activate_btn.clicked.connect(self.activate)
        form.addRow(title)
        form.addRow(subtitle)
        form.addRow("Store ID:", self.store_input)
        form.addRow("License Key:", self.key_input)
        form.addRow(self.status_label)
        form.addRow(self.activate_btn)
        layout.addWidget(card)

    def activate(self):
        store_id, license_key = self.store_input.text().strip(), self.key_input.text().strip()
        if not store_id or not license_key:
            self.status_label.setText("يرجى إدخال Store ID و License Key")
            return
        self.activate_btn.setEnabled(False)
        self.status_label.setText("جارٍ التحقق من الترخيص...")
        self.worker = LicenseCheckWorker(self.manager, store_id, license_key, interval_seconds=1)
        self.worker.checked.connect(self._on_result)
        self.worker.failed.connect(self._on_error)
        self.worker.start()

    def _on_result(self, state: LicenseState):
        if state.status == "active":
            self.activated.emit(state)
            self.accept()
        else:
            self._on_error("الترخيص غير نشط أو محظور")

    def _on_error(self, message: str):
        self.activate_btn.setEnabled(True)
        self.status_label.setText(f"تعذر تفعيل الترخيص: {message}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)


class LicenseLockOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(15, 23, 42, 245);")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel("🔒 الوصول مقفل")
        title.setStyleSheet("color: white; font-size: 30px; font-weight: 900;")
        message = QLabel("عذراً، انتهت مدة الاشتراك الشهري. يرجى التجديد عبر لوحة التحكم")
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("color: #e2e8f0; font-size: 18px;")
        layout.addWidget(title)
        layout.addWidget(message)
