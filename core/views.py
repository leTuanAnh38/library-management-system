from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import update_session_auth_hash, authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Book, BorrowTransaction, Review, Category, Wishlist # Thêm Wishlist vào đây
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
    query = request.GET.get('q', '')
    books_list = Book.objects.all().order_by('-created_at') 
    categories = Category.objects.all()

    if query:
        books_list = books_list.filter(
            Q(title__icontains=query) |          
            Q(author__icontains=query) |         
            Q(category__name__icontains=query)   
        ).distinct()

    wishlist_book_ids = []
    borrowed_book_ids = []
    
    if request.user.is_authenticated:
        # 1. Lấy ID sách đã yêu thích (để giữ màu hồng trái tim)
        wishlist_book_ids = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
        
        # 2. Lấy ID sách ĐANG MƯỢN (để đổi trạng thái nút)
        borrowed_book_ids = BorrowTransaction.objects.filter(
            user=request.user, 
            status='BORROWED'
        ).values_list('book_id', flat=True)

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
        'wishlist_book_ids': list(wishlist_book_ids),
        'borrowed_book_ids': list(borrowed_book_ids) # Gửi danh sách đang mượn sang HTML
    }
    return render(request, 'core/book_list.html', context)

@login_required(login_url='login')
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if book.quantity <= 0:
        messages.error(request, f"Sách '{book.title}' đã hết trong kho!")
        return redirect('book_list')

    han_tra = timezone.now().date() + timedelta(days=14)

    transaction = BorrowTransaction.objects.create(
        user=request.user,
        book=book,
        due_date=han_tra, 
        status='BORROWED'
    )

    # --- THÊM: Tạo thông báo mượn thành công ---
    Notification.objects.create(
        user=request.user,
        message=f"Mượn thành công! Hạn trả cuốn '{book.title}' là ngày {han_tra.strftime('%d/%m/%Y')}.",
        type='SYSTEM',
        status='UNREAD'
    )
    # ------------------------------------------

    book.quantity -= 1
    book.save()

    messages.success(request, f"Mượn thành công! Hạn trả cuốn '{book.title}' là ngày {han_tra.strftime('%d/%m/%Y')}.")
    
    return redirect('book_list')

@login_required(login_url='login')
def borrow_history(request):
    history = BorrowTransaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/borrow_history.html', {'history': history})

@login_required(login_url='login')
def return_book(request, transaction_id):
    # Lấy giao dịch mượn sách, đảm bảo nó tồn tại, thuộc về người dùng và chưa được trả
    borrow_record = get_object_or_404(
        BorrowTransaction, 
        id=transaction_id, 
        user=request.user, 
        status='BORROWED' # Thêm điều kiện này vào get_object_or_404 để xử lý gọn hơn
    )
    
    # Sử dụng database transaction để đảm bảo tính nhất quán dữ liệu
    try:
        with db_transaction.atomic():
            # Cập nhật bản ghi mượn sách
            borrow_record.status = 'RETURNED'
            borrow_record.return_date = timezone.now().date()
            borrow_record.save()
            
            # Cập nhật số lượng sách
            book = borrow_record.book
            book.quantity += 1
            book.save()
            
            messages.success(request, f"Bạn đã trả cuốn sách '{book.title}' thành công. Cảm ơn bạn!")
    except Exception as e:
        # Xử lý lỗi nếu có bất kỳ thao tác nào trong transaction bị thất bại
        messages.error(request, f"Đã xảy ra lỗi khi trả sách: {str(e)}")
        # Bạn có thể muốn log lỗi ở đây để kiểm tra sau
        
    return redirect('borrow_history')

def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    reviews = book.reviews.all().order_by('-created_at')
    
    borrowed_book_ids = []
    if request.user.is_authenticated:
        # Lấy danh sách ID các sách Khanh đang mượn chưa trả
        borrowed_book_ids = BorrowTransaction.objects.filter(
            user=request.user, 
            status='BORROWED'
        ).values_list('book_id', flat=True)
    
    return render(request, 'core/book_detail.html', {
        'book': book,
        'reviews': reviews,
        'borrowed_book_ids': list(borrowed_book_ids) # Gửi sang HTML
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