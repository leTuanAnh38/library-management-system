from .models import BorrowTransaction
from django.db.models.functions import ExtractMonth
from django.db.models import Count

def dashboard_stats(request):
    # Lấy dữ liệu mượn sách theo tháng
    stats = BorrowTransaction.objects.annotate(month=ExtractMonth('borrow_date')) \
        .values('month').annotate(count=Count('id')).order_by('month')
    
    # Khởi tạo mảng 12 tháng với giá trị 0
    data = [0] * 12
    for s in stats:
        if s['month']:
            data[s['month'] - 1] = s['count']
            
    return {'borrow_stats': data}