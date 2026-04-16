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
from django.urls import reverse
from urllib.parse import urlencode
from datetime import datetime
# Hàm kiểm tra quyền Staff
def is_staff(user):
    return user.is_authenticated and user.role in ['STAFF', 'ADMIN']

# ==========================================
# 1. QUẢN LÝ KHO SÁCH (CRUD)
# ==========================================
@user_passes_test(is_staff, login_url='login')
def staff_dashboard(request):
    # 1. Lấy đơn trễ hạn
    overdue_transactions = BorrowTransaction.objects.filter(
        status='OVERDUE'
    ).select_related('user', 'book').order_by('due_date') 

    # 2. Lấy đơn CHỜ DUYỆT MƯỢN (Mới thêm)
    pending_transactions = BorrowTransaction.objects.filter(
        status='PENDING'
    ).select_related('user', 'book').order_by('created_at')
    
    # 3. Lấy đơn ĐANG MƯỢN / CHỜ TRẢ (Mới thêm)
    borrowed_transactions = BorrowTransaction.objects.filter(
        status='BORROWED'
    ).select_related('user', 'book').order_by('due_date')

    total_library_books = Book.objects.aggregate(total=Sum('initial_quantity'))['total'] or 0
    current_available_books = Book.objects.aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'core/staff/dashboard.html', {
        'overdue_transactions': overdue_transactions,
        'pending_transactions': pending_transactions,  # Truyền dữ liệu ra template
        'borrowed_transactions': borrowed_transactions, # Truyền dữ liệu ra template
        'total_library_books': total_library_books,
        'current_available_books': current_available_books
    })

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
    
    # 1. Bắt lấy tham số 'page' trên thanh địa chỉ URL (mặc định là 1 nếu không có)
    page_number = request.GET.get('page', 1) 
    
    # 2. Phân trang (10 cuốn / 1 lần tải)
    paginator = Paginator(books, 10) 
    
    # 3. Đưa biến page_number vào thay vì gán cứng số 1
    page_obj = paginator.get_page(page_number) 

    return render(request, 'core/staff/book_list.html', {
        'books': page_obj, # HTML đang dùng for book in books, nên nó sẽ lặp qua page_obj này
        'query': query
    })
@user_passes_test(is_staff)
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f"Thêm sách '{form.cleaned_data.get('title')}' thành công!")
            return redirect('staff_book_list')
    else:
        form = BookForm()
    
    return render(request, 'core/staff/book_form.html', {
        'form': form, 
        'title': 'Thêm sách mới'
    })

@user_passes_test(is_staff)
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # 1. Bắt lấy số trang hiện tại từ URL (Nếu không có thì mặc định là 1)
    current_page = request.GET.get('page', '1')
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật thông tin sách thành công!")
            
            # 2. Tạo URL chuyển hướng về Kho sách kèm theo số trang hiện tại
            base_url = reverse('staff_book_list')
            query_string = urlencode({'page': current_page})
            url = f"{base_url}?{query_string}"
            return redirect(url)
    else:
        form = BookForm(instance=book)
        
    return render(request, 'core/staff/book_form.html', {
        'form': form, 
        'title': 'Chỉnh sửa sách',
        'current_page': current_page  # 3. Truyền số trang ra giao diện HTML cho nút Hủy bỏ
    })

@user_passes_test(is_staff)
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # 1. Lấy số trang hiện tại từ URL
    current_page = request.GET.get('page', '1')
    
    # 2. Xóa sách
    book.delete()
    messages.success(request, "Đã xóa sách khỏi hệ thống!")
    
    # 3. Trở về đúng trang vừa thao tác xóa
    base_url = reverse('staff_book_list')
    query_string = urlencode({'page': current_page})
    url = f"{base_url}?{query_string}"
    return redirect(url)

# --- QUẢN LÝ DANH MỤC ---
@user_passes_test(is_staff, login_url='login')
def staff_category_list(request):
    # 1. Bắt từ khóa tìm kiếm
    query = request.GET.get('search_query', '').strip()
    
    # 2. Lấy danh sách danh mục (Sắp xếp theo tên như cũ)
    categories = Category.objects.all().order_by('name')
    
    # 3. Xử lý bộ lọc tìm kiếm
    if query:
        categories = categories.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).distinct()
        
    # 4. Xử lý phân trang (10 danh mục / trang)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(categories, 10)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/staff/category_list.html', {
        'categories': page_obj,  # Truyền danh sách đã phân trang ra HTML
        'query': query           # Truyền lại biến q để giữ text trên thanh tìm kiếm
    })

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
@user_passes_test(is_staff, login_url='login')
def staff_publisher_list(request):
    # 1. Bắt từ khóa tìm kiếm trên URL
    query = request.GET.get('search_query', '').strip()
    
    # 2. Lấy toàn bộ danh sách NXB (Sắp xếp theo tên như code cũ của bạn)
    publishers = Publisher.objects.all().order_by('name')
    
    # 3. Lọc dữ liệu nếu admin có gõ tìm kiếm
    if query:
        publishers = publishers.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query)
        ).distinct()
        
    # 4. Chia trang (10 nhà xuất bản / 1 trang)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(publishers, 10)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'core/staff/publisher_list.html', {
        'publishers': page_obj, # Truyền biến đã phân trang ra giao diện
        'query': query          # Truyền lại từ khóa để thanh search không bị mất chữ
    })

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

@user_passes_test(is_staff, login_url='login')
def staff_borrow_management(request):
    # ========================================================
    # 1. LOGIC TỰ ĐỘNG HỦY ĐƠN TRỄ HẸN LẤY SÁCH (CHO MƯỢN)
    # ========================================================
    # Lấy chính xác giờ trên đồng hồ máy tính để tránh lỗi múi giờ UTC
    now = datetime.now() 
    today_date = now.date()
    current_hour = now.hour
    # Lấy các đơn CHỜ DUYỆT (Loại trừ các đơn sinh viên đang yêu cầu trả)
    pending_mmuon = BorrowTransaction.objects.filter(status='PENDING').exclude(reason='YÊU CẦU TRẢ')
    
    for t in pending_mmuon:
        is_expired = False
        if t.pickup_date:
            # Nếu ngày hẹn đã qua hoặc là hôm nay nhưng đã quá ca trực
            if t.pickup_date < today_date:
                is_expired = True
            elif t.pickup_date == today_date:
                if t.pickup_shift == 'SANG' and current_hour >= 12: # Quá 12h trưa hủy ca Sáng
                    is_expired = True
                elif t.pickup_shift == 'CHIEU' and current_hour >= 18: # Quá 18h tối hủy ca Chiều
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

    # ========================================================
    # 2. LOGIC TỰ ĐỘNG XỬ LÝ "YÊU CẦU TRẢ" ẢO (SAU 24 GIỜ)
    # ========================================================
    # Nếu sinh viên bấm trả nhưng quá 24h không mang sách tới quầy, trả về trạng thái Đang mượn
    return_requests = BorrowTransaction.objects.filter(status='PENDING', reason='YÊU CẦU TRẢ')
    for r in return_requests:
        if r.updated_at < timezone.now() - timedelta(days=1):
            r.status = 'BORROWED'
            r.reason = '' # Xóa nhãn yêu cầu trả
            r.save()
            
            Notification.objects.create(
                user=r.user,
                message=f"Yêu cầu trả sách '{r.book.title}' bị hủy do bạn không mang sách tới quầy. Vui lòng thực hiện lại khi sẵn sàng.",
                type='SYSTEM', status='UNREAD'
            )

    # ========================================================
    # 3. LẤY DANH SÁCH & PHÂN TRANG
    # ========================================================
    query = request.GET.get('search_query', '').strip()
    
    # Sắp xếp ưu tiên: Chờ duyệt > Quá hạn > Đang mượn > Khác
    transactions = BorrowTransaction.objects.select_related('user', 'book').annotate(
        status_priority=Case(
            When(status='PENDING', then=Value(1)),
            When(status='OVERDUE', then=Value(2)),
            When(status='BORROWED', then=Value(3)),
            When(status='CANCELLED', then=Value(4)),
            When(status='RETURNED', then=Value(5)),
            default=Value(6),
            output_field=IntegerField(),
        )
    )
    
    if query:
        transactions = transactions.filter(
            Q(user__msv__icontains=query) |          
            Q(user__username__icontains=query) |     
            Q(book__title__icontains=query)
        ).distinct()
        
    transactions = transactions.order_by('status_priority', '-created_at')
    
    page_number = request.GET.get('page', 1) 
    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(page_number) 
    
    return render(request, 'core/staff/borrow_management.html', {
        'transactions': page_obj, 
        'query': query,
        'today': today_date
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
    
    if request.method == 'POST':
        book_condition = request.POST.get('book_condition', 'NORMAL')
        
        try:
            with db_transaction.atomic():
                today = timezone.now().date()
                borrow_record.status = 'RETURNED'
                borrow_record.return_date = today
                borrow_record.save()
                
                fine_amount = 0
                penalty_reasons = []
                
                # 1. Xử lý phạt trễ hạn
                if today > borrow_record.due_date:
                    user.points = max(0, user.points - 5)
                    days_late = (today - borrow_record.due_date).days
                    late_fine = days_late * 5000
                    fine_amount += late_fine
                    penalty_reasons.append(f"Trả trễ {days_late} ngày ({late_fine:,.0f}đ)")
                else:
                    user.points += 10 
                    
                # 2. Xử lý phạt hư hỏng/mất sách
                original_price = borrow_record.book.original_price or 0
                if book_condition == 'LIGHT_DAMAGE':
                    damage_fine = int(float(original_price) * 0.10) # Phạt 10%
                    fine_amount += damage_fine
                    penalty_reasons.append(f"Hư hỏng nhẹ sách ({damage_fine:,.0f}đ)")
                elif book_condition == 'LOST_OR_DESTROYED':
                    damage_fine = int(original_price) # Đền 100%
                    fine_amount += damage_fine
                    penalty_reasons.append(f"Mất/Hư hỏng nặng sách ({damage_fine:,.0f}đ)")
                    
                # 3. Tạo phiếu phạt và thông báo
                if fine_amount > 0:
                    reason_str = " + ".join(penalty_reasons)
                    Penalty.objects.create(
                        user=user,
                        borrow_transaction=borrow_record,
                        amount=fine_amount,
                        reason=reason_str,
                        status='UNPAID'
                    )
                    Notification.objects.create(
                        user=user,
                        message=f"CẢNH BÁO: Thủ thư đã thu hồi cuốn '{borrow_record.book.title}'. Hệ thống phạt {fine_amount:,.0f} VNĐ vì lý do: {reason_str}.",
                        type='SYSTEM',
                        status='UNREAD'
                    )
                else:
                    Notification.objects.create(
                        user=user,
                        message=f"Tuyệt vời! Thủ thư đã thu hồi cuốn '{borrow_record.book.title}' thành công. Bạn được cộng 10 điểm thưởng vì trả đúng hạn.",
                        type='SYSTEM',
                        status='UNREAD'
                    )
                
                user.save() 
                
                # 4. Hoàn sách vào kho (Trừ khi bị mất)
                book = borrow_record.book
                if book_condition != 'LOST_OR_DESTROYED':
                    book.quantity += 1
                book.save()
                
                messages.success(request, f"Đã xác nhận thu hồi sách từ Sinh viên {user.msv}. Tình trạng: {book_condition}")
        except Exception as e:
            messages.error(request, f"Lỗi hệ thống: {str(e)}")
            
    return redirect('staff_borrow_management')
# ==========================================
# 3. QUẢN LÝ TIỀN PHẠT & NGƯỜI DÙNG
# ==========================================

@user_passes_test(is_staff, login_url='login')
def staff_penalty_management(request):
    query = request.GET.get('search_query', '').strip()
    
    # 1. Lấy TẤT CẢ khoản phạt (không dùng exclude PAID nữa)
    # Sắp xếp ưu tiên: Chờ duyệt (1) -> Chưa đóng (2) -> Đã đóng (3)
    penalties = Penalty.objects.select_related('user').annotate(
        status_priority=Case(
            When(status='PROCESSING', then=Value(1)), # Khớp với status trong code của bạn
            When(status='UNPAID', then=Value(2)),
            When(status='PAID', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    )
    
    # 2. Xử lý tìm kiếm theo thanh search
    if query:
        penalties = penalties.filter(
            Q(user__msv__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query)
        ).distinct()

    penalties = penalties.order_by('status_priority', '-created_at')

    # 3. Tính tổng số tiền cần thu (Chỉ cộng dồn những đơn UNPAID và PROCESSING)
    unpaid_penalties = Penalty.objects.filter(status__in=['UNPAID', 'PROCESSING'])
    total_pending_fines = unpaid_penalties.aggregate(total=Sum('amount'))['total'] or 0

    # 4. Phân trang (10 giao dịch / trang)
    page_number = request.GET.get('page', 1) 
    paginator = Paginator(penalties, 10)
    page_obj = paginator.get_page(page_number) 
    
    return render(request, 'core/staff/penalty_management.html', {
        'penalties': page_obj,  
        'query': query,
        'total_pending_fines': total_pending_fines
    })

# Hàm dưới này của bạn đã quá chuẩn, cứ giữ nguyên nhé!
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
    # 1. Lọc danh sách người đọc (Rất tốt, đã loại trừ đúng Admin/Staff)
    readers = User.objects.filter(
        is_staff=False, 
        is_superuser=False
    ).exclude(role__in=['STAFF', 'ADMIN']).order_by('username')
    
    # 2. Xử lý tìm kiếm
    query = request.GET.get('search_query', '').strip()
    if query:
        readers = readers.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(msv__icontains=query)
        )
        
    # 3. ---> THÊM XỬ LÝ PHÂN TRANG Ở ĐÂY <---
    page_number = request.GET.get('page', 1)  # Lấy số trang hiện tại từ URL
    paginator = Paginator(readers, 10)        # Chia 10 người / 1 trang
    page_obj = paginator.get_page(page_number) # Lấy dữ liệu của trang đó
    
    return render(request, 'core/staff/user_management.html', {
        'readers': page_obj,  # Truyền page_obj ra HTML để các nút 1,2,3 hoạt động
    })

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
    # 1. Bắt từ khóa tìm kiếm
    query = request.GET.get('search_query', '').strip()

    # Lấy thông tin bài đánh giá gần nhất của mỗi cuốn sách
    latest_review = Review.objects.filter(book=OuterRef('pk')).order_by('-created_at')

    # Query gốc của bạn (rất xịn)
    books = Book.objects.annotate(
        review_count=Count('reviews'), 
        avg_rating=Avg('reviews__rating'), 
        latest_reviewer=Subquery(latest_review.values('user__username')[:1]),
        latest_review_date=Subquery(latest_review.values('created_at')[:1])
    ).filter(review_count__gt=0)
    
    # 2. Xử lý tìm kiếm (nếu có)
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    # 3. Sắp xếp dữ liệu
    books = books.order_by('-avg_rating', '-review_count')

    # 4. Xử lý phân trang (10 cuốn / 1 trang)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(books, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/staff/review_management.html', {
        'books': page_obj,  # Truyền page_obj thay cho toàn bộ books
        'query': query      # Truyền query để giữ text ở thanh tìm kiếm
    })