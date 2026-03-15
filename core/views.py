from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import update_session_auth_hash, authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Book, BorrowTransaction, Review, Category, Wishlist, Penalty # Thêm Wishlist vào đây
from .forms import CustomUserCreationForm, BookForm
from django.db import transaction as db_transaction # Đổi tên để tránh trùng với biến transaction
from .models import Notification
from .services import check_and_create_due_reminders


def user_logout(request):
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công!')
    return redirect('home')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đăng ký tài khoản thành công! Vui lòng đăng nhập.')
            return redirect('home') 
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'core/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.role in ['ADMIN', 'STAFF']:
            return redirect('/admin/')
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user) 
                messages.success(request, f'Chào mừng {username} đã quay lại!')
                
                if user.is_staff or user.is_superuser or user.role in ['ADMIN', 'STAFF']:
                    return redirect('/admin/') 
                else:
                    return redirect('home') 
            else:
                messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})

@login_required(login_url='login') 
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) 
            messages.success(request, 'Mật khẩu của bạn đã được cập nhật thành công!')
            return redirect('home')
        else:
            messages.error(request, 'Đổi mật khẩu thất bại. Vui lòng kiểm tra lại thông tin bên dưới.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'core/change_password.html', {'form': form})

def home(request):
    if request.user.is_authenticated:
        check_and_create_due_reminders(request.user)

    featured_books = Book.objects.all().order_by('-created_at')[:5]
    recommended_books = Book.objects.all().order_by('?')[:3] 
    books = Book.objects.all().order_by('-created_at')[:6]
    categories = Category.objects.all()

    wishlist_book_ids = []
    borrowed_book_ids = []
    
    if request.user.is_authenticated:
        # Lấy danh sách ID sách đã yêu thích
        wishlist_book_ids = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
        # Lấy danh sách ID sách đang mượn chưa trả
        borrowed_book_ids = BorrowTransaction.objects.filter(user=request.user, status='BORROWED').values_list('book_id', flat=True)

    return render(request, 'core/index.html', {
        'featured_books': featured_books,
        'recommended_books': recommended_books, 
        'books': books,
        'categories': categories,
        'wishlist_book_ids': list(wishlist_book_ids),
        'borrowed_book_ids': list(borrowed_book_ids)
    })
# HÀM BOOK_LIST CHUẨN (Đã gộp cả tìm kiếm, lọc và phân trang)
def book_list(request):
    # Lấy các tham số từ thanh địa chỉ (URL)
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'newest')  # Mặc định là mới nhất
    category_id = request.GET.get('category', '') # Lấy ID danh mục muốn lọc
    
    books_list = Book.objects.all() 
    categories = Category.objects.all()

    # 1. Lọc theo danh mục (nếu người dùng chọn)
    if category_id:
        books_list = books_list.filter(category_id=category_id)

    # 2. Xử lý tìm kiếm (giữ nguyên logic của Khanh)
    if query:
        books_list = books_list.filter(
            Q(title__icontains=query) |          
            Q(author__icontains=query) |         
            Q(category__name__icontains=query)   
        ).distinct()

    # 3. Xử lý Sắp xếp
    if sort == 'title':
        books_list = books_list.order_by('title') # Sắp xếp A-Z theo tiêu đề
    elif sort == 'oldest':
        books_list = books_list.order_by('created_at') # Cũ nhất
    else:
        books_list = books_list.order_by('-created_at') # Mới nhất (mặc định)

    # --- Phần xử lý Wishlist và Borrow (Giữ nguyên của Khanh) ---
    wishlist_book_ids = []
    borrowed_book_ids = []
    if request.user.is_authenticated:
        wishlist_book_ids = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
        borrowed_book_ids = BorrowTransaction.objects.filter(user=request.user, status='BORROWED').values_list('book_id', flat=True)

    # 4. Phân trang (Giữ nguyên của Khanh)
    paginator = Paginator(books_list, 6) 
    page = request.GET.get('page')
    try:
        books = paginator.page(page)
    except PageNotAnInteger:
        books = paginator.page(1)
    except EmptyPage:
        books = paginator.page(paginator.num_pages)

    context = {
        'books': books, 
        'categories': categories,
        'query': query,
        'current_sort': sort,        # Gửi lại để giữ trạng thái dropdown
        'current_category': category_id, # Gửi lại để giữ trạng thái dropdown
        'wishlist_book_ids': list(wishlist_book_ids),
        'borrowed_book_ids': list(borrowed_book_ids)
    }
    return render(request, 'core/book_list.html', context)

@login_required(login_url='login')
def borrow_book(request, book_id):
    user = request.user
    
    # 1. KIỂM TRA HỒ SƠ: Nếu thiếu MSSV hoặc Lớp thì không cho mượn
    # Chúng ta kiểm tra cả hai trường này xem có dữ liệu hay không
    if not user.msv or not user.lop:
        messages.warning(request, "Vui lòng cập nhật MSSV và Lớp trong hồ sơ cá nhân trước khi thực hiện mượn sách!")
        return redirect('profile') # Chuyển hướng Khanh về trang cập nhật hồ sơ

    # 2. Logic mượn sách (Chỉ chạy khi hồ sơ đã đầy đủ)
    book = get_object_or_404(Book, id=book_id)
    
    if book.quantity <= 0:
        messages.error(request, f"Sách '{book.title}' đã hết trong kho!")
        return redirect('book_list')

    han_tra = timezone.now().date() + timedelta(days=14)

    transaction = BorrowTransaction.objects.create(
        user=user,
        book=book,
        due_date=han_tra, 
        status='BORROWED'
    )

    # Tạo thông báo hệ thống
    Notification.objects.create(
        user=user,
        message=f"Mượn thành công! Hạn trả cuốn '{book.title}' là ngày {han_tra.strftime('%d/%m/%Y')}.",
        type='SYSTEM',
        status='UNREAD'
    )

    book.quantity -= 1
    book.save()

    messages.success(request, f"Mượn thành công! Hạn trả cuốn '{book.title}' là ngày {han_tra.strftime('%d/%m/%Y')}.")
    
    return redirect('book_list')

@login_required(login_url='login')
def borrow_history(request):
    history = BorrowTransaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/borrow_history.html', {'history': history})

# core/views.py
@login_required(login_url='login')
def return_book(request, transaction_id):
    borrow_record = get_object_or_404(BorrowTransaction, id=transaction_id, user=request.user, status='BORROWED')
    
    try:
        with db_transaction.atomic():
            today = timezone.now().date()
            borrow_record.status = 'RETURNED'
            borrow_record.return_date = today
            borrow_record.save()
            
            # --- THÊM LOGIC XỬ PHẠT TẠI ĐÂY ---
            if today > borrow_record.due_date:
                # Tính số ngày trễ
                days_late = (today - borrow_record.due_date).days
                # Giả sử phạt 5.000 VNĐ / ngày
                fine_amount = days_late * 5000
                
                from .models import Penalty
                Penalty.objects.create(
                    user=request.user,
                    borrow_transaction=borrow_record,
                    amount=fine_amount,
                    reason=f"Trả sách trễ {days_late} ngày (Hạn trả: {borrow_record.due_date})",
                    status='UNPAID'
                )
                messages.warning(request, f"Bạn trả sách trễ {days_late} ngày. Phí phạt phát sinh: {fine_amount} VNĐ.")
            # ----------------------------------

            book = borrow_record.book
            book.quantity += 1
            book.save()
            
            messages.success(request, f"Bạn đã trả cuốn sách '{book.title}' thành công.")
    except Exception as e:
        messages.error(request, f"Đã xảy ra lỗi: {str(e)}")
        
    return redirect('borrow_history')

# core/views.py

def book_detail(request, book_id):
    # 1. Lấy thông tin cuốn sách hiện tại
    book = get_object_or_404(Book, id=book_id)
    reviews = book.reviews.all().order_by('-created_at')
    
    # 2. LOGIC GỢI Ý THÔNG MINH:
    # - Tìm các cuốn sách cùng Category.
    # - Loại trừ cuốn sách hiện tại (.exclude).
    # - Sắp xếp ngẫu nhiên (.order_by('?')) để mỗi lần F5 sẽ thấy sách mới.
    # - Giới hạn lấy 4 cuốn [:4].
    recommended_books = Book.objects.filter(
        category=book.category
    ).exclude(id=book.id).order_by('?')[:4]

    # Dự phòng: Nếu danh mục này không đủ 4 cuốn, lấy thêm các sách mới nhất khác
    if recommended_books.count() < 4:
        additional_count = 4 - recommended_books.count()
        additional_books = Book.objects.exclude(
            id__in=[book.id] + [b.id for b in recommended_books]
        ).order_by('-created_at')[:additional_count]
        recommended_books = list(recommended_books) + list(additional_books)

    # 3. Kiểm tra sách đang mượn 
    borrowed_book_ids = []
    if request.user.is_authenticated:
        borrowed_book_ids = BorrowTransaction.objects.filter(
            user=request.user, 
            status='BORROWED'
        ).values_list('book_id', flat=True)
    
    # 4. Trả về template với thêm biến recommended_books
    return render(request, 'core/book_detail.html', {
        'book': book,
        'reviews': reviews,
        'recommended_books': recommended_books, # Dữ liệu gợi ý cho AI/ML section
        'borrowed_book_ids': list(borrowed_book_ids)
    })

@login_required(login_url='login')
def add_review(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        Review.objects.create(
            book=book,
            user=request.user,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Cảm ơn Bạn đã để lại nhận xét!")
    
    return redirect('book_detail', book_id=book_id)

def is_staff(user):
    return user.is_authenticated and user.role in ['STAFF', 'ADMIN']

# HÀM STAFF DASHBOARD CHUẨN (Có hỗ trợ tìm kiếm)
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
            messages.success(request, "Thêm sách mới thành công!")
            return redirect('staff_dashboard')
    else:
        form = BookForm()
    return render(request, 'core/staff/book_form.html', {'form': form, 'title': 'Thêm sách mới'})

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

# Hàm 1: Thêm/Bớt sách yêu thích
@login_required(login_url='login')
def toggle_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Kiểm tra xem cuốn sách này đã có trong danh sách yêu thích của User chưa
    wishlist_item = Wishlist.objects.filter(user=request.user, book=book).first()
    
    if wishlist_item:
        # Nếu có rồi thì xóa đi (Bỏ yêu thích)
        wishlist_item.delete()
        messages.success(request, f"Đã bỏ '{book.title}' khỏi danh sách yêu thích.")
    else:
        # Nếu chưa có thì tạo mới (Thêm yêu thích)
        Wishlist.objects.create(user=request.user, book=book)
        messages.success(request, f"Đã thêm '{book.title}' vào danh sách yêu thích.")
    
    # Lệnh này giúp trình duyệt tự động load lại đúng trang người dùng đang đứng (Trang chủ hoặc Kho sách)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

# Hàm 2: Hiển thị trang Danh sách yêu thích
@login_required(login_url='login')
def wishlist_view(request):
    # Lấy toàn bộ sách yêu thích của người dùng hiện tại
    wishlist_items = Wishlist.objects.filter(user=request.user).order_by('-created_at')
    
    # BỔ SUNG: Lấy ID các sách đang mượn (status='BORROWED')
    borrowed_book_ids = BorrowTransaction.objects.filter(
        user=request.user, 
        status='BORROWED'
    ).values_list('book_id', flat=True)
    
    return render(request, 'core/wishlist.html', {
        'wishlist_items': wishlist_items,
        'borrowed_book_ids': list(borrowed_book_ids)
    })

@login_required
def notification_list(request):
    # 1. Lấy tất cả thông báo của người dùng, mới nhất lên đầu
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # 2. Đánh dấu tất cả thông báo UNREAD của người dùng này thành READ
    notifications.filter(status='UNREAD').update(status='READ')
    
    return render(request, 'core/notifications.html', {'notifications': notifications})

# core/views.py
@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        # Thêm 'or ''' để tránh lỗi NULL trong MySQL
        user.first_name = request.POST.get('first_name') or ''
        user.last_name = request.POST.get('last_name') or ''
        user.msv = request.POST.get('msv') or ''
        user.lop = request.POST.get('lop') or ''
        user.dia_chi = request.POST.get('dia_chi') or ''
        
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
            
        user.save()
        messages.success(request, 'Cập nhật hồ sơ thành công!')
        return redirect('profile')
        
    return render(request, 'core/profile.html')

@login_required
def pay_all_penalties(request):
    if request.method == 'POST':
        method = request.POST.get('payment_method')
        # Tìm tất cả các phiếu phạt chưa thanh toán (UNPAID) của người dùng hiện tại
        unpaid_penalties = Penalty.objects.filter(user=request.user, status='UNPAID')
        
        if unpaid_penalties.exists():
            # Cập nhật phương thức và chuyển sang trạng thái chờ xử lý (PROCESSING)
            unpaid_penalties.update(payment_method=method, status='PROCESSING')
            messages.success(request, f"Đã gửi yêu cầu thanh toán bằng hình thức: {dict(Penalty.PAYMENT_METHODS).get(method)}.")
        else:
            messages.info(request, "Khanh hiện không có khoản phạt nào cần thanh toán.")
            
        return redirect('profile')