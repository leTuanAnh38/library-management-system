# file: core/views/borrow_views.py
from django.http import JsonResponse
from datetime import timedelta, datetime
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
    
    # 1. NHẬN DIỆN AJAX: Kiểm tra xem yêu cầu có phải gửi ngầm không
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    # Hàm hỗ trợ: AJAX thì trả JSON, bình thường thì Redirect kèm thông báo Django
    def respond(status, message, redirect_url=None):
        if is_ajax:
            return JsonResponse({'status': status, 'message': message, 'redirect': redirect_url})
        else:
            if status == 'error': messages.error(request, message)
            elif status == 'warning': messages.warning(request, message)
            else: messages.success(request, message)
            return redirect(redirect_url or request.META.get('HTTP_REFERER', 'book_list'))

    # 2. KIỂM TRA PHÍ PHẠT
    if user.total_fine > 0:
        return respond('error', f"Bạn đang nợ ({user.total_fine} VNĐ) tiền phạt. Vui lòng thanh toán trước!", 'profile')

    # 3. KIỂM TRA HỒ SƠ
    if not getattr(user, 'msv', None) or not getattr(user, 'lop', None):
        return respond('warning', "Vui lòng cập nhật MSSV và Lớp trong hồ sơ trước khi mượn sách!", 'profile')

    # 4. KIỂM TRA GIỚI HẠN 4 CUỐN
    active_borrows_count = BorrowTransaction.objects.filter(
        user=user,
        status__in=['PENDING', 'BORROWED', 'OVERDUE']
    ).count()

    if active_borrows_count >= 4:
        return respond('error', f"Bạn đang mượn hoặc chờ duyệt {active_borrows_count} cuốn rồi. Tối đa chỉ được 4 cuốn!")

    # 5. LẤY THÔNG TIN SÁCH
    book = get_object_or_404(Book, id=book_id)

    # 6. KIỂM TRA MƯỢN TRÙNG
    already_borrowed = BorrowTransaction.objects.filter(
        user=user, 
        book=book, 
        status__in=['PENDING', 'BORROWED', 'OVERDUE']
    ).exists()

    if already_borrowed:
        return respond('warning', f"Bạn đang mượn hoặc đã gửi yêu cầu mượn cuốn '{book.title}' rồi!")
    
    # 7. KIỂM TRA KHO
    if book.quantity <= 0:
        return respond('error', f"Sách '{book.title}' đã hết trong kho!")
        
    # 8. LẤY DỮ LIỆU TỪ FORM (Ngày, Ca lấy, Phương thức thanh toán)
    is_premium = book.price and book.price > 0
    if request.method == 'POST':
        pickup_date = request.POST.get('pickup_date')
        pickup_shift = request.POST.get('pickup_shift')
        payment_method = request.POST.get('payment_method', 'FREE')
        
        if not pickup_date or not pickup_shift:
            return respond('error', "Vui lòng chọn ngày và ca lấy sách!")
    else:
        # Chặn truy cập trực tiếp qua URL (GET request) vì phải dùng Modal để chọn ngày
        return respond('error', "Vui lòng sử dụng form đăng ký để chọn thời gian nhận sách.")

    han_tra = timezone.now().date() + timedelta(days=14)
    status = 'PENDING' 
    is_paid = False if is_premium else True

    # Xử lý chuỗi thông báo thời gian
    try:
        formatted_date = datetime.strptime(pickup_date, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        formatted_date = pickup_date
    shift_display = "Buổi Sáng (07:30 - 11:30)" if pickup_shift == 'SANG' else "Buổi Chiều (13:00 - 17:00)"

    # 9. TIẾN HÀNH TẠO GIAO DỊCH
    try:
        with db_transaction.atomic():
            BorrowTransaction.objects.create(
                user=user, book=book, due_date=han_tra, 
                status=status, payment_method=payment_method, is_paid=is_paid,
                pickup_date=pickup_date, pickup_shift=pickup_shift # Lưu thông tin lịch hẹn
            )

            # Tùy chỉnh tin nhắn theo loại sách
            if is_premium:
                payment_display = dict(BorrowTransaction.PAYMENT_CHOICES).get(payment_method, payment_method)
                msg = f"Đăng ký thành công! Vui lòng thanh toán {book.price:,.0f} VNĐ ({payment_display}) và đến nhận sách vào {shift_display} ngày {formatted_date}."
            else:
                msg = f"Đăng ký thành công! Bạn nhớ đến nhận sách vào {shift_display} ngày {formatted_date}. Quá hạn hệ thống sẽ tự hủy đơn!"

            Notification.objects.create(user=user, message=msg, type='SYSTEM', status='UNREAD')
            book.quantity -= 1
            book.save()

        # Giữ nguyên logic hiển thị tin nhắn của bạn
        if not is_ajax:
            try:
                request.session['show_borrow_info_msg'] = msg
            except Exception:
                pass

        return respond('success', msg)
    except Exception as e:
        return respond('error', f"Lỗi hệ thống: {str(e)}")
# ==========================================
# 2. HỆ THỐNG GIỎ MƯỢN SÁCH (CART)
# ==========================================
@login_required(login_url='login')
def add_to_cart(request, book_id):
    cart = request.session.get('borrow_cart', [])
    active_borrows = BorrowTransaction.objects.filter(user=request.user, status__in=['PENDING', 'BORROWED', 'OVERDUE']).count()
    
    if active_borrows + len(cart) >= 4:
        return JsonResponse({'success': False, 'message': f'Giới hạn 4 cuốn! Bạn đang giữ {active_borrows} cuốn và có {len(cart)} cuốn trong giỏ.'})
        
    already_borrowed = BorrowTransaction.objects.filter(user=request.user, book_id=book_id, status__in=['PENDING', 'BORROWED', 'OVERDUE']).exists()
    if already_borrowed:
        return JsonResponse({'success': False, 'message': 'Bạn đã mượn hoặc đang chờ duyệt cuốn sách này rồi.'})

    if str(book_id) not in cart:
        cart.append(str(book_id))
        request.session['borrow_cart'] = cart
        
        # ---> THÊM DÒNG NÀY: Ép Django phải lưu lại Session ngay lập tức <---
        request.session.modified = True 
        
        return JsonResponse({'success': True, 'cart_count': len(cart), 'message': 'Đã thêm vào giỏ sách!'})
    else:
        return JsonResponse({'success': False, 'message': 'Sách này đã có trong giỏ.'})
@login_required(login_url='login')
def view_cart(request):
    cart_ids = request.session.get('borrow_cart', [])
    books = Book.objects.filter(id__in=cart_ids)
    total_fee = sum(book.price for book in books if book.price)
    return render(request, 'core/cart.html', {'books': books, 'total_fee': total_fee})

@login_required(login_url='login')
def remove_from_cart(request, book_id):
    cart = request.session.get('borrow_cart', [])
    if str(book_id) in cart:
        cart.remove(str(book_id))
        request.session['borrow_cart'] = cart
        messages.success(request, "Đã xóa sách khỏi giỏ.")
    return redirect('view_cart')

@login_required(login_url='login')
def checkout_cart(request):
    if request.method == 'POST':
        cart_ids = request.session.get('borrow_cart', [])
        if not cart_ids: return redirect('book_list')
            
        pickup_date = request.POST.get('pickup_date')
        pickup_shift = request.POST.get('pickup_shift')
        payment_method = request.POST.get('payment_method', 'FREE')
        
        books = Book.objects.filter(id__in=cart_ids)
        han_tra = timezone.now().date() + timedelta(days=14)
        
        try:
            with db_transaction.atomic():
                for book in books:
                    if book.quantity > 0:
                        is_premium = book.price and book.price > 0
                        BorrowTransaction.objects.create(
                            user=request.user, book=book, due_date=han_tra, status='PENDING',
                            payment_method=payment_method, is_paid=not is_premium,
                            pickup_date=pickup_date, pickup_shift=pickup_shift
                        )
                        book.quantity -= 1
                        book.save()
                        
                total_fee = sum(b.price for b in books if b.price)
                shift_display = "Sáng" if pickup_shift == 'SANG' else "Chiều"
                
                if total_fee > 0:
                    msg = f"Đăng ký {len(books)} cuốn thành công! Tổng phí: {total_fee:,.0f} VNĐ. Hẹn bạn lấy sách vào ca {shift_display} ngày {pickup_date}."
                else:
                    msg = f"Đăng ký {len(books)} cuốn thành công! Nhớ đến lấy sách vào ca {shift_display} ngày {pickup_date} nhé."
                
                Notification.objects.create(user=request.user, message=msg, type='SYSTEM', status='UNREAD')
                
            request.session['borrow_cart'] = []
            messages.success(request, msg)
            return redirect('borrow_history')
        except Exception as e:
            messages.error(request, f"Lỗi hệ thống: {str(e)}")
            return redirect('view_cart')
    return redirect('view_cart')
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
        
        messages.success(request, f"Yêu cầu trả cuốn '{borrow_record.book.title}' đã được gửi. Vui lòng mang sách đến quầy trong vòng 24h để Thủ thư xác nhận.")
    except Exception as e:
        messages.error(request, f"Đã xảy ra lỗi: {str(e)}")
        
    return redirect('borrow_history')
#Tạo thêm view để xử lý trả nhiều sách cùng lúc (nếu muốn)
@login_required(login_url='login')
def return_books_batch(request):
    """Xử lý yêu cầu trả nhiều sách cùng lúc"""
    if request.method == 'POST':
        # Lấy danh sách các ID giao dịch được tick chọn
        transaction_ids = request.POST.getlist('transaction_ids')
        
        if not transaction_ids:
            messages.warning(request, "Bạn chưa chọn cuốn sách nào để trả.")
            return redirect('borrow_history')

        # Lọc ra các giao dịch hợp lệ (của user này và đang mượn/quá hạn)
        records = BorrowTransaction.objects.filter(
            id__in=transaction_ids,
            user=request.user,
            status__in=['BORROWED', 'OVERDUE']
        )

        count = records.count()
        if count > 0:
            # Chuyển đổi trạng thái hàng loạt
            records.update(status='PENDING', reason='YÊU CẦU TRẢ')
            messages.success(request, f"Thành công! Đã gửi yêu cầu báo trả cho {count} cuốn sách. Vui lòng mang sách đến quầy thủ thư.")
        else:
            messages.error(request, "Không có giao dịch nào hợp lệ để trả.")

    return redirect('borrow_history')