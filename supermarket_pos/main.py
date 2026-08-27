import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from database.db_manager import DBManager
from ui.main_window import MainWindow
from ui.login_dialog import LoginDialog
from ui.theme import apply_bootstrap_theme


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    apply_bootstrap_theme(app)

    db = DBManager()
    db.init_db()

    login = LoginDialog(db)
    if login.exec_() != LoginDialog.Accepted:
        print("Login cancelled or failed, exiting.")
        sys.exit(0)

    print(f"Login accepted for user: {getattr(login, 'user', None)}")
    window = MainWindow(db, login.user, login.login_history_id)
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
