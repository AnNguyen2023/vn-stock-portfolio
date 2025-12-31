import models

def reset_system():
    print("Đang tiến hành xóa toàn bộ dữ liệu...")
    # Xóa tất cả các bảng
    models.Base.metadata.drop_all(bind=models.engine)
    print("Đã xóa xong. Đang tạo lại cấu trúc bảng mới...")
    # Tạo lại bảng
    models.Base.metadata.create_all(bind=models.engine)
    print("Hệ thống đã được đưa về trạng thái xuất xưởng!")

if __name__ == "__main__":
    confirm = input("CẢNH BÁO: Hành động này sẽ xóa sạch mọi giao dịch. Nhấn 'y' để xác nhận: ")
    if confirm.lower() == 'y':
        reset_system()