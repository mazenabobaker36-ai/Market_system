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

## إنشاء ملف التثبيت للويندوز (Setup.exe)

### 1. عبر GitHub Actions (تلقائياً من المتصفح بدون أي إعدادات)
1. ارفع التعديلات على مستودع GitHub:
   ```bash
   git push origin main
   ```
2. ادخل إلى تبويب **Actions** في صفحة المشروع على GitHub.
3. اختر سير عمل **Build Windows Setup**.
4. عند اكتمال البناء، ستجد ملف **`Supermarket_POS_Setup.exe`** جاهزاً للتحميل المباشر كـ Artifact!

---

### 2. محلياً على جهاز يعمل بنظام Windows
1. تأكد من تثبيت **Python 3.11** أو **3.12**.
2. (اختياري) لتجميع ملف الـ Setup، ثبّت [Inno Setup 6](https://jrsoftware.org/isdl.php).
3. شغّل الملف:
   ```cmd
   build_setup.bat
   ```
4. سينتج ملف التثبيت النهائي داخل مجلد `dist_installer\Supermarket_POS_Setup.exe`.

