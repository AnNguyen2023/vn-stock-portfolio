from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

# Import hệ thống dữ liệu (Models)
import models

# Import các "phòng ban" chuyên trách (Routers)
from routers import trading, portfolio, logs, market

app = FastAPI(
    title="Invest Journal API",
    description="Hệ thống quản lý danh mục chứng khoán chuyên nghiệp của đại ca Zon",
    version="1.2.0"
)

# =========================================================================================
# 1. KHỞI TẠO CẤU TRÚC HỆ THỐNG
# =========================================================================================

# Tự động tạo bảng vào Postgres nếu chưa có
models.Base.metadata.create_all(bind=models.engine)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================================
# 2. BỘ GÁC CỔNG BẮT LỖI TOÀN CỤC (GLOBAL ERROR HANDLERS)
# =========================================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Dữ liệu nhập không hợp lệ", "detail": exc.errors()[0]['msg']},
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Lỗi cơ sở dữ liệu", "detail": str(exc)},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Lỗi hệ thống ngoài dự kiến", "detail": str(exc)},
    )

# =========================================================================================
# 3. KẾT NỐI CÁC PHÒNG BAN (REGISTERING ROUTERS)
# =========================================================================================

app.include_router(trading.router)    # Đã chứa: Mua, Bán, Undo
app.include_router(portfolio.router)  # Đã chứa: Portfolio, Performance, Nav-history, Reset
app.include_router(logs.router, tags=["Logs"])# Đã chứa: Logs, Update-note, History-summary
app.include_router(market.router)     # Đã chứa: Historical (Chart)

# =========================================================================================
# 4. ĐIỂM KIỂM TRA HỆ THỐNG
# =========================================================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Đại đô thị Invest Journal đã thông suốt. Chào đại ca Zon!",
        "version": "1.2.0"
    }