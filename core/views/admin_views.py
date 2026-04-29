from django.shortcuts import render

def admin_dashboard_view(request):
    # Tạm thời dùng dữ liệu giả để test giao diện trước. 
    # Sau này bạn có thể query từ database thay cho mảng này.
    borrow_stats = [12, 19, 3, 5, 2, 3, 20, 33, 12, 4, 15, 22] 
    
    return render(request, 'admin/dashboard.html', {'borrow_stats': borrow_stats})