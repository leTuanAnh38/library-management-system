# file: core/views/staff_views.py
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.db import transaction as db_transaction

# Chú ý import lại các model và form từ thư mục gốc của app core
from core.models import Book, BorrowTransaction, Penalty, User, Notification
from core.forms import BookForm

# Hàm kiểm tra quyền Staff
def is_staff(user):
    return user.is_authenticated and user.role in ['STAFF', 'ADMIN']

# ==========================================
# 1. QUẢN LÝ KHO SÁCH (CRUD)
# ==========================================

@user_passes_test(is_staff, login_url='login')
def staff_dashboard(request):
    query = request.GET.get('search_staff')
    books = Book.objects.all() 

    if query:
        books = books.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(location__icontains=query) 
        )

    books = books.order_by('-created_at')
    return render(request, 'core/staff/dashboard.html', {'books': books})

@user_passes_test(is_staff)
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Thêm sách '{form.cleaned_data.get('title')}' thành công!")
            return redirect('staff_dashboard')
    else:
        form = BookForm()
    
    return render(request, 'core/staff/book_form.html', {
        'form': form, 
        'title': 'Thêm sách mới'
    })

@user_passes_test(is_staff)
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật thông tin sách thành công!")
            return redirect('staff_dashboard')
    else:
        form = BookForm(instance=book)
    return render(request, 'core/staff/book_form.html', {'form': form, 'title': 'Chỉnh sửa sách'})

@user_passes_test(is_staff)
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book.delete()
    messages.success(request, "Đã xóa sách khỏi hệ thống!")
    return redirect('staff_dashboard')


# ==========================================
# 2. QUẢN LÝ NGHIỆP VỤ MƯỢN TRẢ SÁCH
# ==========================================

@user_passes_test(is_staff, login_url='login')
def staff_borrow_management(request):
    query = request.GET.get('q', '').strip()
    transactions = BorrowTransaction.objects.all().select_related('user', 'book')
    
    if query:
        transactions = transactions.filter(
            Q(user__msv__icontains=query) |          
            Q(user__username__icontains=query) |     
            Q(user__first_name__icontains=query) |   
            Q(user__last_name__icontains=query)      
        ).distinct()
        
    transactions = transactions.order_by('-created_at')
    return render(request, 'core/staff/borrow_management.html', {
        'transactions': transactions,
        'query': query
    })

@user_passes_test(is_staff, login_url='login')
def staff_approve_borrow(request, transaction_id):
    borrow_record = get_object_or_404(BorrowTransaction, id=transaction_id, status='PENDING', is_paid=False)
    
    try:
        with db_transaction.atomic():
            borrow_record.status = 'BORROWED'
            borrow_record.is_paid = True
            borrow_record.borrow_date = timezone.now().date()
            borrow_record.due_date = timezone.now().date() + timedelta(days=14)
            borrow_record.save()
            
            Notification.objects.create(
                user=borrow_record.user,
                message=f"Thủ thư đã duyệt tiền và giao cuốn VIP '{borrow_record.book.title}' cho bạn. Hạn trả là {borrow_record.due_date.strftime('%d/%m/%Y')}.",
                type='SYSTEM',
                status='UNREAD'
            )
            
        messages.success(request, f"Đã xác nhận thu tiền và giao sách VIP cho sinh viên {borrow_record.user.msv}.")
    except Exception as e:
        messages.error(request, f"Lỗi hệ thống: {str(e)}")
        
    return redirect('staff_borrow_management')

@user_passes_test(is_staff, login_url='login')
def staff_confirm_return(request, transaction_id):
    borrow_record = get_object_or_404(BorrowTransaction, id=transaction_id, status__in=['BORROWED', 'PENDING'])
    user = borrow_record.user
    
    try:
        with db_transaction.atomic():
            today = timezone.now().date()
            borrow_record.status = 'RETURNED'
            borrow_record.return_date = today
            borrow_record.save()
            
            if today > borrow_record.due_date:
                user.points = max(0, user.points - 5)
                days_late = (today - borrow_record.due_date).days
                fine_amount = days_late * 5000
                
                Penalty.objects.create(
                    user=user,
                    borrow_transaction=borrow_record,
                    amount=fine_amount,
                    reason=f"Trả sách trễ {days_late} ngày",
                    status='UNPAID'
                )

                Notification.objects.create(
                    user=user,
                    message=f"CẢNH BÁO: Thủ thư đã thu hồi cuốn '{borrow_record.book.title}'. Bạn trả trễ {days_late} ngày, hệ thống phạt {fine_amount} VNĐ và TRỪ 5 ĐIỂM tích lũy.",
                    type='SYSTEM',
                    status='UNREAD'
                )
            else:
                user.points += 10 
                Notification.objects.create(
                    user=user,
                    message=f"Tuyệt vời! Thủ thư đã xác nhận thu hồi cuốn '{borrow_record.book.title}' thành công. Bạn được cộng 10 điểm thưởng vì trả sách đúng hạn.",
                    type='SYSTEM',
                    status='UNREAD'
                )
            
            user.save() 
            
            book = borrow_record.book
            book.quantity += 1
            book.save()
            
            messages.success(request, f"Đã xác nhận thu hồi sách từ Sinh viên {user.msv} (Tên: {user.get_full_name() or user.username}).")
    except Exception as e:
        messages.error(request, f"Lỗi hệ thống: {str(e)}")
        
    return redirect('staff_borrow_management')


# ==========================================
# 3. QUẢN LÝ TIỀN PHẠT & NGƯỜI DÙNG
# ==========================================

@user_passes_test(is_staff, login_url='login')
def staff_penalty_management(request):
    penalties = Penalty.objects.exclude(status='PAID').order_by('-created_at')
    return render(request, 'core/staff/penalty_management.html', {'penalties': penalties})

@user_passes_test(is_staff, login_url='login')
def staff_confirm_penalty(request, penalty_id):
    penalty = get_object_or_404(Penalty, id=penalty_id, status__in=['UNPAID', 'PROCESSING'])
    penalty.status = 'PAID'
    penalty.save()
    
    Notification.objects.create(
        user=penalty.user,
        message=f"Thủ thư đã xác nhận thu khoản tiền phạt {penalty.amount} VNĐ của bạn. Cảm ơn bạn đã hoàn tất nghĩa vụ!",
        type='SYSTEM',
        status='UNREAD'
    )
    
    messages.success(request, f"Đã xác nhận thu tiền phạt thành công từ sinh viên {penalty.user.msv}.")
    return redirect('staff_penalty_management')

@user_passes_test(is_staff, login_url='login')
def staff_user_management(request):
    readers = User.objects.filter(
        is_staff=False, 
        is_superuser=False
    ).exclude(role__in=['STAFF', 'ADMIN']).order_by('username')
    
    query = request.GET.get('q')
    if query:
        readers = readers.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(msv__icontains=query)
        )
        
    return render(request, 'core/staff/user_management.html', {'readers': readers})

@user_passes_test(is_staff, login_url='login')
def staff_user_detail(request, user_id):
    reader = get_object_or_404(User, id=user_id)
    borrow_history = BorrowTransaction.objects.filter(user=reader).order_by('-created_at')
    penalties = Penalty.objects.filter(user=reader).order_by('-created_at')
    
    return render(request, 'core/staff/user_detail.html', {
        'reader': reader,
        'borrow_history': borrow_history,
        'penalties': penalties
    })