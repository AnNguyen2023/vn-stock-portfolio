# 📈 INVEST JOURNAL - Quản lý Danh mục Chứng khoán Việt Nam

Ứng dụng Web cá nhân giúp theo dõi tài sản, nhật ký giao dịch và đối soát hiệu suất đầu tư thực tế tại thị trường chứng khoán Việt Nam.

## 🌟 Tính năng cốt lõi
- **Quản lý Danh mục (Live Portfolio):** Theo dõi mã CP, khối lượng, giá vốn bình quân gia quyền.
- **Giá thị trường Real-time:** Tự động cập nhật giá từ Datafeed của VPS mỗi 30 giây.
- **Nhật ký đầu tư (Audit Log):** Timeline chi tiết mọi hành động: Nạp tiền, Rút tiền, Khớp lệnh Mua/Bán, Lãi qua đêm.
- **Theo dõi Hiệu suất (Performance):** Tính toán lãi/lỗ theo các mốc 1 ngày, 1 tháng, 1 năm và YTD (đầu năm đến nay).
- **Privacy Mode:** Nút ẩn/hiện thông tin nhạy cảm (Timeline & Lịch sử lệnh) khi sử dụng nơi công cộng.
- **Tra cứu lịch sử:** Tính tổng lãi lỗ thực nhận dựa trên khoảng thời gian tùy chọn.

## 🛠 Công nghệ sử dụng
- **Frontend:** Next.js 15+, Tailwind CSS 4 (Theme: Purple & Emerald).
- **Backend:** Python FastAPI.
- **Database:** PostgreSQL (SQLAlchemy ORM).
- **Data Source:** VPS API Datafeed.

## 📂 Cấu trúc thư mục
```text
vn-stock-portfolio/
├── backend/            # Python FastAPI, Logic tính toán lãi lỗ, Crawler
│   ├── main.py         # API Endpoints & Logic nghiệp vụ
│   ├── models.py       # Cấu trúc Database (PostgreSQL)
│   ├── crawler.py      # Module lấy giá từ VPS
│   └── schemas.py      # Định nghĩa kiểu dữ liệu (Pydantic)
├── frontend/           # Next.js App
│   ├── app/            # Giao diện chính (Page & Layout)
│   └── lib/            # Cấu hình API (Axios)
└── README.md

---
🚀 **[Demo Documentation Kit](file:///e:/vn-stock-portfolio/docs/README_DEMO.md)** - Chuẩn bị cho buổi demo sản phẩm.
```