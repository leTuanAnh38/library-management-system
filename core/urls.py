from django.urls import path
from . import views

urlpatterns = [
    # Đường dẫn trống '' nghĩa là trang chủ gốc (ví dụ: http://127.0.0.1:8000/)
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('kho-sach/', views.book_list, name='book_list'),
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    path('lich-su-muon/', views.borrow_history, name='borrow_history'),
    path('tra-sach/<int:transaction_id>/', views.return_book, name='return_book'),
    path('sach/<int:book_id>/', views.book_detail, name='book_detail'),
    path('sach/<int:book_id>/review/', views.add_review, name='add_review'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/add-book/', views.add_book, name='add_book'),
    path('staff/edit-book/<int:book_id>/', views.edit_book, name='edit_book'),
    path('staff/delete-book/<int:book_id>/', views.delete_book, name='delete_book'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:book_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/pay-all/', views.pay_all_penalties, name='pay_all_penalties'),
    path('api/books/', views.api_get_books, name='api_get_books'),
    path('api/books/add/', views.api_create_book, name='api_create_book'),
    path('api/books/delete/<int:book_id>/', views.api_delete_book, name='api_delete_book'),
    # core/urls.py
    path('staff/add-book/', views.add_book, name='add_book'),
    # URL cho quản lý Mượn / Trả của Thủ thư
    path('staff/borrows/', views.staff_borrow_management, name='staff_borrow_management'),
    path('staff/borrows/<int:transaction_id>/confirm/', views.staff_confirm_return, name='staff_confirm_return'),
    
    # URL cho quản lý Tiền Phạt của Thủ thư
    path('staff/penalties/', views.staff_penalty_management, name='staff_penalty_management'),
    path('staff/penalties/<int:penalty_id>/confirm/', views.staff_confirm_penalty, name='staff_confirm_penalty'),

    # core/urls.py
    path('staff/users/', views.staff_user_management, name='staff_user_management'),
    path('staff/users/<int:user_id>/', views.staff_user_detail, name='staff_user_detail'),
]