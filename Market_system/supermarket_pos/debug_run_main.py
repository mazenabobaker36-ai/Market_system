import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from database.db_manager import DBManager
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    db = DBManager()
    db.init_db()
    # fetch owner user
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM Users WHERE username = 'owner'")
    row = cur.fetchone()
    if not row:
        print('Owner user not found')
        sys.exit(1)
    user = {'id': row[0], 'username': row[1], 'role': row[2]}
    print('Creating MainWindow for', user)
    mw = MainWindow(db, user, None)
    mw.show()
    print('MainWindow shown, entering app.exec_()')
    sys.exit(app.exec_())
