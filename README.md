# Lume Travel

> Website du lịch tương tác với phong cách biên tập tối giản, giúp người dùng khám phá điểm đến, xem hành trình gợi ý và gửi yêu cầu tư vấn.

## Giới thiệu

Lume Travel là một travel storefront chạy local, kết hợp giao diện responsive với một server Python nhỏ gọn. Dự án có các tương tác dành cho trải nghiệm khám phá như slider ảnh, bộ lọc hành trình, modal chi tiết điểm đến, bản đồ 3D, chế độ sáng/tối và âm thanh nền ambient.

## Tính năng

- Khám phá và lọc các hành trình theo biển, núi, văn hóa hoặc sống chậm.
- Xem thông tin chi tiết điểm đến và mở vị trí trên Google Earth.
- Gửi form đặt tư vấn, đăng ký newsletter và thêm đánh giá.
- Đăng nhập và đăng ký tài khoản với SQLite.
- Chatbot hỗ trợ tư vấn điểm đến qua API backend.
- Chế độ sáng/tối được lưu trong trình duyệt.
- Âm thanh nền tùy chọn bằng Web Audio API, không tự phát khi chưa có tương tác.
- Danh sách điểm đến có thể tự đồng bộ từ API mỗi giờ.

## Công nghệ

- HTML, CSS và JavaScript thuần
- Python 3.10+
- SQLite
- Web Audio API
- Gemini hoặc OpenAI API tùy cấu hình

## Chạy local

Yêu cầu Python 3.10+.

```powershell
py server.py
```

Sau đó mở http://localhost:3000

Hoặc chạy `start.bat` bằng double-click.

## Tài khoản demo

- Email: `demo@lume.travel`
- Mật khẩu: `lume2025`

## API chính

- `POST /api/login`: đăng nhập
- `POST /api/register`: tạo tài khoản
- `GET /api/destinations`: lấy các địa điểm đã phát hành
- `POST /api/chat`: proxy tới Gemini/OpenAI nếu đã cấu hình API key

## Cấu hình chatbot AI

Đặt một trong các biến môi trường trước khi chạy server:

```powershell
$env:GEMINI_API_KEY = "your-key"
py server.py
```

Hoặc dùng `OPENAI_API_KEY` và tùy chọn `OPENAI_MODEL`.

Database `lume.db` được tạo và cập nhật tự động trong cùng folder.
