from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

ROOT = Path(__file__).parent
DATABASE = ROOT / "lume.db"
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL") or os.getenv("POSTGRES_URL")
PORT = int(os.getenv("PORT", "3000"))
PASSWORD_ITERATIONS = 600_000
DEMO_EMAIL = "demo@lume.travel"
DEMO_PASSWORD = "lume2025"
DESTINATION_CATALOG = [
    ("Ninh Bình", "núi", "Việt Nam · 3 ngày", "từ 3.900.000đ", "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=900&q=85"),
    ("Phú Yên", "biển", "Việt Nam · 4 ngày", "từ 4.600.000đ", "https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?auto=format&fit=crop&w=900&q=85"),
    ("Kyoto", "văn hóa", "Nhật Bản · 5 ngày", "từ 18.900.000đ", "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=900&q=85"),
    ("Sa Pa", "chậm", "Việt Nam · 3 ngày", "từ 3.500.000đ", "https://images.unsplash.com/photo-1557750255-c76072a7aad1?auto=format&fit=crop&w=900&q=85"),
    ("Bali", "biển", "Indonesia · 6 ngày", "từ 14.500.000đ", "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=900&q=85"),
    ("Tà Xùa", "núi", "Việt Nam · 2 ngày", "từ 2.800.000đ", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=85"),
    ("Mộc Châu", "chậm", "Việt Nam · 3 ngày", "từ 3.200.000đ", "https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=900&q=85"),
    ("Luang Prabang", "văn hóa", "Lào · 4 ngày", "từ 8.900.000đ", "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?auto=format&fit=crop&w=900&q=85"),
    ("Palawan", "biển", "Philippines · 5 ngày", "từ 16.900.000đ", "https://images.unsplash.com/photo-1516690561799-46d8f74f9abf?auto=format&fit=crop&w=900&q=85"),
    ("Marrakech", "văn hóa", "Morocco · 5 ngày", "từ 21.500.000đ", "https://images.unsplash.com/photo-1548013146-72479768bdaa?auto=format&fit=crop&w=900&q=85"),
    ("Tasmania", "núi", "Australia · 7 ngày", "từ 32.900.000đ", "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85"),
    ("Madeira", "biển", "Bồ Đào Nha · 6 ngày", "từ 26.500.000đ", "https://images.unsplash.com/photo-1526392060635-9d6019884377?auto=format&fit=crop&w=900&q=85"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PASSWORD_ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def is_postgres() -> bool:
    return bool(DATABASE_URL)


def get_connection():
    if is_postgres():
        if psycopg is None:
            raise RuntimeError("Đã cấu hình DATABASE_URL nhưng chưa cài psycopg. Chạy: pip install -r requirements.txt")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def execute(connection, query: str, parameters: tuple = ()):
    if is_postgres():
        query = query.replace("?", "%s")
    return connection.execute(query, parameters)


def initialize_database() -> None:
    if is_postgres():
        initialize_postgres_database()
        return
    with get_connection() as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                destination TEXT NOT NULL,
                travelers TEXT NOT NULL,
                travel_month TEXT NOT NULL,
                email TEXT NOT NULL,
                note TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                subscribed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        demo = execute(connection, "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
        if demo is None:
            execute(connection,
                "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (DEMO_EMAIL, "Lume explorer", hash_password(DEMO_PASSWORD), utc_now()),
            )
        execute(connection,
            """
            CREATE TABLE IF NOT EXISTS destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                place TEXT NOT NULL,
                price TEXT NOT NULL,
                image TEXT NOT NULL,
                available_at TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        if execute(connection, "SELECT COUNT(*) FROM destinations").fetchone()[0] == 0:
            start_time = datetime.now(timezone.utc)
            connection.executemany(
                "INSERT INTO destinations (name, type, place, price, image, available_at, published) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(name, kind, place, price, image, (start_time + timedelta(hours=max(0, index - 5))).isoformat(), int(index < 6)) for index, (name, kind, place, price, image) in enumerate(DESTINATION_CATALOG)],
            )


def initialize_postgres_database() -> None:
    schema_path = ROOT / "schema.sql"
    with get_connection() as connection:
        connection.execute(schema_path.read_text(encoding="utf-8"))
        connection.execute(
            """
            INSERT INTO users (email, name, password_hash, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            (DEMO_EMAIL, "Lume explorer", hash_password(DEMO_PASSWORD), utc_now()),
        )
        count = connection.execute("SELECT COUNT(*) AS count FROM destinations").fetchone()["count"]
        if count == 0:
            start_time = datetime.now(timezone.utc)
            connection.executemany(
                "INSERT INTO destinations (name, type, place, price, image, available_at, published) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [(name, kind, place, price, image, start_time + timedelta(hours=max(0, index - 5)), index < 6) for index, (name, kind, place, price, image) in enumerate(DESTINATION_CATALOG)],
            )


def get_destinations() -> list[dict]:
    now = utc_now()
    with get_connection() as connection:
        execute(connection, "UPDATE destinations SET published = 1 WHERE published = 0 AND available_at <= ?", (now,))
        rows = execute(connection, "SELECT name, type, place, price, image FROM destinations WHERE published = 1 ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def create_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    execute(connection,
        "INSERT INTO sessions (user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, token_hash, utc_now(), (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()),
    )
    return token


def ask_ai(message: str, history: list[dict]) -> str:
    provider = os.getenv("AI_PROVIDER", "").lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if provider == "openai" and openai_key:
        selected_provider = "openai"
    elif provider == "gemini" and gemini_key:
        selected_provider = "gemini"
    elif gemini_key:
        selected_provider = "gemini"
    elif openai_key:
        selected_provider = "openai"
    else:
        return local_assistant_reply(message)

    system_prompt = "Bạn là Lume AI, một trợ lý du lịch thân thiện. Trả lời bằng tiếng Việt, thực tế và ngắn gọn. Khi tư vấn lịch trình, hãy hỏi thêm ngân sách, số ngày hoặc sở thích nếu cần. Không bịa thông tin chắc chắn về giá, visa hoặc thời tiết hiện tại."
    if selected_provider == "gemini":
        contents = [{"role": "user", "parts": [{"text": system_prompt}]}]
        contents.extend({"role": "model" if item.get("role") == "assistant" else "user", "parts": [{"text": item.get("content", "")}]} for item in history[-8:])
        contents.append({"role": "user", "parts": [{"text": message}]})
        payload = json.dumps({"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}}).encode()
        request = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())
        return result["candidates"][0]["content"]["parts"][0]["text"]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": item.get("role", "user"), "content": item.get("content", "")} for item in history[-8:])
    messages.append({"role": "user", "content": message})
    payload = json.dumps({"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "messages": messages, "temperature": 0.7, "max_tokens": 500}).encode()
    request = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode())
    return result["choices"][0]["message"]["content"]


def local_assistant_reply(message: str) -> str:
    """Keep the assistant useful when no external AI key is configured."""
    question = message.lower()
    destinations = {
        "kyoto": "Kyoto hợp nhất vào tháng 3–4 hoặc 10–11. Bạn có thể đi chậm qua Arashiyama, Kiyomizu-dera và dành một buổi cho trà đạo.",
        "bali": "Bali phù hợp từ tháng 4–10. Lịch trình cân bằng có thể gồm Ubud, ruộng bậc thang và một buổi ngắm hoàng hôn ở Uluwatu.",
        "ninh bình": "Ninh Bình hợp cho chuyến 3 ngày 2 đêm: đi thuyền Tràng An buổi sớm, đạp xe qua Tam Cốc và ngắm hoàng hôn từ Hang Múa.",
        "phú yên": "Phú Yên đẹp nhất khi đi chậm: đón bình minh ở Mũi Điện, ghé Gành Đá Đĩa và ăn hải sản bên đầm Ô Loan.",
    }
    for destination, reply in destinations.items():
        if destination in question:
            return reply + " Bạn muốn mình gợi ý theo ngân sách hay số ngày?"
    if any(word in question for word in ("tiết kiệm", "ngân sách", "rẻ")):
        return "Để đi tiết kiệm, hãy chọn chuyến 2–3 ngày, đặt phương tiện sớm và ưu tiên điểm đến trong nước như Ninh Bình, Phú Yên hoặc Sa Pa. Bạn dự kiến ngân sách bao nhiêu?"
    if any(word in question for word in ("3 ngày", "ba ngày", "3 hôm")):
        return "Với 3 ngày, Ninh Bình là lựa chọn dễ đi và đủ thư giãn. Lume gợi ý 1 ngày Tràng An, 1 ngày Tam Cốc – Hang Múa và 1 ngày dành cho cafe, đạp xe quanh làng quê."
    return "Mình có thể tư vấn Ninh Bình, Phú Yên, Kyoto, Bali hoặc các chuyến đi tiết kiệm. Bạn muốn đi trong bao nhiêu ngày và ngân sách khoảng bao nhiêu?"


class LumeHandler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length > 10_000:
            raise ValueError("Payload quá lớn.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        try:
            data = self.read_json()
            if route == "/api/chat":
                message = str(data.get("message", "")).strip()
                if not message or len(message) > 2_000:
                    return self.send_json(400, {"message": "Câu hỏi không hợp lệ hoặc quá dài."})
                try:
                    reply = ask_ai(message, data.get("history", []))
                    return self.send_json(200, {"reply": reply})
                except (RuntimeError, KeyError, IndexError):
                    return self.send_json(503, {"message": "Trợ lý AI chưa được cấu hình. Hãy thêm GEMINI_API_KEY hoặc OPENAI_API_KEY trên server."})
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                    return self.send_json(502, {"message": "Không kết nối được tới dịch vụ AI lúc này."})
            if route == "/api/bookings":
                destination = str(data.get("destination", "")).strip()
                travelers = str(data.get("travelers", "")).strip()
                travel_month = str(data.get("date", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                note = str(data.get("note", "")).strip()[:1_000]
                if not destination or not travelers or not travel_month or "@" not in email:
                    return self.send_json(400, {"message": "Vui lòng điền đủ thông tin đặt tư vấn."})
                with get_connection() as connection:
                    execute(connection, "INSERT INTO bookings (destination, travelers, travel_month, email, note) VALUES (?, ?, ?, ?, ?)", (destination, travelers, travel_month, email, note))
                return self.send_json(201, {"message": "Đã nhận yêu cầu tư vấn."})
            if route == "/api/reviews":
                name = str(data.get("name", "")).strip()[:100]
                comment = str(data.get("comment", "")).strip()[:1_000]
                rating = int(data.get("rating", 0))
                if not name or not comment or rating not in range(1, 6):
                    return self.send_json(400, {"message": "Đánh giá chưa hợp lệ."})
                with get_connection() as connection:
                    execute(connection, "INSERT INTO reviews (name, rating, comment) VALUES (?, ?, ?)", (name, rating, comment))
                return self.send_json(201, {"message": "Đánh giá đã được lưu."})
            if route == "/api/newsletter":
                email = str(data.get("email", "")).strip().lower()
                if "@" not in email:
                    return self.send_json(400, {"message": "Email chưa hợp lệ."})
                with get_connection() as connection:
                    try:
                        execute(connection, "INSERT INTO newsletter_subscribers (email) VALUES (?)", (email,))
                    except (sqlite3.IntegrityError, psycopg.errors.UniqueViolation if psycopg else sqlite3.IntegrityError):
                        pass
                return self.send_json(201, {"message": "Đăng ký nhận tin thành công."})
            email = str(data.get("email", "")).strip().lower()
            password = str(data.get("password", ""))
            if not email or not password:
                return self.send_json(400, {"message": "Email và mật khẩu là bắt buộc."})

            with get_connection() as connection:
                if route == "/api/register":
                    name = str(data.get("name", "")).strip()
                    if not name:
                        return self.send_json(400, {"message": "Vui lòng nhập tên của bạn."})
                    try:
                        insert_query = "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)"
                        if is_postgres():
                            insert_query += " RETURNING id"
                        cursor = execute(connection, insert_query, (email, name, hash_password(password), utc_now()))
                    except sqlite3.IntegrityError:
                        return self.send_json(409, {"message": "Email này đã được đăng ký."})
                    user_id = cursor.fetchone()["id"] if is_postgres() else cursor.lastrowid
                    token = create_session(connection, user_id)
                    return self.send_json(201, {"message": "Tạo tài khoản thành công.", "token": token, "user": {"email": email, "name": name}})

                if route == "/api/login":
                    user = execute(connection, "SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                    if user is None or not verify_password(password, user["password_hash"]):
                        return self.send_json(401, {"message": "Email hoặc mật khẩu chưa đúng."})
                    execute(connection, "UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now(), user["id"]))
                    token = create_session(connection, user["id"])
                    return self.send_json(200, {"message": "Đăng nhập thành công.", "token": token, "user": {"email": user["email"], "name": user["name"]}})

            return self.send_json(404, {"message": "Không tìm thấy đường dẫn."})
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"message": "Dữ liệu gửi lên không hợp lệ."})
        except Exception:
            self.send_json(500, {"message": "Máy chủ đang gặp sự cố."})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/destinations":
            return self.send_json(200, {"destinations": get_destinations(), "next_update": "Tự động thêm 1 địa danh mỗi giờ"})
        if route in ("/", "/index.html"):
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_json(404, {"message": "Không tìm thấy đường dẫn."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), LumeHandler)
    print(f"Lume Travel đang chạy trên port {PORT}")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    server.serve_forever()
