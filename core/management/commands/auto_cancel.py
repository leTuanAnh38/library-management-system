# core/management/commands/auto_cancel.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from django.db import transaction as db_transaction
from core.models import BorrowTransaction, Notification

class Command(BaseCommand):
    help = 'Tự động hủy các đơn mượn sách quá giờ hẹn lấy'

    def handle(self, *args, **kwargs):
        now = datetime.now()
        today_date = now.date()
        current_hour = now.hour

        # Lấy các đơn CHỜ DUYỆT (Loại trừ các đơn sinh viên đang yêu cầu trả)
        pending_mmuon = BorrowTransaction.objects.filter(status='PENDING').exclude(reason='YÊU CẦU TRẢ')
        count = 0

        for t in pending_mmuon:
            is_expired = False
            if t.pickup_date:
                # Nếu ngày hẹn đã qua
                if t.pickup_date < today_date:
                    is_expired = True
                # Nếu là hôm nay nhưng quá giờ
                elif t.pickup_date == today_date:
                    if t.pickup_shift == 'SANG' and current_hour >= 12:
                        is_expired = True
                    elif t.pickup_shift == 'CHIEU' and current_hour >= 18:
                        is_expired = True

            if is_expired:
                with db_transaction.atomic():
                    t.status = 'CANCELLED'
                    t.reason = 'Hủy tự động do quá hạn thời gian đến nhận sách'
                    t.save()
                    
                    # Hoàn lại số lượng sách vào kho
                    t.book.quantity += 1
                    t.book.save()
                    
                    # Gửi thông báo cho sinh viên
                    shift_text = "Sáng" if t.pickup_shift == 'SANG' else "Chiều"
                    cancel_msg = f"HỦY TỰ ĐỘNG: Đơn mượn sách '{t.book.title}' bị hủy do bạn không đến nhận đúng hẹn (Ca {shift_text} ngày {t.pickup_date.strftime('%d/%m/%Y')})."
                    Notification.objects.create(user=t.user, message=cancel_msg, type='SYSTEM', status='UNREAD')
                    count += 1
                    
        self.stdout.write(self.style.SUCCESS(f'[{now.strftime("%H:%M:%S")}] Đã quét và tự động hủy {count} đơn quá giờ.'))