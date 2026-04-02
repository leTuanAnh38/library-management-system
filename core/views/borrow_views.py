# file: core/views/borrow_views.py

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# ---> THÊM DÒNG NÀY ĐỂ SỬ DỤNG HÀM CASE, WHEN CỦA DJANGO ORM <---
from django.db.models import Case, When, Value, IntegerField

# Import models từ app core
from core.models import Book, BorrowTransaction, Notification

# ==========================================
# 1. NGHIỆP VỤ MƯỢN SÁCH
# ==========================================

@login_required(login_url='login')
def borrow_book(request, book_id):
    user = request.user
    
    # 1. KIỂM TRA PHÍ PHẠT
    if user.total_fine > 0:
        messages.error(request, f"Bạn hiện đang có khoản phí phạt chưa thanh toán ({user.total_fine} VNĐ). Vui lòng hoàn tất nghĩa vụ để tiếp tục mượn sách!")
        return redirect('profile')

    # 2. KIỂM TRA HỒ SƠ
    if not getattr(user, 'msv', None) or not getattr(user, 'lop', None):
        messages.warning(request, "Vui lòng cập nhật MSSV và Lớp trong hồ sơ cá nhân trước khi thực hiện mượn sách!")
        return redirect('profile')

    # 3. Lấy thông tin sách
    book = get_object_or_404(Book, id=book_id)
    
    if book.quantity <= 0:
        messages.error(request, f"Sách '{book.title}' đã hết trong kho!")
        return redirect(request.META.get('HTTP_REFERER', 'book_list'))
        
    # XỬ LÝ SÁCH VIP (CÓ PHÍ) VÀ PHƯƠNG THỨC THANH TOÁN
    is_premium = book.price and book.price > 0

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'FREE')
    else:
        if is_premium:
            messages.warning(request, "Vui lòng chọn phương thức thanh toán tại trang Danh mục để mượn sách VIP!")
            return redirect('premium_books')
        payment_method = 'FREE'

    han_tra = timezone.now().date() + timedelta(days=14)
    
    # ---> ĐÃ SỬA: Mặc định tất cả các yêu cầu mượn đều là PENDING (Chờ duyệt)
    status = 'PENDING' 
    is_paid = False if is_premium else True

    try:
        with db_transaction.atomic():
            transaction = BorrowTransaction.objects.create(
                user=user,
                book=book,
                due_date=han_tra, 
                status=status,
                payment_method=payment_method, 
                is_paid=is_paid                
            )

            # ---> ĐÃ SỬA: Cập nhật thông báo cho sinh viên biết là phải chờ duyệt
            if is_premium:
                payment_display = dict(BorrowTransaction.PAYMENT_CHOICES).get(payment_method, payment_method)
                msg = f"Đã gửi yêu cầu mượn sách có phí '{book.title}'. Vui lòng thanh toán {book.price:,.0f} VNĐ qua hình thức [{payment_display}] để Thủ thư duyệt!"
            else:
                msg = f"Đã gửi yêu cầu mượn cuốn '{book.title}'. Vui lòng chờ Thủ thư duyệt hoặc đến quầy để nhận sách."

            # Tạo thông báo hệ thống
            Notification.objects.create(
                user=user,
                message=msg,
                type='SYSTEM',
                status='UNREAD'
            )

            book.quantity -= 1
            book.save()

        messages.success(request, msg)
    except Exception as e:
        messages.error(request, f"Đã có lỗi xảy ra trong quá trình mượn sách: {str(e)}")
    
    return redirect(request.META.get('HTTP_REFERER', 'book_list'))
# ==========================================
# 2. LỊCH SỬ GIAO DỊCH
# ==========================================

@login_required(login_url='login')
def borrow_history(request):
    # ---> ĐÃ SỬA LẠI ĐOẠN QUERY NÀY ĐỂ SẮP XẾP ƯU TIÊN TRẠNG THÁI <---
    history_list = BorrowTransaction.objects.filter(user=request.user).annotate(
        status_priority=Case(
            When(status='OVERDUE', then=Value(1)),   # Quá hạn lên top 1
            When(status='BORROWED', then=Value(2)),  # Đang mượn top 2
            When(status='PENDING', then=Value(3)),   # Chờ duyệt top 3
            When(status='RETURNED', then=Value(4)),  # Đã trả xuống cuối
            default=Value(5),
            output_field=IntegerField(),
        )
    ).order_by('status_priority', '-created_at')
    
    # Phân trang: Mỗi lần tải 8 giao dịch
    paginator = Paginator(history_list, 8) 
    page = request.GET.get('page', 1)
    
    try:
        history = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        history = paginator.page(1)
        
    return render(request, 'core/borrow_history.html', {'history': history})

# ==========================================
# 3. NGHIỆP VỤ YÊU CẦU TRẢ SÁCH (Dành cho Sinh viên)
# ==========================================

@login_required(login_url='login')
def return_book(request, transaction_id):
    # Chỉ lấy những giao dịch đang mượn (BORROWED) hoặc QUÁ HẠN (OVERDUE)
    borrow_record = get_object_or_404(BorrowTransaction, id=transaction_id, user=request.user, status__in=['BORROWED', 'OVERDUE'])
    
    try:
        # Chuyển trạng thái sang Chờ xác nhận
        borrow_record.status = 'PENDING'
        # ---> THÊM DÒNG NÀY: Gắn mác để phân biệt với đơn chờ mượn
        borrow_record.reason = 'YÊU CẦU TRẢ' 
        borrow_record.save()
        
        messages.success(request, f"Yêu cầu trả cuốn '{borrow_record.book.title}' đã được gửi. Vui lòng mang sách đến quầy để Thủ thư xác nhận.")
    except Exception as e:
        messages.error(request, f"Đã xảy ra lỗi: {str(e)}")
        
    return redirect('borrow_history')