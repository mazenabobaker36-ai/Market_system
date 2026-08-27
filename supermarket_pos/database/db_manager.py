import hashlib
import hmac
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "pos_database.db"


class DBManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with self._connect() as conn:
            cur = conn.cursor()

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Owner', 'Admin', 'Saler')),
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Login_History (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    login_at TEXT NOT NULL,
                    logout_at TEXT,
                    status TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES Users(id)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    stock_qty REAL NOT NULL DEFAULT 0,
                    default_price REAL NOT NULL DEFAULT 0,
                    expiry_date TEXT,
                    image_path TEXT,
                    category TEXT DEFAULT 'أخرى',
                    created_at TEXT NOT NULL
                )
                """
            )

            # Ensure image_path and category columns exist in Products
            try:
                cur.execute("PRAGMA table_info(Products)")
                prod_cols = [r["name"] for r in cur.fetchall()]
                if "image_path" not in prod_cols:
                    cur.execute("ALTER TABLE Products ADD COLUMN image_path TEXT")
                if "category" not in prod_cols:
                    cur.execute("ALTER TABLE Products ADD COLUMN category TEXT DEFAULT 'أخرى'")
            except Exception:
                pass

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE,
                    email TEXT,
                    notes TEXT,
                    address TEXT,
                    points REAL DEFAULT 0,
                    last_visit TEXT
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Suppliers table for vendors
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    contact_person TEXT,
                    phone TEXT,
                    address TEXT,
                    category_supplied TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    total REAL NOT NULL,
                    paid REAL NOT NULL,
                    change_amount REAL NOT NULL,
                    qr_data TEXT,
                    user_id INTEGER,
                    customer_id INTEGER,
                    discount REAL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES Users(id),
                    FOREIGN KEY(customer_id) REFERENCES Customers(id)
                )
                """
            )

            # Ensure discount column exists if table was previously created without it
            try:
                cur.execute("PRAGMA table_info(Invoices)")
                inv_cols = [r["name"] for r in cur.fetchall()]
                if "discount" not in inv_cols:
                    cur.execute("ALTER TABLE Invoices ADD COLUMN discount REAL DEFAULT 0")
            except Exception:
                pass

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Invoice_Items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    qty REAL NOT NULL,
                    manual_price REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY(invoice_id) REFERENCES Invoices(id),
                    FOREIGN KEY(product_id) REFERENCES Products(id)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS Stock_Movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    qty REAL NOT NULL,
                    move_type TEXT NOT NULL,
                    reference TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES Products(id)
                )
                """
            )

        self._migrate_schema()
        self._seed_defaults()

    def _migrate_schema(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(Invoices)")
            columns = {row[1] for row in cur.fetchall()}
            if "qr_data" not in columns:
                cur.execute("ALTER TABLE Invoices ADD COLUMN qr_data TEXT")

    def _seed_defaults(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        defaults = [
            ("owner", self._hash_password("1234"), "Owner", now),
            ("admin", self._hash_password("1234"), "Admin", now),
            ("saler", self._hash_password("1234"), "Saler", now),
        ]
        with self._connect() as conn:
            cur = conn.cursor()
            for username, password, role, created_at in defaults:
                cur.execute("SELECT id FROM Users WHERE username = ?", (username,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO Users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                        (username, password, role, created_at),
                    )

            cur.execute("SELECT COUNT(*) as c FROM Categories")
            if cur.fetchone()["c"] == 0:
                default_categories = [
                    ("مشروبات", "جميع أنواع العصائر والمشروبات الغازية والمياه المعدنية", now),
                    ("أطعمة", "المأكولات والمعلبات والوجبات الخفيفة والزيوت والأرز", now),
                    ("مخبوزات", "الخبز الطازج والتوست والكعك والمعجنات والفطائر", now),
                    ("منظفات", "مساحيق الغسيل ومطهرات ومنظفات الأسطح والأواني", now),
                    ("ألبان", "الحليب والأجبان والزبادي ومشتقات الألبان الطازجة", now),
                    ("حلويات", "الشوكولاتة والبسكويت والحلويات والسكاكر", now),
                    ("أخرى", "منتجات متنوعة وأصناف عامة", now),
                ]
                cur.executemany(
                    "INSERT OR IGNORE INTO Categories (name, description, created_at) VALUES (?, ?, ?)",
                    default_categories,
                )

            cur.execute("SELECT COUNT(*) as c FROM Products")
            count = cur.fetchone()["c"]
            if count == 0:
                products = [
                    ("1000001", "Milk 1L", 30, 2.5, (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"), "ألبان", now),
                    ("1000002", "Bread", 50, 1.2, (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"), "مخبوزات", now),
                    ("1000003", "Rice 1kg", 40, 3.0, (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"), "أطعمة", now),
                ]
                cur.executemany(
                    "INSERT INTO Products (barcode, name, stock_qty, default_price, expiry_date, category, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    products,
                )

    @staticmethod
    def _hash_password(password: str) -> str:
        iterations = 120000
        salt = os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    def _verify_password(self, raw_password: str, stored_password: str) -> bool:
        if not stored_password:
            return False

        if stored_password.startswith("pbkdf2_sha256$"):
            try:
                _, iter_txt, salt, expected = stored_password.split("$", 3)
                iterations = int(iter_txt)
                digest = hashlib.pbkdf2_hmac(
                    "sha256",
                    raw_password.encode("utf-8"),
                    salt.encode("utf-8"),
                    iterations,
                ).hex()
                return hmac.compare_digest(digest, expected)
            except Exception:
                return False

        if stored_password.startswith("sha256$"):
            legacy = "sha256$" + hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(legacy, stored_password)

        # توافق رجعي مع كلمات المرور القديمة غير المشفرة
        return hmac.compare_digest(stored_password, raw_password)

    @staticmethod
    def _normalize_role(role: str) -> str:
        role_txt = (role or "").strip().lower()
        mapping = {
            "owner": "Owner",
            "admin": "Admin",
            "saler": "Saler",
        }
        if role_txt not in mapping:
            raise ValueError("الدور غير صالح. القيم المتاحة: owner/admin/saler")
        return mapping[role_txt]

    def validate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, role, password FROM Users WHERE username = ? AND is_active = 1",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None

            if not self._verify_password(password, row["password"]):
                return None

            # ترقية الحسابات القديمة إلى PBKDF2 بعد أول تسجيل دخول ناجح
            if not str(row["password"]).startswith("pbkdf2_sha256$"):
                cur.execute(
                    "UPDATE Users SET password = ? WHERE id = ?",
                    (self._hash_password(password), row["id"]),
                )

            return {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
            }

    def log_login(self, user: Dict[str, Any], status: str = "SUCCESS") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Login_History (user_id, username, role, login_at, status) VALUES (?, ?, ?, ?, ?)",
                (user.get("id"), user.get("username", "UNKNOWN"), user.get("role", "UNKNOWN"), now, status),
            )
            return cur.lastrowid

    def log_failed_login(self, username: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO Login_History (user_id, username, role, login_at, status) VALUES (?, ?, ?, ?, ?)",
                (None, username, "UNKNOWN", now, "FAILED"),
            )

    def log_logout(self, login_history_id: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                "UPDATE Login_History SET logout_at = ? WHERE id = ?",
                (now, login_history_id),
            )

    def find_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Products WHERE barcode = ?", (barcode.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_products(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM Products ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]

    def add_or_update_product(
        self,
        barcode: str,
        name: str,
        qty: float,
        default_price: float,
        expiry_date: Optional[str] = None,
        image_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cat_val = (category or "أخرى").strip() or "أخرى"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, image_path, category FROM Products WHERE barcode = ?", (barcode.strip(),))
            row = cur.fetchone()

            if row:
                product_id = row["id"]
                cur.execute(
                    """
                    UPDATE Products
                    SET name = ?, stock_qty = stock_qty + ?, default_price = ?, expiry_date = COALESCE(?, expiry_date), image_path = COALESCE(?, image_path), category = COALESCE(?, category)
                    WHERE id = ?
                    """,
                    (name, qty, default_price, expiry_date, image_path, cat_val, product_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO Products (barcode, name, stock_qty, default_price, expiry_date, image_path, category, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (barcode.strip(), name, qty, default_price, expiry_date, image_path, cat_val, now),
                )
                product_id = cur.lastrowid

            cur.execute(
                "INSERT INTO Stock_Movements (product_id, qty, move_type, reference, created_at) VALUES (?, ?, ?, ?, ?)",
                (product_id, qty, "IN", "Stock Entry", now),
            )
            return product_id

    def bulk_import_products(self, products_list: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Bulk import products from Excel list with validation.
        Returns: (inserted_count, updated_count)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inserted = 0
        updated = 0

        with self._connect() as conn:
            cur = conn.cursor()
            for p in products_list:
                barcode = str(p.get("barcode") or p.get("Barcode") or p.get("الباركود") or "").strip()
                name = str(p.get("name") or p.get("Product_Name") or p.get("product_name") or p.get("Name") or p.get("اسم المنتج") or "").strip()
                if not barcode or not name:
                    continue

                try:
                    qty = float(p.get("stock_qty") or p.get("Stock_Qty") or p.get("quantity") or p.get("qty") or p.get("الكمية") or 0)
                except (ValueError, TypeError):
                    qty = 0.0

                try:
                    price = float(p.get("default_price") or p.get("price") or p.get("Price") or p.get("السعر") or 0)
                except (ValueError, TypeError):
                    price = 0.0

                expiry_date = p.get("expiry_date") or p.get("Expiry_Date") or p.get("تاريخ الانتهاء")
                if expiry_date:
                    expiry_date = str(expiry_date).strip()[:10]  # format YYYY-MM-DD
                else:
                    expiry_date = None

                image_path = p.get("image_path") or p.get("Image_Path")
                if image_path:
                    image_path = str(image_path).strip()
                else:
                    image_path = None

                category = str(p.get("category") or p.get("Category") or p.get("التصنيف") or "").strip() or "أخرى"

                cur.execute("SELECT id FROM Products WHERE barcode = ?", (barcode,))
                row = cur.fetchone()

                if row:
                    product_id = row["id"]
                    cur.execute(
                        """
                        UPDATE Products
                        SET name = ?, stock_qty = stock_qty + ?, default_price = ?, expiry_date = COALESCE(?, expiry_date), image_path = COALESCE(?, image_path), category = COALESCE(?, category)
                        WHERE id = ?
                        """,
                        (name, qty, price, expiry_date, image_path, category, product_id),
                    )
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO Products (barcode, name, stock_qty, default_price, expiry_date, image_path, category, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (barcode, name, qty, price, expiry_date, image_path, category, now),
                    )
                    product_id = cur.lastrowid
                    inserted += 1

                cur.execute(
                    "INSERT INTO Stock_Movements (product_id, qty, move_type, reference, created_at) VALUES (?, ?, ?, ?, ?)",
                    (product_id, qty, "IN", "Excel Import", now),
                )

        return inserted, updated

    def list_categories(self, search_text: str = "") -> List[Dict[str, Any]]:
        """Return list of categories with product counts and search support."""
        with self._connect() as conn:
            query = """
                SELECT c.id, c.name, COALESCE(c.description, '') AS description, c.created_at,
                       COUNT(p.id) AS product_count
                FROM Categories c
                LEFT JOIN Products p ON TRIM(p.category) = TRIM(c.name)
            """
            params = []
            txt = (search_text or "").strip()
            if txt:
                query += " WHERE c.name LIKE ? OR c.description LIKE ?"
                like = f"%{txt}%"
                params.extend([like, like])
            query += " GROUP BY c.id, c.name, c.description, c.created_at ORDER BY c.name ASC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def create_category(self, name: str, description: str = "") -> int:
        """Create a new product category."""
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم القسم / الفئة مطلوب")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Categories WHERE TRIM(name) = ?", (name,))
            if cur.fetchone():
                raise ValueError(f"الفئة '{name}' مسجلة مسبقاً")
            cur.execute(
                "INSERT INTO Categories (name, description, created_at) VALUES (?, ?, ?)",
                (name, description or None, now),
            )
            return cur.lastrowid

    def update_category(self, category_id: int, name: str, description: str = "") -> None:
        """Update existing category name & description, cascading name changes to Products."""
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم القسم / الفئة مطلوب")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM Categories WHERE id = ?", (category_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("الفئة غير موجودة")
            old_name = row["name"]

            # Check duplicate name
            cur.execute("SELECT id FROM Categories WHERE TRIM(name) = ? AND id != ?", (name, category_id))
            if cur.fetchone():
                raise ValueError(f"اسم الفئة '{name}' مستخدم بالفعل لفئة أخرى")

            cur.execute(
                "UPDATE Categories SET name = ?, description = ? WHERE id = ?",
                (name, description or None, category_id),
            )
            if old_name != name:
                cur.execute("UPDATE Products SET category = ? WHERE category = ?", (name, old_name))

    def delete_category(self, category_id: int) -> None:
        """Delete category and re-assign any linked products to 'أخرى'."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM Categories WHERE id = ?", (category_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("الفئة غير موجودة")
            cat_name = row["name"]
            cur.execute("DELETE FROM Categories WHERE id = ?", (category_id,))
            cur.execute("UPDATE Products SET category = 'أخرى' WHERE category = ?", (cat_name,))

    def get_distinct_categories(self) -> List[str]:
        """Return unified list of all unique categories from Categories table and Products table."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM Categories WHERE name IS NOT NULL AND TRIM(name) != '' ORDER BY name ASC")
            db_cats = [r["name"].strip() for r in cur.fetchall() if r["name"] and r["name"].strip()]

            cur.execute("SELECT DISTINCT category FROM Products WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category ASC")
            prod_cats = [r["category"].strip() for r in cur.fetchall() if r["category"] and r["category"].strip()]

            combined = []
            for c in db_cats + prod_cats:
                if c and c not in combined:
                    combined.append(c)

            defaults = ["مشروبات", "أطعمة", "مخبوزات", "منظفات", "ألبان", "أخرى"]
            for d in defaults:
                if d not in combined:
                    combined.append(d)

            # Keep 'أخرى' at the end of the list
            return sorted(combined, key=lambda x: (x == "أخرى", x))

    def create_customer(self, name: str, phone: str = "", email: str = "", notes: str = "") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Customers (name, phone, email, notes, points, last_visit) VALUES (?, ?, ?, ?, 0, NULL)",
                (name, phone or None, email or None, notes or None),
            )
            return cur.lastrowid

    def list_customers(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM Customers ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]

    def update_customer(self, customer_id: int, name: str, phone: str = "", email: str = "", notes: str = "") -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Customers WHERE id = ?", (customer_id,))
            if not cur.fetchone():
                raise ValueError("العميل غير موجود")
            cur.execute(
                "UPDATE Customers SET name = ?, phone = ?, email = ?, notes = ? WHERE id = ?",
                (name, phone or None, email or None, notes or None, customer_id),
            )

    def delete_customer(self, customer_id: int) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Customers WHERE id = ?", (customer_id,))
            if not cur.fetchone():
                raise ValueError("العميل غير موجود")
            cur.execute("DELETE FROM Customers WHERE id = ?", (customer_id,))

    # Suppliers CRUD
    def list_suppliers(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM Suppliers ORDER BY company_name ASC").fetchall()
            return [dict(r) for r in rows]

    def create_supplier(self, company_name: str, contact_person: str = "", phone: str = "", address: str = "", category_supplied: str = "") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Suppliers (company_name, contact_person, phone, address, category_supplied, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (company_name, contact_person or None, phone or None, address or None, category_supplied or None, now),
            )
            return cur.lastrowid

    def update_supplier(self, supplier_id: int, company_name: str, contact_person: str = "", phone: str = "", address: str = "", category_supplied: str = "") -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Suppliers WHERE id = ?", (supplier_id,))
            if not cur.fetchone():
                raise ValueError("المورد غير موجود")
            cur.execute(
                "UPDATE Suppliers SET company_name = ?, contact_person = ?, phone = ?, address = ?, category_supplied = ? WHERE id = ?",
                (company_name, contact_person or None, phone or None, address or None, category_supplied or None, supplier_id),
            )

    def delete_supplier(self, supplier_id: int) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Suppliers WHERE id = ?", (supplier_id,))
            if not cur.fetchone():
                raise ValueError("المورد غير موجود")
            cur.execute("DELETE FROM Suppliers WHERE id = ?", (supplier_id,))

    def list_users_admin(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, role, is_active, created_at FROM Users ORDER BY id ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def create_user_admin(self, username: str, role: str, password: str) -> int:
        username = (username or "").strip()
        password = (password or "").strip()

        if not username:
            raise ValueError("اسم المستخدم مطلوب")
        if len(username) < 3:
            raise ValueError("اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
        if not re.match(r"^[A-Za-z0-9_.@-]+$", username):
            raise ValueError("اسم المستخدم يحتوي أحرف غير مسموحة")
        if len(password) < 4:
            raise ValueError("كلمة المرور يجب أن تكون 4 أحرف على الأقل")

        normalized_role = self._normalize_role(role)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Users WHERE username = ?", (username,))
            if cur.fetchone():
                raise ValueError("اسم المستخدم موجود مسبقًا")

            cur.execute(
                "INSERT INTO Users (username, password, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
                (username, self._hash_password(password), normalized_role, now),
            )
            return cur.lastrowid

    def update_user_admin(self, user_id: int, username: str, role: str, is_active: bool) -> None:
        username = (username or "").strip()
        if not username:
            raise ValueError("اسم المستخدم مطلوب")

        normalized_role = self._normalize_role(role)

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Users WHERE id = ?", (user_id,))
            if not cur.fetchone():
                raise ValueError("المستخدم غير موجود")

            cur.execute("SELECT id FROM Users WHERE username = ? AND id <> ?", (username, user_id))
            if cur.fetchone():
                raise ValueError("اسم المستخدم مستخدم لحساب آخر")

            cur.execute(
                "UPDATE Users SET username = ?, role = ?, is_active = ? WHERE id = ?",
                (username, normalized_role, 1 if is_active else 0, user_id),
            )

    def reset_user_password_admin(self, user_id: int, new_password: str) -> None:
        new_password = (new_password or "").strip()
        if len(new_password) < 4:
            raise ValueError("كلمة المرور يجب أن تكون 4 أحرف على الأقل")

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Users WHERE id = ?", (user_id,))
            if not cur.fetchone():
                raise ValueError("المستخدم غير موجود")

            cur.execute(
                "UPDATE Users SET password = ? WHERE id = ?",
                (self._hash_password(new_password), user_id),
            )

    def delete_user_admin(self, user_id: int, current_user_id: Optional[int] = None) -> None:
        if current_user_id and int(user_id) == int(current_user_id):
            raise ValueError("لا يمكن حذف الحساب المستخدم حاليًا")

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Users WHERE id = ?", (user_id,))
            if not cur.fetchone():
                raise ValueError("المستخدم غير موجود")

            cur.execute("DELETE FROM Users WHERE id = ?", (user_id,))

    def create_invoice(
        self,
        items: List[Dict[str, Any]],
        paid: float,
        user_id: int,
        customer_id: Optional[int] = None,
        discount: float = 0.0,
        total: Optional[float] = None,
    ) -> Tuple[int, str, float, float]:
        if not items:
            raise ValueError("Invoice has no items")

        computed_subtotal = sum(i["qty"] * i["manual_price"] for i in items)
        if total is None:
            total = max(0.0, computed_subtotal - discount)
        total = round(total, 2)
        discount = round(discount, 2)

        change_amount = round(paid - total, 2)
        if change_amount < -0.001:
            raise ValueError("Paid amount is less than total")

        now = datetime.now()
        invoice_no = f"INV-{now.strftime('%Y%m%d-%H%M%S')}"
        now_txt = now.strftime("%Y-%m-%d %H:%M:%S")
        qr_data = self._build_invoice_qr_payload(invoice_no, now_txt, items, total, paid, change_amount)

        with self._connect() as conn:
            cur = conn.cursor()

            for item in items:
                cur.execute("SELECT stock_qty FROM Products WHERE id = ?", (item["product_id"],))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Product not found: {item['product_id']}")
                if row["stock_qty"] < item["qty"]:
                    raise ValueError("Insufficient stock for one or more products")

            cur.execute(
                """
                INSERT INTO Invoices (invoice_no, created_at, total, paid, change_amount, qr_data, user_id, customer_id, discount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice_no, now_txt, total, paid, change_amount, qr_data, user_id, customer_id, discount),
            )
            invoice_id = cur.lastrowid

            for item in items:
                subtotal = item["qty"] * item["manual_price"]
                cur.execute(
                    """
                    INSERT INTO Invoice_Items (invoice_id, product_id, qty, manual_price, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (invoice_id, item["product_id"], item["qty"], item["manual_price"], subtotal),
                )

                cur.execute(
                    "UPDATE Products SET stock_qty = stock_qty - ? WHERE id = ?",
                    (item["qty"], item["product_id"]),
                )

                cur.execute(
                    "INSERT INTO Stock_Movements (product_id, qty, move_type, reference, created_at) VALUES (?, ?, ?, ?, ?)",
                    (item["product_id"], item["qty"], "OUT", invoice_no, now_txt),
                )

            if customer_id:
                cur.execute(
                    "UPDATE Customers SET last_visit = ? WHERE id = ?",
                    (now_txt, customer_id),
                )

        return invoice_id, invoice_no, total, change_amount

    def _build_invoice_qr_payload(
        self,
        invoice_no: str,
        created_at: str,
        items: List[Dict[str, Any]],
        total: float,
        paid: float,
        change_amount: float,
    ) -> str:
        payload = {
            "invoice_no": invoice_no,
            "created_at": created_at,
            "total": round(total, 2),
            "paid": round(paid, 2),
            "change": round(change_amount, 2),
            "items": [
                {
                    "product_id": i["product_id"],
                    "barcode": i.get("barcode"),
                    "name": i.get("name"),
                    "qty": i["qty"],
                    "price": i["manual_price"],
                }
                for i in items
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def list_invoices_admin(self, search_text: str = "") -> List[Dict[str, Any]]:
        with self._connect() as conn:
            query = """
                SELECT i.id, i.invoice_no, i.created_at, i.total, i.qr_data, u.username AS cashier_name
                FROM Invoices i
                LEFT JOIN Users u ON u.id = i.user_id
            """
            params: List[Any] = []

            txt = (search_text or "").strip()
            if txt:
                query += """
                    WHERE i.invoice_no LIKE ?
                    OR i.created_at LIKE ?
                    OR COALESCE(u.username, '') LIKE ?
                """
                like = f"%{txt}%"
                params.extend([like, like, like])

            query += " ORDER BY i.id DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def get_invoice_details(self, invoice_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT i.*, u.username, c.name AS customer_name
                FROM Invoices i
                LEFT JOIN Users u ON u.id = i.user_id
                LEFT JOIN Customers c ON c.id = i.customer_id
                WHERE i.id = ?
                """,
                (invoice_id,),
            )
            header = cur.fetchone()
            if not header:
                raise ValueError("Invoice not found")

            cur.execute(
                """
                SELECT ii.*, p.name, p.barcode
                FROM Invoice_Items ii
                JOIN Products p ON p.id = ii.product_id
                WHERE ii.invoice_id = ?
                """,
                (invoice_id,),
            )
            items = [dict(r) for r in cur.fetchall()]
            result = dict(header)
            result["items"] = items
            subtotal = sum(float(it.get("subtotal", 0) or 0) for it in items)
            result["subtotal"] = subtotal
            if "discount" not in result or result["discount"] is None:
                result["discount"] = max(0.0, subtotal - float(result.get("total", 0) or 0))
            return result

    def get_dashboard_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            cur = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")

            cur.execute("SELECT COUNT(*) AS c FROM Products")
            products_count = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM Customers")
            customers_count = cur.fetchone()["c"]

            cur.execute("SELECT COALESCE(SUM(total), 0) AS s FROM Invoices WHERE DATE(created_at) = ?", (today,))
            sales_today = cur.fetchone()["s"]

            cur.execute("SELECT COUNT(*) AS c FROM Invoices WHERE DATE(created_at) = ?", (today,))
            invoices_today = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM Products WHERE stock_qty > 0")
            available_stock_count = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM Categories")
            categories_count = cur.fetchone()["c"]

            return {
                "products_count": products_count,
                "customers_count": customers_count,
                "sales_today": sales_today,
                "invoices_today": invoices_today,
                "available_stock_count": available_stock_count,
                "categories_count": categories_count,
            }

    def get_login_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM Login_History ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_expiry_report(self, days: int = 30) -> List[Dict[str, Any]]:
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *,
                    CASE
                        WHEN expiry_date IS NULL THEN 'NO_DATE'
                        WHEN DATE(expiry_date) < DATE('now') THEN 'EXPIRED'
                        WHEN DATE(expiry_date) <= DATE(?) THEN 'NEAR_EXPIRY'
                        ELSE 'OK'
                    END AS expiry_status
                FROM Products
                WHERE expiry_date IS NOT NULL
                ORDER BY DATE(expiry_date) ASC
                """,
                (end_date.strftime("%Y-%m-%d"),),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_sales_report(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT i.invoice_no, i.created_at, i.total, i.paid, i.change_amount, u.username
                FROM Invoices i
                LEFT JOIN Users u ON u.id = i.user_id
                WHERE DATE(i.created_at) BETWEEN DATE(?) AND DATE(?)
                ORDER BY i.created_at DESC
                """,
                (start_date, end_date),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_available_products_count(self) -> int:
        """Return count of distinct Products with stock_qty > 0 (available product lines)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as c FROM Products WHERE stock_qty > 0")
            row = cur.fetchone()
            return int(row["c"]) if row else 0
