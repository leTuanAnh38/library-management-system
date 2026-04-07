import google.genai as genai
from google.genai import types
from django.conf import settings
from django.db.models import Q, Count
from core.models import Book, User, BorrowTransaction
import time
import logging

logger = logging.getLogger(__name__)

# Rate limiting decorator
def rate_limit_gemini(func):
    """Giới hạn 1 request mỗi 5 giây để tránh bị block API"""
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
        # Khởi tạo client Gemini mới nhất
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def _get_user_status(self, user):
        """Lấy trạng thái thực tế của User để Bot tư vấn chuẩn xác (ĐÂY LÀ ĐIỂM THÔNG MINH CỐT LÕI)"""
        active_borrows = BorrowTransaction.objects.filter(
            user=user, status__in=['PENDING', 'BORROWED', 'OVERDUE']
        ).count()
        fine = getattr(user, 'total_fine', 0)
        return {
            'active_borrows': active_borrows,
            'fine': fine,
            'can_borrow': active_borrows < 4 and fine == 0
        }

    def get_user_preferences(self, user):
        """Phân tích sở thích dựa trên lịch sử mượn"""
        borrows = BorrowTransaction.objects.filter(
            user=user, 
            status__in=['RETURNED', 'BORROWED', 'PENDING']
        ).select_related('book').values('book__category__name')[:15]
        
        categories = [b['book__category__name'] for b in borrows if b['book__category__name']]
        # Lấy các danh mục xuất hiện nhiều nhất
        return list(set(categories))[:3]
    
    def get_book_recommendations(self, user, category=None, limit=3):
        """Thuật toán gợi ý sách thông minh"""
        query = Book.objects.filter(status='AVAILABLE', quantity__gt=0).exclude(
            borrow_records__user=user
        )
        if category:
            query = query.filter(category__name__icontains=category)
        else:
            user_categories = self.get_user_preferences(user)
            if user_categories:
                query = query.filter(category__name__in=user_categories)
        
        # Lấy top sách mượn nhiều nhất trong nhóm gợi ý
        query = query.annotate(borrow_count=Count('borrow_records')).order_by('-borrow_count')
        
        return [f"- {b.title} (Tác giả: {b.author or 'Đang cập nhật'} | {b.price if b.price and b.price > 0 else 'Miễn phí'})" for b in query[:limit]]
    
    @rate_limit_gemini
    def chat(self, user_message, user):
        """Xử lý chat thông minh với Context-Aware"""
        try:
            # 1. Thu thập dữ liệu thời gian thực của sinh viên
            user_status = self._get_user_status(user)
            user_categories = self.get_user_preferences(user)
            recommendations = self.get_book_recommendations(user)
            
            # 2. Xây dựng System Instruction (Định hình nhân cách và luật lệ cho Bot)
            system_instruction = f"""Bạn là Alovu Assistant - Thủ thư AI thông minh, nhiệt tình của Thư viện Alovu.
            
QUY ĐỊNH THƯ VIỆN BẠN CẦN NẮM RÕ:
1. Mượn tối đa: 4 cuốn/người.
2. Quy trình mượn sách Miễn phí: Bấm 'MƯỢN SÁCH' -> Xác nhận Form -> Chờ Thủ thư duyệt. (Hệ thống chạy ngầm, không cần load lại trang).
3. Quy trình mượn sách VIP (Có phí): Bấm 'MƯỢN SÁCH' -> Chọn Tiền mặt hoặc Chuyển khoản (quét QR) -> Xác nhận -> Chờ duyệt.
4. Thời hạn mượn: 14 ngày mặc định. Phạt nếu trả muộn hoặc làm hỏng.

THÔNG TIN NGƯỜI DÙNG ĐANG CHAT VỚI BẠN:
- Đang mượn/chờ duyệt: {user_status['active_borrows']}/4 cuốn.
- Tiền phạt đang nợ: {user_status['fine']} VNĐ.
- Thể loại hay đọc: {', '.join(user_categories) if user_categories else 'Đang tìm hiểu'}
- Danh sách sách có thể gợi ý NGAY LẬP TỨC:
{chr(10).join(recommendations) if recommendations else 'Hiện chưa có sách phù hợp'}

NGUYÊN TẮC TRẢ LỜI (QUAN TRỌNG):
- TRẢ LỜI NGẮN GỌN (Tối đa 3-4 câu), ngôn ngữ TỰ NHIÊN, thân thiện như một người bạn (dùng xưng hô Mình - Bạn).
- Không lặp lại toàn bộ quy định nếu không được hỏi. Chỉ trả lời đúng trọng tâm câu hỏi.
- NẾU NGƯỜI DÙNG MUỐN MƯỢN SÁCH: Hãy kiểm tra thông tin của họ. Nếu họ nợ phạt (>0 VNĐ) hoặc đã mượn đủ 4 cuốn, hãy TỪ CHỐI KHÉO LÉO và nhắc họ thanh toán/trả sách.
- Nếu người dùng cảm ơn hoặc khen, hãy đáp lại vui vẻ và hỏi họ có cần tìm sách gì không.
- Thêm các Emoji phù hợp (📚, ✨, 😊, 💡).
"""
            # 3. Gọi Gemini API thế hệ mới (Sử dụng config để truyền System Instruction)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7, # Độ sáng tạo vừa phải, giữ tính logic không bị "ngáo"
                )
            )
            return response.text
            
        except Exception as e:
            # Ghi log lỗi vào server thay vì ném ra màn hình cho người dùng
            logger.error(f"Gemini API Error: {str(e)}")
            return self._get_mock_response(user_message, user)
            
    def _get_mock_response(self, user_message, user):
        """Hệ thống Trả lời Offline thông minh khi đứt cáp hoặc API Limit"""
        user_msg_lower = user_message.lower()
        user_status = self._get_user_status(user)
        
        if any(word in user_msg_lower for word in ["mượn", "cách mượn", "muon sach"]):
            if not user_status['can_borrow']:
                return f"⚠️ Mình kiểm tra thấy bạn đang mượn {user_status['active_borrows']}/4 cuốn và nợ {user_status['fine']} VNĐ tiền phạt. Bạn cần hoàn tất các khoản này trước khi mượn thêm sách nhé!"
            return "📚 Rất dễ! Bạn chỉ cần tìm sách ưng ý -> Bấm 'MƯỢN SÁCH' -> Chọn hình thức thanh toán (nếu là sách VIP) và Xác nhận. Hệ thống sẽ báo ngay cho Thủ thư duyệt."
            
        if any(word in user_msg_lower for word in ["gợi ý", "sách hay", "đề xuất"]):
            recs = self.get_book_recommendations(user)
            if recs:
                return f"💡 Mình nghĩ bạn sẽ thích những cuốn này đó:\n{chr(10).join(recs)}\nBạn ưng cuốn nào không?"
            return "Hiện tại kho sách đang cập nhật thêm, bạn dạo một vòng trang chủ xem sao nhé! ✨"
            
        if any(word in user_msg_lower for word in ["trả", "trả sách"]):
            return "🔄 Khi nào đọc xong, bạn chỉ cần mang sách đến quầy, Thủ thư sẽ quét mã và cập nhật hệ thống cho bạn trong 1 nốt nhạc!"
            
        if any(word in user_msg_lower for word in ["phạt", "đóng tiền"]):
            return "⚠️ Nếu trả muộn hoặc làm hỏng sách sẽ có phí phạt. Bạn có thể đóng tiền mặt trực tiếp tại quầy hoặc chuyển khoản QR cho Thủ thư nhé."
            
        return "👋 Chào bạn! Trợ lý AI Alovu đây. Mình có thể giúp bạn tìm sách, hướng dẫn mượn trả hoặc kiểm tra tình trạng tài khoản. Bạn cần mình giúp gì nào? 😊"