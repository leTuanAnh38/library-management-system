import google.genai as genai
from django.conf import settings
from django.db.models import Q, Count
from core.models import Book, User, BorrowTransaction
import time
from functools import wraps

# Rate limiting decorator để tránh vượt quota Gemini API
def rate_limit_gemini(func):
    """Giới hạn 1 request mỗi 5 giây"""
    last_call = [0]
    
    def wrapper(*args, **kwargs):
        elapsed = time.time() - last_call[0]
        if elapsed < 5:
            time.sleep(5 - elapsed)
        result = func(*args, **kwargs)
        last_call[0] = time.time()
        return result
    return wrapper

class GeminiChatService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def get_library_context(self):
        """Tạo context chi tiết về thư viện từ database"""
        total_books = Book.objects.count()
        available_books = Book.objects.filter(status='AVAILABLE').count()
        categories = list(Book.objects.values_list('category__name', flat=True).distinct())
        
        # Lấy top 5 sách được mượn nhiều nhất
        popular_books = Book.objects.annotate(
            borrow_count=Count('borrow_records')
        ).order_by('-borrow_count')[:5]
        popular_list = ", ".join([f"{b.title}" for b in popular_books])
        
        return f"""BẠN LÀ CHATBOT HỖ TRỢ THƯ VIỆN ĐIỆN TỬ - ALOVU THƯ VIỆN

📚 THÔNG TIN THỰC TẾ VỀ THƯ VIỆN:
- Tổng số sách: {total_books} cuốn
- Sách có sẵn để mượn: {available_books} cuốn
- Danh mục sách: {', '.join(categories) if categories else 'Chưa có danh mục'}
- Sách được mượn nhiều nhất: {popular_list if popular_list else 'Đang cập nhật'}

🎯 NHIỆM VỤ CỦA BẠN (BẮT BUỘC):
1. Hướng dẫn mượn sách: TÌM SÁCH → BẤM MƯỢN →  THỜI HẠN (14 ngày) → XÁC NHẬN → Chờ duyệt (thủ thư sẽ duyệt yêu cầu trong vòng 24h) → duyệt xong tới thư viện nhận sách
2. ĐỀ XUẤT SÁCH PHÙ HỢP dựa trên:
   - Danh mục người dùng yêu thích
   - Sách được mượn nhiều nhất
   - Sở thích lịch sử mượn
3. Trả lời câu hỏi về quy định thư viện
4. TRÁCH NHIỆM QUAN TRỌNG: Khi người dùng nói "Được/Có/Được rồi/OK", hãy TIẾP TỤC hỏi chi tiết để hỗ trợ!

⚙️ HƯỚNG DẬN TRẢ LỜI:
- Trả lời NGẮN GỌN (2-3 câu tối đa)
- Luôn dùng TIẾNG VIỆT, có icon 📚 📖 🔍
- Mỗi câu trả lời đều phải CÓ HÀNH ĐỘNG (đề xuất/hướng dẫn/gợi ý)
- Không được nói "Xin lỗi/Rất tiếc/Chưa có thông tin" - phải TÌM CÁCH GIẢI QUYẾT
- Khi người dùng đồng ý, LUÔN hỏi tiếp theo để tìm sách cụ thể"""
    
    def get_user_preferences(self, user):
        """Lấy thông tin sở thích sách của user từ lịch sử mượn"""
        borrows = BorrowTransaction.objects.filter(
            user=user, 
            status__in=['RETURNED', 'BORROWED']
        ).select_related('book').values('book__category__name')[:10]
        
        categories = [b['book__category__name'] for b in borrows if b['book__category__name']]
        return categories if categories else []
    
    def get_book_recommendations(self, user, category=None, limit=5):
        """Gợi ý sách dựa trên danh mục hoặc sở thích"""
        query = Book.objects.filter(status='AVAILABLE').exclude(
            borrow_records__user=user
        )
        
        if category:
            query = query.filter(category__name__icontains=category)
        else:
            user_categories = self.get_user_preferences(user)
            if user_categories:
                query = query.filter(category__name__in=user_categories)
        
        # Sắp xếp theo lượt mượn nhiều nhất
        query = query.annotate(
            borrow_count=Count('borrow_records')
        ).order_by('-borrow_count')
        
        return [
            f"📖 **{b.title}** - {b.author or 'Chưa rõ'} ({b.borrow_count} lượt mượn)"
            for b in query[:limit]
        ]
    
    @rate_limit_gemini
    def chat(self, user_message, user):
        """Gửi tin nhắn đến Gemini hoặc dùng mock nếu API hết quota"""
        try:
            context = self.get_library_context()
            user_categories = self.get_user_preferences(user)
            recommendations = self.get_book_recommendations(user)
            
            # Prompt cải thiện với system message rõ ràng
            prompt = f"""{context}

📋 THÔNG TIN VỀ NGƯỜI DÙNG HIỆN TẠI:
- Danh mục yêu thích: {', '.join(user_categories) if user_categories else 'Đang khám phá'}
- Gợi ý sách phù hợp: {chr(10).join(recommendations[:3]) if recommendations else 'Sách đa thể loại'}

💬 CUỘC HỘI THOẠI HIỆN TẠI:
Người dùng: {user_message}

HÀNH ĐỘNG BẠN PHẢI LÀM:
- Nếu hỏi về đề xuất sách: GỢI Ý 2-3 CUỐN CỤ THỂ từ danh sách trên
- Nếu hỏi về mượn sách: CHỈ RÕ từng BƯỚC TỪ TÌM → MƯỢN → XÁC NHẬN
- Nếu nói "Có/Được/OK": HỎI TIẾP để tìm sách CỤ THỂ hoặc danh mục
- Trả lời TỬC THì phải có ĐỊNH HƯỚNG hành động tiếp theo

Trả lời ngay:"""
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        
        except Exception as e:
            # Nếu API bị lỗi, dùng mock response
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                return self._get_mock_response(user_message, self.get_book_recommendations(user))
            return f"Xin lỗi, tôi gặp lỗi: {str(e)}"
    
    def _get_mock_response(self, user_message, recommendations):
        """Mock response khi API hết quota"""
        user_msg_lower = user_message.lower()
        
        responses = {
            "mượn": f"📚 **Cách mượn sách chi tiết:**\n1️⃣ Tìm sách trên trang chủ\n2️⃣ Bấm nút 'Mượn sách'\n3️⃣  thời hạn (14 ngày)\n4️⃣ Xác nhận\n\nSách được gợi ý:\n{chr(10).join(recommendations[:3]) if recommendations else 'Khám phá sách ngay!'}",
            "đề xuất": f"📖 **Sách được gợi ý cho bạn:** \n{chr(10).join(recommendations[:5]) if recommendations else 'Hãy cho biết sở thích!'}",
            "trả": "🔄 **Cách trả sách:** Vào 'Lịch sử mượn' → Tìm sách → Bấm 'Trả sách' → Xác nhận",
            "phạt": "⚠️ **Quy định phạt:** Trả muộn 5.000đ/ngày. Kiểm tra hạn trả trong hồ sơ!",
            "tìm": "🔍 **Tìm sách:** Dùng ô tìm kiếm hoặc lọc theo danh mục ở trang chủ.",
            "có": f"✅ Tuyệt vời! Bạn muốn mượn loại sách nào? Gợi ý:\n{chr(10).join(recommendations[:3]) if recommendations else 'Văn học, Công nghệ, Kinh tế...'}",
            "được": f"👍 Bạn chọn danh mục nào? Gợi ý sách:\n{chr(10).join(recommendations[:3]) if recommendations else 'Khám phá sách!'}",
        }
        
        for key, response in responses.items():
            if key in user_msg_lower:
                return response
        
        return f"👋 Chào bạn! Mình giúp bạn:\n• 📚 Mượn sách\n• 📖 Tìm sách yêu thích\n• ✅ Giải đáp quy định\n\nBạn cần gì ạ? Gợi ý: {chr(10).join(recommendations[:2]) if recommendations else 'Sách đa dạng!'}"
