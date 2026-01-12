# Invest Journal - Backend API 📈

Hệ thống Backend quản lý nhật ký đầu tư chứng khoán cá nhân, được xây dựng bằng **FastAPI**, hỗ trợ theo dõi danh mục, thống kê lãi lỗ và cập nhật dữ liệu thị trường chứng khoán Việt Nam (VN-HSE/HNX/UPCOM).

## 🚀 Tính Năng Chính

*   **Quản Lý Danh Mục (Portfolio):**
    *   Theo dõi tài sản ròng (NAV), số dư tiền mặt.
    *   Ghi lại dòng tiền nạp/rút.
    *   Quản lý danh sách cổ phiếu đang nắm giữ (Holding).
*   **Nhật Ký Giao Dịch (Trading Journal):**
    *   Ghi lại chi tiết lệnh Mua/Bán.
    *   Tự động tính thuế (0.1%) và phí giao dịch (0.15%).
    *   Ghi chú tâm lý/lý do giao dịch.
*   **Theo Dõi Hiệu Suất:**
    *   Thống kê lãi lỗ đã chốt (Realized Profit).
    *   Snapshot NAV hàng ngày để vẽ biểu đồ tăng trưởng tài sản.
*   **Dữ Liệu Thị Trường (Market Data):**
    *   Tích hợp thư viện **vnstock3** để lấy dữ liệu giá real-time và lịch sử.
    *   Cơ chế **Redis Caching** giúp giảm tải request ra ngoài và tăng tốc độ phản hồi.
    *   Hệ thống **Background Workers** tự động đồng bộ dữ liệu lịch sử cho các mã trong danh mục.

## 🛠 Tech Stack

*   **Core:** Python 3.12, FastAPI
*   **Database:** PostgreSQL (SQLAlchemy ORM)
*   **Cache:** Redis
*   **Data Source:** vnstock3 (nguồn VCI/SSI)
*   **Deployment:** Docker

## 📂 Cấu Trúc Dự Án

```
backend/
├── core/               # Cấu hình DB, Redis, Config
├── routers/            # Các API Endpoint (Portfolio, Trading, Market...)
├── services/           # Logic nghiệp vụ (Sync data, tính toán)
├── models.py           # Định nghĩa Database Schema
├── crawler.py          # Module giao tiếp với vnstock3
├── main.py             # Entry point của ứng dụng
├── Dockerfile          # Cấu hình build Docker image
└── requirements.txt    # Các thư viện phụ thuộc
```

## ⚙️ Cài Đặt & Chạy (Local)

### 1. Yêu cầu
*   Python 3.10 trở lên.
*   PostgreSQL & Redis đang chạy (hoặc dùng Docker).

### 2. Thiết lập môi trường
Tạo file `.env` từ file mẫu (nếu có) hoặc cấu hình các biến sau:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/vn_stock
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

### 3. Cài đặt thư viện
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Chạy ứng dụng
```bash
uvicorn main:app --reload
```
Server sẽ chạy tại: `http://localhost:8000`
API Docs (Swagger UI): `http://localhost:8000/docs`

## 🐳 Chạy bằng Docker

```bash
# Build image
docker build -t invest-journal-backend .

# Run container
docker run -p 8000:8000 --env-file .env invest-journal-backend
```

## 📝 API Endpoints Chính

| Method | Endpoint | Mô tả |
| :--- | :--- | :--- |
| **GET** | `/portfolio` | Lấy tổng quan tài sản & danh mục hiện tại |
| **POST** | `/trading/buy` | Thực hiện lệnh Mua cổ phiếu |
| **POST** | `/trading/sell` | Thực hiện lệnh Bán cổ phiếu |
| **GET** | `/market/historical` | Lấy dữ liệu lịch sử giá (có Cache) |
| **POST** | `/market/sync-portfolio-history` | Kích hoạt worker đồng bộ dữ liệu |

## 🤝 Contributing
Dự án được phát triển với tinh thần "Code cho vui, lãi là chính". Mọi đóng góp đều được hoan nghênh!

1.  Fork dự án
2.  Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit thay đổi (`git commit -m 'Add some AmazingFeature'`)
4.  Push lên branch (`git push origin feature/AmazingFeature`)
5.  Tạo Pull Request
