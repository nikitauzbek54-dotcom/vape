import asyncpg
import json
from typing import Optional


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        await self._create_tables()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    tg_id BIGINT PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    stock INTEGER DEFAULT 0,
                    strength TEXT,
                    flavor TEXT,
                    category TEXT NOT NULL,
                    photos JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS cart (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    UNIQUE(user_id, product_id)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name TEXT,
                    phone TEXT,
                    delivery_type TEXT,
                    metro_station TEXT,
                    comment TEXT,
                    status TEXT DEFAULT 'new',
                    total INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER,
                    name TEXT,
                    price INTEGER,
                    quantity INTEGER
                );
                CREATE TABLE IF NOT EXISTS admins (
                    tg_id BIGINT PRIMARY KEY,
                    role TEXT DEFAULT 'manager'
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    # ===== USERS =====
    async def get_user(self, tg_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE tg_id=$1", tg_id)

    async def create_user(self, tg_id: int, name: str, phone: Optional[str] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (tg_id, name, phone) VALUES ($1, $2, $3) "
                "ON CONFLICT (tg_id) DO UPDATE SET name=$2, phone=COALESCE($3, users.phone)",
                tg_id, name, phone
            )

    async def update_user_phone(self, tg_id: int, phone: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET phone=$1 WHERE tg_id=$2", phone, tg_id)

    async def get_all_users(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT tg_id FROM users")

    # ===== PRODUCTS =====
    async def add_product(self, name, description, price, stock, strength, flavor, category, photos):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                INSERT INTO products (name, description, price, stock, strength, flavor, category, photos)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
            """, name, description, price, stock, strength, flavor, category, json.dumps(photos))

    async def get_products_by_category(self, category: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM products WHERE category=$1 ORDER BY id DESC", category
            )

    async def get_product(self, product_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE id=$1", product_id)

    async def get_all_products(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products ORDER BY id DESC")

    async def update_product(self, product_id: int, **fields):
        if not fields:
            return
        keys = list(fields.keys())
        values = list(fields.values())
        set_clause = ", ".join(f"{k}=${i+1}" for i, k in enumerate(keys))
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE products SET {set_clause} WHERE id=${len(keys)+1}",
                *values, product_id
            )

    async def delete_product(self, product_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM products WHERE id=$1", product_id)
            await conn.execute("DELETE FROM cart WHERE product_id=$1", product_id)

    async def decrease_stock(self, product_id: int, qty: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET stock = GREATEST(stock - $1, 0) WHERE id=$2",
                qty, product_id
            )

    # ===== CART =====
    async def add_to_cart(self, user_id: int, product_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cart (user_id, product_id, quantity) VALUES ($1, $2, 1)
                ON CONFLICT (user_id, product_id) DO UPDATE SET quantity = cart.quantity + 1
            """, user_id, product_id)

    async def get_cart(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT c.id as cart_id, c.quantity, p.*
                FROM cart c JOIN products p ON c.product_id = p.id
                WHERE c.user_id=$1 ORDER BY c.id
            """, user_id)

    async def cart_count(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COALESCE(SUM(quantity), 0) FROM cart WHERE user_id=$1", user_id
            )

    async def update_cart_qty(self, cart_id: int, delta: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE cart SET quantity = quantity + $1 WHERE id=$2 AND quantity + $1 > 0",
                delta, cart_id
            )
            await conn.execute("DELETE FROM cart WHERE id=$1 AND quantity <= 0", cart_id)

    async def remove_from_cart(self, cart_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM cart WHERE id=$1", cart_id)

    async def clear_cart(self, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM cart WHERE user_id=$1", user_id)

    # ===== ORDERS =====
    async def create_order(self, user_id, name, phone, delivery_type, metro_station, comment, total):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                INSERT INTO orders (user_id, name, phone, delivery_type, metro_station, comment, total)
                VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
            """, user_id, name, phone, delivery_type, metro_station, comment, total)

    async def add_order_item(self, order_id, product_id, name, price, quantity):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO order_items (order_id, product_id, name, price, quantity)
                VALUES ($1, $2, $3, $4, $5)
            """, order_id, product_id, name, price, quantity)

    async def get_order(self, order_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)

    async def get_order_items(self, order_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM order_items WHERE order_id=$1", order_id)

    async def get_user_orders(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM orders WHERE user_id=$1 ORDER BY id DESC LIMIT 10", user_id
            )

    async def get_orders_by_status(self, status: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM orders WHERE status=$1 ORDER BY id DESC", status
            )

    async def get_all_orders(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM orders ORDER BY id DESC LIMIT 50")

    async def update_order_status(self, order_id: int, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE orders SET status=$1 WHERE id=$2", status, order_id)

    # ===== ADMINS =====
    async def is_admin(self, tg_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM admins WHERE tg_id=$1", tg_id) is not None

    async def add_admin(self, tg_id: int, role: str = "manager"):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO admins (tg_id, role) VALUES ($1, $2) "
                "ON CONFLICT (tg_id) DO UPDATE SET role=$2", tg_id, role
            )

    async def remove_admin(self, tg_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM admins WHERE tg_id=$1 AND role != 'owner'", tg_id)

    async def get_all_admins(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM admins ORDER BY role DESC")

    # ===== SETTINGS =====
    async def get_setting(self, key: str, default: str = ""):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM settings WHERE key=$1", key)
            return row["value"] if row else default

    async def set_setting(self, key: str, value: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value=$2
            """, key, value)