from .models import BorrowTransaction
from django.db.models.functions import ExtractMonth
from django.db.models import Count
from .models import Wishlist, Category # Thêm Category vào đây

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

def global_counts(request):
    # Lấy toàn bộ danh mục sách từ CSDL
    categories = Category.objects.all()
    
    # Đếm số sách yêu thích (giữ nguyên code cũ của bạn)
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        
    return {
        'wishlist_count': wishlist_count,
        'categories': categories  # Trả về biến categories để dùng ở mọi nơi
    }