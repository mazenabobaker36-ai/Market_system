import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from database.db_manager import DBManager
from ui.main_window import MainWindow
from ui.login_dialog import LoginDialog
from ui.theme import apply_bootstrap_theme
from licensing import ActivationDialog, LicenseManager
from updater import UpdateDialog
from utils.store_config import load_store_name


CURRENT_VERSION = "1.0.0"


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    apply_bootstrap_theme(app)

    license_manager = LicenseManager()
    try:
        local_license_available = license_manager.has_local_license()
        if local_license_available:
            local_state = license_manager.check_offline()
            if local_state.status == "offline_expired":
                local_license_available = False
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        local_license_available = False

    if not local_license_available:
        activation = ActivationDialog(license_manager)
        if activation.exec_() != ActivationDialog.Accepted:
            sys.exit(0)

    credentials = license_manager.stored_credentials()
    if credentials:
        update_dialog = UpdateDialog(credentials[0], CURRENT_VERSION)
        update_dialog.start()
        if update_dialog.exec_() == UpdateDialog.Accepted:
            update_dialog.launch_updater()
            sys.exit(0)

    db = DBManager()
    db.init_db()

    login = LoginDialog(db)
    if login.exec_() != LoginDialog.Accepted:
        print("Login cancelled or failed, exiting.")
        sys.exit(0)

    print(f"Login accepted for user: {getattr(login, 'user', None)}")
    window = MainWindow(
        db,
        login.user,
        login.login_history_id,
        license_manager,
        store_name=load_store_name(),
    )
    # keep a persistent reference on the QApplication so the window isn't garbage-collected
    setattr(app, "_main_window", window)

    # ensure login dialog is fully closed and scheduled for deletion so it doesn't interfere
    try:
        login.close()
        login.deleteLater()
    except Exception:
        pass

    print("Showing main window now (Maximized)...")
    window.showMaximized()
    try:
        # raise and activate to ensure it becomes visible on top of other windows/dialogs
        window.raise_()
        window.activateWindow()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: (window.raise_(), window.activateWindow()))
    except Exception:
        pass

    print("Main window shown; entering app.exec_")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
