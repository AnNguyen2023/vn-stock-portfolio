
import os
import sys

# Thêm thư mục hiện tại vào path để import được models, core...
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import engine, Base
import models
from services.market_service import sync_securities_task

def init_db_and_sync():
    print("--- [INIT] Đang khởi tạo bảng và đồng bộ dữ liệu ban đầu ---")
    
    # 1. Tạo bảng nếu chưa có (trong trường hợp chưa chạy main.py)
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Đã kiểm tra/tạo các bảng database")
    except Exception as e:
        print(f"❌ Lỗi tạo bảng: {e}")
        return

    # 2. Chạy sync securities
    sync_securities_task()
    print("--- [HOÀN TẤT] ---")

if __name__ == "__main__":
    init_db_and_sync()
