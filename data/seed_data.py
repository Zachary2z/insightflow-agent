import argparse
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

try:
    from data.seed_realistic_scenarios import (
        drop_realistic_tables,
        seed_realistic_scenarios,
        table_counts as realistic_table_counts,
    )
except ModuleNotFoundError:
    from seed_realistic_scenarios import (
        drop_realistic_tables,
        seed_realistic_scenarios,
        table_counts as realistic_table_counts,
    )


DEFAULT_DB_PATH = Path(__file__).resolve().with_name("ecommerce.db")
RANDOM_SEED = 42
USER_COUNT = 120
ORDER_COUNT = 540


CATEGORIES = [
    "Cameras",
    "Audio",
    "Computers",
    "Home",
    "Sports",
    "Books",
]

PRODUCTS_BY_CATEGORY = {
    "Cameras": [
        ("Mirrorless Camera A", 5299.00),
        ("Action Camera B", 1899.00),
        ("Camera Lens C", 2499.00),
        ("Tripod D", 499.00),
        ("Camera Bag E", 329.00),
        ("Memory Card F", 129.00),
    ],
    "Audio": [
        ("Noise Cancelling Headphones", 1599.00),
        ("Wireless Earbuds", 899.00),
        ("Bluetooth Speaker", 699.00),
        ("Studio Microphone", 1199.00),
        ("Soundbar", 2199.00),
        ("USB Audio Interface", 799.00),
    ],
    "Computers": [
        ("Laptop Pro 14", 8999.00),
        ("Mechanical Keyboard", 699.00),
        ("Gaming Mouse", 399.00),
        ("USB-C Hub", 299.00),
        ("4K Monitor", 2599.00),
        ("External SSD", 1099.00),
    ],
    "Home": [
        ("Air Purifier", 1299.00),
        ("Robot Vacuum", 2399.00),
        ("Coffee Maker", 699.00),
        ("Desk Lamp", 199.00),
        ("Smart Plug", 99.00),
        ("Electric Kettle", 259.00),
    ],
    "Sports": [
        ("Yoga Mat", 159.00),
        ("Running Shoes", 699.00),
        ("Fitness Tracker", 799.00),
        ("Dumbbell Set", 399.00),
        ("Cycling Helmet", 299.00),
        ("Tennis Racket", 599.00),
    ],
    "Books": [
        ("Data Analysis Handbook", 89.00),
        ("Business Strategy Guide", 109.00),
        ("Python SQL Cookbook", 139.00),
        ("Marketing Playbook", 99.00),
        ("Operations Management", 119.00),
        ("Product Analytics", 129.00),
    ],
}

CITIES = [
    "Shanghai",
    "Beijing",
    "Shenzhen",
    "Guangzhou",
    "Hangzhou",
    "Chengdu",
    "Nanjing",
    "Wuhan",
]

FIRST_NAMES = [
    "Alex",
    "Blake",
    "Casey",
    "Drew",
    "Elliot",
    "Harper",
    "Jamie",
    "Jordan",
    "Morgan",
    "Quinn",
    "Riley",
    "Taylor",
]

LAST_NAMES = [
    "Chen",
    "Li",
    "Wang",
    "Zhang",
    "Liu",
    "Yang",
    "Huang",
    "Zhao",
    "Wu",
    "Zhou",
]


def create_schema(conn: sqlite3.Connection) -> None:
    drop_realistic_tables(conn)
    conn.executescript(
        """
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            category_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('paid', 'cancelled', 'refunded')),
            total_amount REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )


def seed_users(conn: sqlite3.Connection, rng: random.Random, reference_date: date) -> None:
    rows = []
    for user_id in range(1, USER_COUNT + 1):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        created_at = reference_date - timedelta(days=rng.randint(30, 720))
        rows.append(
            (
                user_id,
                name,
                rng.choice(CITIES),
                rng.choice(["female", "male", "unknown"]),
                rng.randint(18, 65),
                created_at.isoformat(),
            )
        )

    conn.executemany(
        """
        INSERT INTO users (id, name, city, gender, age, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def seed_categories_and_products(
    conn: sqlite3.Connection, rng: random.Random, reference_date: date
) -> list[tuple[int, float]]:
    for category_id, category_name in enumerate(CATEGORIES, start=1):
        conn.execute(
            "INSERT INTO categories (id, category_name) VALUES (?, ?)",
            (category_id, category_name),
        )

    products = []
    product_id = 1
    for category_id, category_name in enumerate(CATEGORIES, start=1):
        for product_name, price in PRODUCTS_BY_CATEGORY[category_name]:
            created_at = reference_date - timedelta(days=rng.randint(180, 900))
            conn.execute(
                """
                INSERT INTO products (id, product_name, category_id, price, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (product_id, product_name, category_id, price, created_at.isoformat()),
            )
            products.append((product_id, price))
            product_id += 1

    return products


def order_status_for_index(index: int) -> str:
    if index % 15 == 0:
        return "refunded"
    if index % 10 == 0:
        return "cancelled"
    return "paid"


def seed_orders(
    conn: sqlite3.Connection,
    rng: random.Random,
    products: list[tuple[int, float]],
    reference_date: date,
) -> None:
    order_item_id = 1
    for order_id in range(1, ORDER_COUNT + 1):
        if order_id == 1:
            order_date = reference_date - timedelta(days=330)
        elif order_id == 2:
            order_date = reference_date
        else:
            order_date = reference_date - timedelta(days=rng.randint(0, 330))

        items = []
        total_amount = 0.0
        for product_id, base_price in rng.sample(products, rng.randint(1, 4)):
            quantity = rng.randint(1, 4)
            unit_price = round(base_price * rng.uniform(0.85, 1.15), 2)
            total_amount += quantity * unit_price
            items.append((order_item_id, order_id, product_id, quantity, unit_price))
            order_item_id += 1

        conn.execute(
            """
            INSERT INTO orders (id, user_id, order_date, status, total_amount)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id,
                rng.randint(1, USER_COUNT),
                order_date.isoformat(),
                order_status_for_index(order_id),
                round(total_amount, 2),
            ),
        )
        conn.executemany(
            """
            INSERT INTO order_items (id, order_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?, ?)
            """,
            items,
        )


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = ["users", "orders", "order_items", "products", "categories"]
    counts = {
        table_name: conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in tables
    }
    counts.update(realistic_table_counts(conn))
    return counts


def seed_database(db_path: str | Path = DEFAULT_DB_PATH) -> dict:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(RANDOM_SEED)
    reference_date = date.today()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        create_schema(conn)
        seed_users(conn, rng, reference_date)
        products = seed_categories_and_products(conn, rng, reference_date)
        seed_orders(conn, rng, products, reference_date)
        seed_realistic_scenarios(conn)
        conn.commit()
        counts = table_counts(conn)

    return {
        "success": True,
        "db_path": str(db_path),
        "table_counts": counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the InsightFlow ecommerce SQLite database.")
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Output SQLite database path. Defaults to data/ecommerce.db.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = seed_database(args.db_path)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
