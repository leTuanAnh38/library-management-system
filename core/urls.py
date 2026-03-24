from django.urls import path

# Import 6 file view riêng biệt từ thư mục core/views/ mà chúng ta vừa tạo
from core.views import (
    auth_views,
    book_views,
    borrow_views,
    user_views,
    staff_views,
    api_views
)

urlpatterns = [
    # ==========================================
    # 1. NHÓM XÁC THỰC (AUTHENTICATION)
    # ==========================================
    path('login/', auth_views.user_login, name='login'),
    path('register/', auth_views.register, name='register'),
    path('logout/', auth_views.user_logout, name='logout'),
    path('change-password/', auth_views.change_password, name='change_password'),

    # ==========================================
    # 2. NHÓM HIỂN THỊ SÁCH (TRANG CHỦ & TÌM KIẾM)
    # ==========================================
    path('', book_views.home, name='home'),
    path('books/', book_views.book_list, name='book_list'),
    path('premium-books/', book_views.premium_book_list, name='premium_books'),
    path('book/<int:book_id>/', book_views.book_detail, name='book_detail'),
    path('book/<int:book_id>/review/', book_views.add_review, name='add_review'),
    path('guide/', book_views.guide_view, name='guide'),
    path('contact/', book_views.contact_view, name='contact'),

    # ==========================================
    # 3. NHÓM NGƯỜI DÙNG CÁ NHÂN (USER PROFILE)
    # ==========================================
    path('profile/', user_views.profile_view, name='profile'),
    path('pay-penalties/', user_views.pay_all_penalties, name='pay_all_penalties'),
    path('wishlist/', user_views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:book_id>/', user_views.toggle_wishlist, name='toggle_wishlist'),
    path('notifications/', user_views.notification_list, name='notification_list'),

    # ==========================================
    # 4. NHÓM MƯỢN TRẢ SÁCH (BORROW / RETURN)
    # ==========================================
    path('borrow/<int:book_id>/', borrow_views.borrow_book, name='borrow_book'),
    path('borrow-history/', borrow_views.borrow_history, name='borrow_history'),
    path('return/<int:transaction_id>/', borrow_views.return_book, name='return_book'),

    # ==========================================
    # 5. NHÓM NGHIỆP VỤ THỦ THƯ (STAFF DASHBOARD)
    # ==========================================
    path('staff/', staff_views.staff_dashboard, name='staff_dashboard'),
    path('staff/book/add/', staff_views.add_book, name='add_book'),
    path('staff/book/edit/<int:book_id>/', staff_views.edit_book, name='edit_book'),
    path('staff/book/delete/<int:book_id>/', staff_views.delete_book, name='delete_book'),
    
    path('staff/borrows/', staff_views.staff_borrow_management, name='staff_borrow_management'),
    path('staff/borrows/approve/<int:transaction_id>/', staff_views.staff_approve_borrow, name='staff_approve_borrow'),
    path('staff/borrows/confirm-return/<int:transaction_id>/', staff_views.staff_confirm_return, name='staff_confirm_return'),
    
    path('staff/penalties/', staff_views.staff_penalty_management, name='staff_penalty_management'),
    path('staff/penalties/confirm/<int:penalty_id>/', staff_views.staff_confirm_penalty, name='staff_confirm_penalty'),
    
    path('staff/users/', staff_views.staff_user_management, name='staff_user_management'),
    path('staff/users/<int:user_id>/', staff_views.staff_user_detail, name='staff_user_detail'),

    # ==========================================
    # 6. NHÓM API (XỬ LÝ NGẦM AJAX & LOAD MORE)
    # ==========================================
    path('api/books/', api_views.api_get_books, name='api_get_books'),
    path('api/books/add/', api_views.api_create_book, name='api_create_book'),
    path('api/books/delete/<int:book_id>/', api_views.api_delete_book, name='api_delete_book'),
    
    path('api/chart-data/', api_views.admin_chart_data, name='admin_chart_data'),
    path('api/search/', api_views.live_search_api, name='api_live_search'),
    path('api/wishlist/toggle/<int:book_id>/', api_views.toggle_wishlist_api, name='api_toggle_wishlist'),
    path('api/review/add/<int:book_id>/', api_views.api_add_review, name='api_add_review'),
    path('api/admin-chart/', api_views.admin_chart_data, name='admin_chart_data'),
    
    path('api/books/load-more/', api_views.api_load_more_books, name='api_load_more_books'),
    path('api/notifications/load-more/', api_views.api_load_more_notifications, name='api_load_more_notifications'),
    path('api/history/load-more/', api_views.api_load_more_history, name='api_load_more_history'),
    path('api/wishlist/load-more/', api_views.api_load_more_wishlist, name='api_load_more_wishlist'),
    path('api/notifications/unread-count/', api_views.api_unread_notification_count, name='api_unread_notification_count'),
]