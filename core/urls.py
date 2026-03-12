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
]