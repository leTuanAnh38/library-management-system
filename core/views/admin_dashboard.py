from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.db.models import Count
from core.models import Book, BorrowTransaction

@method_decorator(staff_member_required, name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'admin/custom_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Thống kê 4 ô màu trên cùng (Dữ liệu thực tế từ DB)
        context['total_books'] = Book.objects.count()
        context['available_books'] = Book.objects.filter(status='AVAILABLE').count()
        context['pending_borrows'] = BorrowTransaction.objects.filter(status='PENDING').count()
        context['overdue_borrows'] = BorrowTransaction.objects.filter(status='OVERDUE').count()

        # 2. Danh sách mượn quá hạn cho bảng bên dưới
        context['overdue_list'] = BorrowTransaction.objects.filter(
            status='OVERDUE'
        ).select_related('user', 'book').order_by('due_date')[:10]
        
        return context

@staff_member_required
def admin_chart_api(request):
    # Dữ liệu thực tế từ Database
    status_data = [
        BorrowTransaction.objects.filter(status='BORROWED').count(),
        BorrowTransaction.objects.filter(status='PENDING').count(),
        BorrowTransaction.objects.filter(status='RETURNED').count(),
        BorrowTransaction.objects.filter(status='OVERDUE').count(),
    ]
    
    top_books = Book.objects.annotate(num_borrows=Count('borrow_records')).order_by('-num_borrows')[:5]
    
    return JsonResponse({
        "status_labels": ['Đang mượn', 'Chờ duyệt', 'Đã trả', 'Quá hạn'],
        "status_data": status_data,
        "top_labels": [b.title[:20] for b in top_books],
        "top_data": [b.num_borrows for b in top_books],
    })