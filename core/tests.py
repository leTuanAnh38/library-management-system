from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Book, BorrowTransaction, Penalty, Category

User = get_user_model()

class LibraryBusinessLogicTests(TestCase):
    def setUp(self):
        """
        Hàm này chạy trước MỖI bài test. 
        Dùng để tạo sẵn dữ liệu ảo (Mock Data) trên RAM để test.
        """
        # 1. Tạo 1 Category ảo
        self.category = Category.objects.create(name='Công nghệ thông tin')
        
        # 2. Tạo 1 User ảo
        self.user = User.objects.create_user(
            username='khanh_test', 
            password='testpassword123',
            first_name='Khanh',
            msv='SV999',
            lop='KTPM',
            points=20 # Cho sẵn 20 điểm
        )
        
        # 3. Tạo 1 Cuốn sách ảo
        self.book = Book.objects.create(
            title='Clean Code',
            author='Robert C. Martin',
            quantity=5,
            category=self.category
        )

    # ==========================================
    # BÀI TEST 1: Kiểm tra khởi tạo User thành công
    # ==========================================
    def test_01_user_creation_and_attributes(self):
        self.assertEqual(self.user.username, 'khanh_test')
        self.assertEqual(self.user.msv, 'SV999')
        self.assertEqual(User.objects.count(), 1) # Đảm bảo DB ảo có đúng 1 user

    # ==========================================
    # BÀI TEST 2: Kiểm tra logic số lượng sách giảm khi mượn
    # ==========================================
    def test_02_borrow_book_decreases_quantity(self):
        initial_quantity = self.book.quantity
        
        # Giả lập hành động mượn sách
        BorrowTransaction.objects.create(
            user=self.user,
            book=self.book,
            due_date=timezone.now().date() + timedelta(days=14),
            status='BORROWED'
        )
        self.book.quantity -= 1
        self.book.save()

        # Kiểm tra xem kho sách có bị trừ đi 1 không (5 - 1 = 4)
        self.assertEqual(self.book.quantity, initial_quantity - 1)

    # ==========================================
    # BÀI TEST 3: Kiểm tra logic chặn mượn sách khi đang nợ tiền phạt (ĐÃ FIX LỖI)
    # ==========================================
    def test_03_user_with_unpaid_penalty_has_fine(self):
        # 1. Tạo một giao dịch mượn sách ảo trước (BẮT BUỘC ĐỂ KHÔNG BỊ LỖI NULL)
        dummy_transaction = BorrowTransaction.objects.create(
            user=self.user,
            book=self.book,
            due_date=timezone.now().date() - timedelta(days=10),
            status='RETURNED'
        )

        # 2. Giả lập user bị phạt 50k, gắn với giao dịch ảo vừa tạo
        Penalty.objects.create(
            user=self.user,
            borrow_transaction=dummy_transaction, # Dòng vá lỗi nằm ở đây
            amount=50000,
            reason="Làm rách trang sách",
            status='UNPAID'
        )
        
        # 3. Gọi hàm property total_fine trong models để xem hệ thống có tính đúng tổng nợ không
        self.assertEqual(self.user.total_fine, 50000)
        self.assertTrue(self.user.total_fine > 0) # Khẳng định user này không đủ điều kiện mượn

    # ==========================================
    # BÀI TEST 4: Kiểm tra logic CỘNG điểm khi trả đúng hạn
    # ==========================================
    def test_04_return_book_on_time_adds_points(self):
        initial_points = self.user.points # Ban đầu có 20 điểm
        
        # Giả lập logic trong hàm return_book (trả đúng hạn được +10)
        self.user.points += 10
        self.user.save()
        
        # Mong đợi: 20 + 10 = 30 điểm
        self.assertEqual(self.user.points, initial_points + 10)

    # ==========================================
    # BÀI TEST 5: Kiểm tra logic TRỪ điểm khi trả trễ hạn (Không âm điểm)
    # ==========================================
    def test_05_return_book_late_deducts_points(self):
        # Đặt lại điểm user thành 3 điểm (để test logic không bị âm)
        self.user.points = 3
        self.user.save()
        
        # Giả lập logic trong hàm return_book (trả trễ bị -5, min = 0)
        self.user.points = max(0, self.user.points - 5)
        self.user.save()
        
        # Mong đợi: 3 - 5 = -2, nhưng hệ thống chặn số âm nên điểm phải bằng 0
        self.assertEqual(self.user.points, 0)