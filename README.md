# Lume Travel

> Website du lịch tương tác với phong cách biên tập tối giản, giúp người dùng khám phá điểm đến, xem hành trình gợi ý và gửi yêu cầu tư vấn.

## Giới thiệu

Lume Travel là một travel storefront chạy local, kết hợp giao diện responsive với một server Python nhỏ gọn. Dự án có các tương tác dành cho trải nghiệm khám phá như slider ảnh, bộ lọc hành trình, modal chi tiết điểm đến, bản đồ 3D, chế độ sáng/tối và âm thanh nền ambient.

## Tính năng

- Khám phá và lọc các hành trình theo biển, núi, văn hóa hoặc sống chậm.
- Xem thông tin chi tiết điểm đến và mở vị trí trên Google Earth.
- Gửi form đặt tư vấn, đăng ký newsletter và thêm đánh giá.
- Đăng nhập và đăng ký tài khoản với Neon PostgreSQL hoặc SQLite fallback.
- Chatbot hỗ trợ tư vấn điểm đến qua API backend, có local fallback khi chưa cấu hình API key.
- Chế độ sáng/tối được lưu trong trình duyệt.
- Âm thanh nền tùy chọn bằng Web Audio API, không tự phát khi chưa có tương tác.
- Danh sách điểm đến có thể tự đồng bộ từ API mỗi giờ.

## Công nghệ

- HTML, CSS và JavaScript thuần
- Python 3.10+
- SQLite
- Web Audio API
- Gemini hoặc OpenAI API tùy cấu hình
- Neon PostgreSQL với Psycopg 3

## Chạy local

Yêu cầu Python 3.10+.

```powershell
py server.py
```

Sau đó mở http://localhost:3000

Hoặc chạy `start.bat` bằng double-click.

## Deploy trên Render

Tạo một Web Service từ repository này. Render có thể tự nhận cấu hình trong `render.yaml`; nếu nhập thủ công, dùng:

- Build command: `pip install -r requirements.txt`
- Start command: `python server.py`

Server tự đọc biến môi trường `PORT` do Render cấp và lắng nghe trên `0.0.0.0`.

## Kết nối Neon

Cài dependencies:

```powershell
pip install -r requirements.txt
```

Đặt connection string Neon vào biến môi trường `DATABASE_URL` rồi chạy server. Backend sẽ tự tạo bảng và seed các điểm đến lần đầu khởi động. Nếu không có `DATABASE_URL`, ứng dụng tự dùng `lume.db` để chạy local.

```powershell
$env:DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
py server.py
```

Schema PostgreSQL nằm trong `schema.sql`, gồm users, sessions, destinations, bookings, reviews, newsletter_subscribers và chat_messages.

## Tài khoản demo

- Email: `demo@lume.travel`
- Mật khẩu: `lume2025`

## Bảo mật tài khoản

- Mật khẩu được băm bằng PBKDF2-HMAC-SHA256, không lưu mật khẩu gốc.
- Session được lưu dưới dạng hash trong database; token chỉ nằm trong cookie `HttpOnly`.
- Cookie dùng `SameSite=Lax` và tự bật `Secure` khi chạy HTTPS trên Render.
- Đăng nhập sai quá 5 lần trong 15 phút từ cùng địa chỉ sẽ bị giới hạn tạm thời.
- Đặt `FORCE_SECURE_COOKIES=1` nếu triển khai sau proxy HTTPS nhưng không dùng URL Render mặc định.

## API chính

- `POST /api/login`: đăng nhập
- `POST /api/register`: tạo tài khoản
- `GET /api/destinations`: lấy các địa điểm đã phát hành
- `POST /api/chat`: proxy tới Gemini/OpenAI nếu đã cấu hình API key

## Cấu hình chatbot AI

Đặt một trong các biến môi trường trước khi chạy server để dùng AI bên ngoài:

```powershell
$env:GEMINI_API_KEY = "your-key"
py server.py
```

Gemini có thể chọn model bằng `GEMINI_MODEL` (mặc định `gemini-2.0-flash`). Có thể dùng OpenAI bằng `OPENAI_API_KEY` và tùy chọn `OPENAI_MODEL`.

Để dùng GitHub Models (thay cho Copilot API trực tiếp), đặt token có quyền gọi model:

```powershell
$env:AI_PROVIDER = "github"
$env:GITHUB_TOKEN = "your-github-token"
$env:GITHUB_MODEL = "openai/gpt-4o-mini"
py server.py
```

Trên Render, thêm các biến này trong Environment. Gói Copilot cá nhân không cung cấp API key để server gọi trực tiếp.

Nếu chưa có API key, trợ lý vẫn hoạt động với các câu trả lời local cho Kyoto, Bali, Ninh Bình, Phú Yên, chuyến đi 3 ngày và tư vấn tiết kiệm.

Database `lume.db` được tạo và cập nhật tự động trong cùng folder.
