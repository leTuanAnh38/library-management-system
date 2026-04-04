# file: core/views/staff_views.py
from django.db.models import Case, When, Value, IntegerField
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum
from django.db import transaction as db_transaction
from ..models import Category, Publisher, Review
from ..forms import CategoryForm, PublisherForm
from django.core.paginator import Paginator
# Chú ý import lại các model và form từ thư mục gốc của app core
from core.models import Book, BorrowTransaction, Penalty, User, Notification
from core.forms import BookForm
from django.db.models import Avg, Count, OuterRef, Subquery

# Hàm kiểm tra quyền Staff
def is_staff(user):
    return user.is_authenticated and user.role in ['STAFF', 'ADMIN']

# ==========================================
# 1. QUẢN LÝ KHO SÁCH (CRUD)
# ==========================================
@user_passes_test(is_staff, login_url='login')
def staff_dashboard(request):
    # Chỉ giữ lại phần thống kê cho Dashboard
    overdue_transactions = BorrowTransaction.objects.filter(
        status='OVERDUE'
    ).select_related('user', 'book').order_by('due_date') 

    total_library_books = Book.objects.aggregate(total=Sum('initial_quantity'))['total'] or 0
    current_available_books = Book.objects.aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'core/staff/dashboard.html', {
        'overdue_transactions': overdue_transactions,
        'total_library_books': total_library_books,
        'current_available_books': current_available_books
    })

# THÊM HÀM MỚI NÀY VÀO DƯỚI HÀM TRÊN
@user_passes_test(is_staff, login_url='login')
def staff_book_list(request):
    query = request.GET.get('search_staff', '')
    books = Book.objects.all() 

    if query:
        books = books.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(location__icontains=query) 
        )

    books = books.order_by('-created_at')
    
    # THÊM PHẦN NÀY: Phân trang (10 cuốn / 1 lần tải)
    paginator = Paginator(books, 10) 
    page_obj = paginator.get_page(1) # Lần đầu tiên chỉ lấy trang 1

    return render(request, 'core/staff/book_list.html', {
        'books': page_obj, # Truyền page_obj thay cho toàn bộ books
        'query': query
    })

@user_passes_test(is_staff)
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
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
        form = BookForm(request.POST,request.FILES, instance=book)
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

# --- QUẢN LÝ DANH MỤC ---
def staff_category_list(request):
    categories = Category.objects.all().order_by('name')
    # Sửa từ 'staff/category_list.html' thành 'core/staff/category_list.html'
    return render(request, 'core/staff/category_list.html', {'categories': categories})

def staff_category_form(request, pk=None):
    instance = get_object_or_404(Category, pk=pk) if pk else None
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật danh mục thành công!")
            return redirect('staff_category_list')
    else:
        form = CategoryForm(instance=instance)
    
    title = "Chỉnh sửa danh mục" if pk else "Thêm danh mục mới"
    # Sửa từ 'staff/category_form.html' thành 'core/staff/category_form.html'
    return render(request, 'core/staff/category_form.html', {'form': form, 'title': title})

# --- QUẢN LÝ NHÀ XUẤT BẢN ---
def staff_publisher_list(request):
    publishers = Publisher.objects.all().order_by('name')
    # Sửa từ 'staff/publisher_list.html' thành 'core/staff/publisher_list.html'
    return render(request, 'core/staff/publisher_list.html', {'publishers': publishers})

def staff_publisher_form(request, pk=None):
    instance = get_object_or_404(Publisher, pk=pk) if pk else None
    if request.method == 'POST':
        form = PublisherForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật nhà xuất bản thành công!")
            return redirect('staff_publisher_list')
    else:
        form = PublisherForm(instance=instance)
    
    title = "Chỉnh sửa nhà xuất bản" if pk else "Thêm nhà xuất bản mới"
    # Sửa từ 'staff/category_form.html' thành 'core/staff/category_form.html'
    return render(request, 'core/staff/category_form.html', {'form': form, 'title': title})

# Quản lý mượn trả sách
@user_passes_test(is_staff, login_url='login')
def staff_borrow_management(request):
    query = request.GET.get('q', '').strip()
    
    # Sắp xếp mức độ ưu tiên cho Thủ thư
    transactions = BorrowTransaction.objects.select_related('user', 'book').annotate(
        status_priority=Case(
            When(status='PENDING', then=Value(1)),   # Chờ duyệt (nóng nhất)
            When(status='OVERDUE', then=Value(2)),   # Quá hạn (nóng thứ hai)
            When(status='BORROWED', then=Value(3)),  # Đang mượn (bình thường)
            When(status='RETURNED', then=Value(4)),  # Đã trả (đã xong)
            default=Value(5),
            output_field=IntegerField(),
        )
    )
    
    if query:
        transactions = transactions.filter(
            Q(user__msv__icontains=query) |          
            Q(user__username__icontains=query) |     
            Q(user__first_name__icontains=query) |   
            Q(user__last_name__icontains=query)      
        ).distinct()
        
    # Sắp xếp theo ưu tiên trạng thái trước, sau đó mới đến ngày tạo
    transactions = transactions.order_by('status_priority', '-created_at')
    
    # ==========================================
    # ---> THÊM PHẦN PHÂN TRANG VÀO ĐÂY <---
    # ==========================================
    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(1) # Lần đầu chỉ render trang 1
    
    return render(request, 'core/staff/borrow_management.html', {
        'transactions': page_obj, # TRUYỀN PAGE_OBJ VÀO ĐÂY
        'query': query
    })

@user_passes_test(is_staff, login_url='login')
def staff_approve_borrow(request, transaction_id):
    # ---> ĐÃ SỬA: Bỏ điều kiện is_paid=False để Thủ thư có thể tìm và duyệt được cả sách Free
    borrow_record = get_object_or_404(BorrowTransaction, id=transaction_id, status='PENDING')
    
    try:
        with db_transaction.atomic():
            borrow_record.status = 'BORROWED'
            borrow_record.is_paid = True  # Đảm bảo đơn nào duyệt xong cũng là hợp lệ
            borrow_record.borrow_date = timezone.now().date()
            borrow_record.due_date = timezone.now().date() + timedelta(days=14)
            borrow_record.save()
            
            # ---> ĐÃ SỬA: Phân loại sách để hiển thị tin nhắn phù hợp
            is_premium = borrow_record.book.price and borrow_record.book.price > 0
            
            if is_premium:
                msg_noti = f"Thủ thư đã duyệt tiền và giao cuốn sách có phí '{borrow_record.book.title}' cho bạn. Hạn trả là {borrow_record.due_date.strftime('%d/%m/%Y')}."
                msg_success = f"Đã xác nhận thu tiền và giao sách có phí cho sinh viên {borrow_record.user.msv}."
            else:
                msg_noti = f"Thủ thư đã duyệt và giao cuốn sách '{borrow_record.book.title}' cho bạn. Hạn trả là {borrow_record.due_date.strftime('%d/%m/%Y')}."
                msg_success = f"Đã xác nhận duyệt giao sách cho sinh viên {borrow_record.user.msv}."

            Notification.objects.create(
                user=borrow_record.user,
                message=msg_noti,
                type='SYSTEM',
                status='UNREAD'
            )
            
        messages.success(request, msg_success)
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

@user_passes_test(is_staff, login_url='login')
def staff_review_management(request):
    # Lấy thông tin bài đánh giá gần nhất của mỗi cuốn sách
    latest_review = Review.objects.filter(book=OuterRef('pk')).order_by('-created_at')

    # Đã sửa 'review_set' thành 'reviews' theo đúng cấu trúc Database của bạn
    books = Book.objects.annotate(
        review_count=Count('reviews'), 
        avg_rating=Avg('reviews__rating'), 
        latest_reviewer=Subquery(latest_review.values('user__username')[:1]),
        latest_review_date=Subquery(latest_review.values('created_at')[:1])
    ).filter(review_count__gt=0).order_by('-avg_rating', '-review_count')

    return render(request, 'core/staff/review_management.html', {'books': books})