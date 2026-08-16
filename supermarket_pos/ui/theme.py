from PyQt5.QtWidgets import QApplication


RETAIL_QSS = r"""
/* ============================================================
   RETAIL POS — Complete QSS Theme
   Palette:
     App BG       #eef2f6
     White Card   #ffffff
     Blue Primary #2563eb
     Blue Active  #eff6ff
     Sidebar BG   #ffffff
     Text Dark    #0f172a
     Text Muted   #64748b
     Border       #e2e8f0
   ============================================================ */

/* ---------- Global Reset ---------- */
/* Removed unsupported 'box-sizing' to avoid Qt warnings */
* {
    margin: 0;
    padding: 0;
}

QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: 'Segoe UI', 'Inter', 'Tajawal', 'Arial', sans-serif;
    font-size: 13px;
    outline: none;
    selection-background-color: #dbeafe;
    selection-color: #1d4ed8;
}

QMainWindow, QDialog {
    background: #f8fafc;
}

QScrollBar:vertical {
    background: #f8fafc;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #f8fafc;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #94a3b8; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ============================================================
   SIDEBAR
   ============================================================ */
QFrame#sidebar {
    background: #ffffff;
    border-right: 2px solid #e8edf5;
    border-radius: 0;
}

QLabel#brandTitleLabel {
    font-size: 17px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.3px;
}

QToolButton#sidebarToggleBtn {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 17px;
    font-weight: 900;
    padding: 4px 6px;
    border-radius: 6px;
}
QToolButton#sidebarToggleBtn:hover {
    background: #eff6ff;
    color: #2563eb;
}

QLabel#menuSectionLabel {
    color: #94a3b8;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.8px;
    padding: 12px 10px 4px 10px;
    background: transparent;
    border-radius: 0;
}

QPushButton#navMenuBtn {
    text-align: right;
    background: transparent;
    color: #475569;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 9px 12px 9px 14px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#navMenuBtn:hover {
    background: #f8fafc;
    color: #1e293b;
    border-left: 3px solid #bfdbfe;
}
QPushButton#navMenuBtn:checked {
    background: #eff6ff;
    color: #1d4ed8;
    font-weight: 700;
    border-left: 3px solid #2563eb;
}
QPushButton#navMenuBtn:disabled {
    color: #cbd5e1;
    border-left: 3px solid transparent;
}

QLabel#profileBadge {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 12px;
    font-weight: 600;
    color: #334155;
}

QLabel#sidebarFooterLabel {
    color: #22c55e;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 10px;
    background: transparent;
    border-radius: 0;
}

/* ============================================================
   TOP HEADER BAR
   ============================================================ */
QFrame#topHeaderCard {
    background: #ffffff;
    border: 1px solid #e8edf5;
    border-radius: 10px;
    min-height: 52px;
}

QLineEdit#globalSearchInput {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 9px 12px;
    color: #334155;
    font-size: 13px;
}
QLineEdit#globalSearchInput:focus {
    background: #ffffff;
    border: 1.5px solid #2563eb;
}
QLineEdit#globalSearchInput::placeholder {
    color: #94a3b8;
}

QToolButton#iconGhostBtn {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 9px;
    color: #475569;
    font-size: 15px;
}
QToolButton#iconGhostBtn:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: #2563eb;
}

QPushButton#profilePillBtn {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 999px;
    color: #1e293b;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#profilePillBtn:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: #1d4ed8;
}

QLabel#breadcrumbLabel {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 6px;
    background: transparent;
    border-radius: 0;
}

/* ============================================================
   CARDS & CONTAINERS
   ============================================================ */
QFrame#pageCard,
QFrame#invoicePreviewCard,
QFrame#posLeftPanel,
QFrame#posRightPanel,
QFrame#posSummaryBox {
    background: #ffffff;
    border: 1px solid #e8edf5;
    border-radius: 10px;
}

QGroupBox {
    background: #ffffff;
    border: 1.5px solid #e8edf5;
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 700;
    font-size: 13px;
    color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #334155;
    font-weight: 800;
    font-size: 13px;
}

/* ============================================================
   STAT DASHBOARD CARDS
   ============================================================ */
QFrame[card="stat"] {
    border-radius: 12px;
    border: 1px solid transparent;
    min-height: 110px;
}
/* Top stat palettes with higher contrast */
QFrame[cardVariant="products"] {
    background: #ffffff;
    border: 1px solid #e6eefc;
}
QFrame[cardVariant="sales"] {
    background: #2563eb; /* vibrant blue */
    border: 1px solid #1e40af;
}
QFrame[cardVariant="low_stock"], QFrame[cardVariant="low_stock"] QLabel {
    /* low stock soft yellow */
    background: #fefce8;
    border: 1px solid #fde047;
}
QFrame[cardVariant="out_of_stock"] {
    background: #fef2f2; /* soft red */
    border: 1px solid #fca5a5;
}

QLabel#statIconLabel {
    font-size: 26px;
    background: transparent;
}
QLabel#statTitleLabel {
    font-size: 12px;
    font-weight: 800;
    color: #1e293b;
    background: transparent;
    letter-spacing: 0.5px;
}
QLabel#statValueLabel {
    font-size: 32px;
    font-weight: 900;
    color: #1e293b;
    background: transparent;
}
QLabel#statSubLabel {
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    background: transparent;
}

/* Specific overrides for palette choices */
QFrame[cardVariant="sales"] QLabel#statValueLabel { color: #ffffff; }
QFrame[cardVariant="sales"] QLabel#statTitleLabel { color: #ffffff; }
QFrame[cardVariant="products"] QLabel#statValueLabel { color: #1e293b; }
QFrame[cardVariant="low_stock"] QLabel#statValueLabel { color: #a16207; }
QFrame[cardVariant="out_of_stock"] QLabel#statValueLabel { color: #dc2626; }

/* Shortcut action cards sizing */
QPushButton#shortcutCard {
    min-height: 85px;
    max-height: 100px;
}

/* Table item spacing */
QTableWidget {
    gridline-color: #f1f5f9;
}
QTableWidget::item {
    padding: 8px 12px;
}

/* Modern pill-style tabs for Reports */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background: #ffffff;
    border-radius: 12px;
    top: -1px;
}
QTabBar::tab {
    background: #f1f5f9;
    color: #64748b;
    padding: 10px 20px;
    margin-right: 6px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #2563eb;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background: #e2e8f0;
    color: #1e293b;
}

/* ============================================================
   INPUTS & FORM ELEMENTS
   ============================================================ */
QLineEdit,
QComboBox,
QDateEdit,
QSpinBox,
QDoubleSpinBox,
QTextEdit {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 9px 12px;
    color: #1e293b;
    font-size: 13px;
    min-height: 16px;
    selection-background-color: #dbeafe;
}
QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QTextEdit:focus {
    background: #ffffff;
    border: 1.5px solid #2563eb;
}
QLineEdit:hover,
QComboBox:hover,
QDateEdit:hover {
    border-color: #93c5fd;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
    padding-right: 6px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
    padding: 4px;
}

QCheckBox {
    color: #334155;
    font-weight: 600;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border-color: #2563eb;
}

/* ============================================================
   BUTTONS
   ============================================================ */
QPushButton {
    background: #64748b;
    color: #ffffff;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.2px;
}
QPushButton:hover { background: #475569; }
QPushButton:pressed { background: #334155; }
QPushButton:disabled {
    background: #e2e8f0;
    color: #94a3b8;
}

QPushButton[variant="primary"] {
    background: #2563eb;
    color: #ffffff;
}
QPushButton[variant="primary"]:hover { background: #1d4ed8; }
QPushButton[variant="primary"]:pressed { background: #1e40af; }

QPushButton[variant="success"] {
    background: #10b981;
    color: #ffffff;
}
QPushButton[variant="success"]:hover { background: #059669; }
QPushButton[variant="success"]:pressed { background: #047857; }

QPushButton[variant="danger"] {
    background: #ef4444;
    color: #ffffff;
}
QPushButton[variant="danger"]:hover { background: #dc2626; }
QPushButton[variant="danger"]:pressed { background: #b91c1c; }

QPushButton[variant="orange"] {
    background: #f97316;
    color: #ffffff;
}
QPushButton[variant="orange"]:hover { background: #ea580c; }
QPushButton[variant="orange"]:pressed { background: #c2410c; }

QPushButton[variant="dark"] {
    background: #0f172a;
    color: #ffffff;
}
QPushButton[variant="dark"]:hover { background: #1e293b; }
QPushButton[variant="dark"]:pressed { background: #020617; }

QPushButton[variant="outline"] {
    background: transparent;
    color: #475569;
    border: 1.5px solid #e2e8f0;
}
QPushButton[variant="outline"]:hover {
    background: #f8fafc;
    border-color: #2563eb;
    color: #2563eb;
}

QPushButton[variant="cyan"] {
    background: #06b6d4;
    color: #ffffff;
}
QPushButton[variant="cyan"]:hover { background: #0891b2; }

QPushButton[variant="purple"] {
    background: #8b5cf6;
    color: #ffffff;
}
QPushButton[variant="purple"]:hover { background: #7c3aed; }

/* Nav category / payment method pills */
QPushButton#categoryTabBtn,
QPushButton#payMethodBtn {
    background: #f8fafc;
    color: #475569;
    border: 1.5px solid #e2e8f0;
    border-radius: 999px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton#categoryTabBtn:checked,
QPushButton#payMethodBtn:checked {
    background: #eff6ff;
    color: #1d4ed8;
    border-color: #93c5fd;
    font-weight: 700;
}
QPushButton#categoryTabBtn:hover,
QPushButton#payMethodBtn:hover {
    background: #f1f5f9;
    border-color: #93c5fd;
}

/* Report filter pills */
QPushButton#reportPillBtn {
    background: #f8fafc;
    color: #475569;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 700;
    font-size: 12px;
}
QPushButton#reportPillBtn:checked {
    background: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
}
QPushButton#reportPillBtn:hover { background: #f1f5f9; }

/* Action icon buttons in tables */
QPushButton#actionViewBtn {
    background: #e0f2fe;
    color: #0369a1;
    border: none;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#actionEditBtn {
    background: #cffafe;
    color: #0e7490;
    border: none;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#actionDeleteBtn {
    background: #fee2e2;
    color: #b91c1c;
    border: none;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#actionViewBtn:hover { background: #bae6fd; }
QPushButton#actionEditBtn:hover { background: #a5f3fc; }
QPushButton#actionDeleteBtn:hover { background: #fecaca; }

/* ============================================================
   TABLES
   ============================================================ */
QTableWidget {
    background: #ffffff;
    border: 1px solid #e8edf5;
    border-radius: 10px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
    alternate-background-color: #f8fafc;
    font-size: 13px;
    color: #334155;
}

QHeaderView {
    background: transparent;
    border-radius: 0;
}
QHeaderView::section {
    background: #f8fafc;
    color: #64748b;
    padding: 10px 12px;
    border: none;
    border-bottom: 1.5px solid #e8edf5;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background: #f1f5f9;
    color: #334155;
}

QTableWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:selected {
    background: #eff6ff;
    color: #1d4ed8;
}

/* ============================================================
   LABELS / TYPOGRAPHY
   ============================================================ */
QLabel#pageTitleLabel {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    background: transparent;
    border-radius: 0;
}
QLabel#pageSubtitleLabel {
    font-size: 12px;
    color: #64748b;
    background: transparent;
    border-radius: 0;
}
QLabel#sectionTitleLabel {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    background: transparent;
    border-radius: 0;
}
QLabel[role="muted"] {
    color: #64748b;
    background: transparent;
    border-radius: 0;
}
QLabel[role="value"] {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    background: transparent;
    border-radius: 0;
}

/* Invoice badges */
QLabel#invoiceBadgeBlue {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#statusBadgeGreen {
    background: #d1fae5;
    color: #065f46;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#statusBadgeRed {
    background: #fee2e2;
    color: #b91c1c;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#statusBadgeYellow {
    background: #fef3c7;
    color: #92400e;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#statusBadgeBlue {
    background: #dbeafe;
    color: #1e40af;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}

/* QR Preview */
QLabel#qrPreview {
    background: #f8fafc;
    border: 1.5px dashed #cbd5e1;
    border-radius: 10px;
    color: #64748b;
    font-weight: 600;
    padding: 12px;
}

/* POS product card */
QFrame#quickProductCard {
    background: #ffffff;
    border: 1.5px solid #e8edf5;
    border-radius: 10px;
}
QFrame#quickProductCard:hover {
    border: 1.5px solid #93c5fd;
    background: #fafcff;
}
QLabel#quickProductName {
    font-weight: 700;
    color: #0f172a;
    font-size: 13px;
    background: transparent;
    border-radius: 0;
}
QLabel#stockBadge {
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fde68a;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#posHintLabel {
    color: #64748b;
    font-weight: 600;
    background: transparent;
    border-radius: 0;
}

/* Invoice dark header */
QFrame#invoiceDarkHeader {
    background: #1e293b;
    border-radius: 10px;
}
QLabel#invoiceHeaderText {
    color: #ffffff;
    font-weight: 700;
    background: transparent;
    border-radius: 0;
}
QLabel#invoiceHeaderTitle {
    color: #f1f5f9;
    font-size: 24px;
    font-weight: 900;
    background: transparent;
    border-radius: 0;
}

/* Compact shortcut cards */
QFrame#shortcutCard {
    background: #ffffff;
    border: 1px solid #e8edf5;
    border-radius: 10px;
}

/* Activity / log items */
QFrame#activityItem {
    background: #f8fafc;
    border: 1px solid #f1f5f9;
    border-radius: 8px;
    padding: 2px;
}

/* ============================================================
   LOGIN DIALOG
   ============================================================ */
QDialog#loginDialog {
    background: #eef2f6;
    border-radius: 16px;
}
QFrame#loginCard {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
}

/* ============================================================
   MISC
   ============================================================ */
QSplitter::handle {
    background: #e2e8f0;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover { background: #93c5fd; }

QAbstractScrollArea {
    background: #ffffff;
    border-radius: 10px;
}

QToolTip {
    background: #0f172a;
    color: #f8fafc;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 600;
}

QMessageBox {
    background: #ffffff;
}
QMessageBox QPushButton {
    min-width: 80px;
}

QProgressBar {
    background: #e2e8f0;
    border-radius: 4px;
    height: 8px;
    border: none;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 4px;
}
"""


def apply_bootstrap_theme(app: QApplication) -> None:
    app.setStyleSheet(RETAIL_QSS)
