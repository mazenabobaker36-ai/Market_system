# Supermarket POS (PyQt5 + QR)

نظام سوبرماركت محلي باستخدام Python و PyQt5 و SQLite، يدعم:

1. إدارة المخزون
2. الفواتير والإيصالات PDF
3. Dashboard
4. صفحة العملاء الدائمين
5. سجل دخول المستخدمين
6. 3 أنواع مستخدمين: `Owner`, `Admin`, `Saler`
7. تقرير الصلاحية + تقرير المبيعات

## هيكلية المشروع

```text
supermarket_pos/
├── main.py
├── requirements.txt
├── pos_database.db  (ينشأ تلقائياً)
├── database/
│   └── db_manager.py
├── ui/
│   ├── login_dialog.py
│   ├── cashier_window.py
│   └── stock_window.py
├── utils/
│   ├── invoice_pdf.py
│   └── barcode_helper.py
├── assets/
│   ├── invoice_template.html
│   └── styles.css
└── reports/
```

## التشغيل

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## حسابات افتراضية

- `owner / 1234`
- `admin / 1234`
- `saler / 1234`

## إنشاء ملف exe

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name supermarket_pos main.py
```

> إذا احتجت تضمين ملفات `assets` مع exe سأجهز لك أمر PyInstaller النهائي حسب نظامك.
