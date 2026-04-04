# core/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def check_overdue_job():
    """Hàm này sẽ gọi cái lệnh check_overdue mà bạn vừa tạo"""
    try:
        print("Đang chạy kiểm tra sách trễ hạn tự động...")
        # Gọi lệnh tự động y như lúc bạn gõ trên Terminal
        call_command('check_overdue') 
    except Exception as e:
        logger.error(f"Lỗi khi chạy lệnh check_overdue: {e}")

def start():
    scheduler = BackgroundScheduler()
    # Đặt lịch chạy: 8h00 sáng mỗi ngày
    scheduler.add_job(check_overdue_job, 'cron', hour=8, minute=0)
    # Nếu muốn test ngay, bạn có thể đổi thành: scheduler.add_job(check_overdue_job, 'interval', minutes=1)
    
    
    scheduler.start()
    print("⏳ Hệ thống đặt lịch tự động đã khởi động (Chạy lúc 8h sáng mỗi ngày).")