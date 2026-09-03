# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys

block_cipher = None

# Base directory is the supermarket_pos directory
SPECPATH = Path(globals().get('SPECPATH', os.path.dirname(os.path.abspath('main.py'))))

datas = [
    (str(SPECPATH / 'assets' / 'invoice_template.html'), 'assets'),
    (str(SPECPATH / 'assets' / 'styles.css'), 'assets'),
]

# Include seed database if it exists
if (SPECPATH / 'pos_database.db').exists():
    datas.append((str(SPECPATH / 'pos_database.db'), '.'))

# Include bundled sample product images if any
images_dir = SPECPATH / 'assets' / 'product_images'
if images_dir.exists():
    datas.append((str(images_dir), os.path.join('assets', 'product_images')))

hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'sqlite3',
    'weasyprint',
    'qrcode',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'utils.paths',
    'utils.invoice_pdf',
    'utils.barcode_helper',
    'database.db_manager',
    'ui.main_window',
    'ui.login_dialog',
    'ui.cashier_window',
    'ui.stock_window',
    'ui.categories_tab',
    'ui.dashboard_tab',
    'ui.invoices_admin_tab',
    'ui.user_admin_tab',
    'ui.invoice_view_dialog',
    'ui.theme',
]

a = Analysis(
    ['main.py'],
    pathex=[str(SPECPATH)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='supermarket_pos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='supermarket_pos',
)
