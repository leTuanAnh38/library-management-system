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
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def _get_user_status(self, user):
        """Lấy trạng thái thực tế của User"""
        active_borrows = BorrowTransaction.objects.filter(
            user=user, status__in=['PENDING', 'BORROWED', 'OVERDUE']
        ).count()
        fine = getattr(user, 'total_fine', 0)
        return {
            'active_borrows': active_borrows,
            'fine': fine,
            'can_borrow': active_borrows < 4 and fine == 0,
            'remaining_quota': max(0, 4 - active_borrows) # SỐ LƯỢNG SÁCH CÒN ĐƯỢC MƯỢN THÊM
        }

    def get_user_preferences(self, user):
        """Phân tích sở thích dựa trên lịch sử mượn"""
        borrows = BorrowTransaction.objects.filter(
            user=user, 
            status__in=['RETURNED', 'BORROWED', 'PENDING']
        ).select_related('book').values('book__category__name')[:15]
        
        categories = [b['book__category__name'] for b in borrows if b['book__category__name']]
        return list(set(categories))[:3]
    
    def get_dynamic_context(self, user, user_message):
        """Tự động rà soát database dựa trên câu chat của người dùng (Bao gồm xử lý sách Free)"""
        query = Book.objects.filter(status='AVAILABLE', quantity__gt=0).exclude(borrow_records__user=user)
        user_msg_lower = user_message.lower()

        # 1. Bắt từ khóa tìm sách Miễn phí / Free
        is_searching_free = "free" in user_msg_lower or "miễn phí" in user_msg_lower
        if is_searching_free:
            query = query.filter(Q(price=0) | Q(price__isnull=True))

        keywords = user_msg_lower.split()
        stop_words = ['có', 'sách', 'nào', 'về', 'không', 'tìm', 'cho', 'mình', 'cuốn', 'thể', 'loại', 'muốn', 'đọc', 'free', 'miễn', 'phí']
        search_terms = [w for w in keywords if w not in stop_words and len(w) > 2]
        
        # 2. Tìm kiếm đích danh theo từ khóa
        if search_terms:
            q_objects = Q()
            for term in search_terms:
                q_objects |= Q(title__icontains=term) | Q(author__icontains=term) | Q(category__name__icontains=term)
            
            searched_books = query.filter(q_objects).distinct()[:3]
            if searched_books.exists():
                return "Sách khớp với yêu cầu tìm kiếm của sinh viên:\n" + "\n".join(
                    [f"- {b.title} (Tác giả: {b.author or 'Đang cập nhật'} | {b.price if b.price and b.price > 0 else 'Miễn phí'})" for b in searched_books]
                )
        
        # 3. Lọc theo sở thích (nếu không chủ động tìm sách free)
        user_categories = self.get_user_preferences(user)
        if user_categories and not is_searching_free:
            query_pref = query.filter(category__name__in=user_categories)
            if query_pref.exists():
                query = query_pref
            
        query = query.annotate(borrow_count=Count('borrow_records')).order_by('-borrow_count')
        recs = [f"- {b.title} (Tác giả: {b.author or 'Đang cập nhật'} | {b.price if b.price and b.price > 0 else 'Miễn phí'})" for b in query[:3]]
        
        # 4. Luôn kẹp thêm 1-2 cuốn sách FREE vào cuối cùng để AI chủ động gợi ý (NẾU CHƯA TÌM)
        if not is_searching_free:
            free_books = Book.objects.filter(Q(price=0) | Q(price__isnull=True), status='AVAILABLE', quantity__gt=0).exclude(borrow_records__user=user).order_by('?')[:2]
            free_recs = [f"- {b.title} (Tác giả: {b.author or 'Đang cập nhật'} | Miễn phí)" for b in free_books]
            if free_recs:
                 return "Gợi ý sách hay thư viện đang có sẵn:\n" + "\n".join(recs) + "\n\nSách MIỄN PHÍ có thể gợi ý thêm:\n" + "\n".join(free_recs)

        return "Gợi ý sách hay thư viện đang có sẵn:\n" + "\n".join(recs) if recs else "Hiện thư viện đang cập nhật thêm sách mới."

    @rate_limit_gemini
    def chat(self, user_message, user, chat_history=None):
        """Xử lý chat thông minh với Context-Aware & Memory"""
        try:
            user_status = self._get_user_status(user)
            dynamic_books_info = self.get_dynamic_context(user, user_message)
            
            system_instruction = f"""Bạn là Alovu Assistant - Thủ thư AI xuất sắc và thân thiện của Thư viện Alovu.
            
QUY ĐỊNH THƯ VIỆN CHUẨN (TUYỆT ĐỐI TUÂN THỦ):
1. Mượn tối đa: 4 cuốn/người.
2. Thời hạn mượn: 14 ngày/cuốn.
3. Quy định trả trễ: Nếu sinh viên trả sách trễ hạn so với quy định 14 ngày, sẽ bị phạt tiền (5.000 VNĐ/ngày trễ) và bị trừ 5 điểm tích lũy.
4. Quy định mất sách/hỏng sách: Nếu sinh viên làm mất sách hoặc làm hỏng nặng không thể phục hồi, bắt buộc phải đền bù 100% số tiền gốc mua cuốn sách đó.
5. Quy trình mượn: Bấm 'MƯỢN SÁCH' (Sách có phí cần thanh toán tiền mặt/QR) -> Chờ Thủ thư duyệt.

HỒ SƠ CỦA SINH VIÊN ĐANG CHAT (BÁM SÁT THÔNG TIN NÀY):
- Số sách đang mượn/chờ duyệt: {user_status['active_borrows']}/4 cuốn.
- SỐ SÁCH CÒN CÓ THỂ MƯỢN THÊM LÀ: {user_status['remaining_quota']} cuốn.
- Tiền nợ phạt hiện tại: {user_status['fine']} VNĐ.
- Quyền mượn tiếp: {'ĐƯỢC PHÉP' if user_status['can_borrow'] else 'BỊ CHẶN (Phải trả sách hoặc đóng phạt trước khi mượn tiếp)'}.

DỮ LIỆU SÁCH TRONG KHO (Dùng để trả lời câu hỏi hiện tại):
{dynamic_books_info}

NGUYÊN TẮC GIAO TIẾP:
- TRẢ LỜI NGẮN GỌN (tối đa 3-4 câu). Trả lời thẳng vào câu hỏi của sinh viên.
- Chủ động giới thiệu các đầu sách "Miễn phí" nếu thấy phù hợp với ngữ cảnh.
- Nếu sinh viên hỏi "tôi có thể mượn bao nhiêu cuốn nữa", hãy trả lời chính xác là {user_status['remaining_quota']} cuốn dựa trên thông tin hồ sơ của họ.
- Nếu sinh viên hỏi về đền bù, trả trễ, hỏng sách: Cung cấp thông tin phạt trễ hoặc đền 100% giá trị sách như quy định thư viện.
- NẾU SINH VIÊN BỊ CHẶN QUYỀN MƯỢN: Lịch sự từ chối yêu cầu mượn và nhắc nhở số tiền nợ hoặc số sách cần trả.
- Xưng hô 'Mình - Bạn', dùng emoji thân thiện (📚, 💡, ⚠️, ✨).
"""
            # Nạp Lịch sử trò chuyện để Bot có trí nhớ
            contents = []
            if chat_history:
                for msg in chat_history:
                    # Đã sửa lỗi Part.from_text
                    contents.append(types.Content(role=msg['role'], parts=[types.Part.from_text(text=msg['text'])]))
            
            # Nạp câu hỏi mới nhất
            # Đã sửa lỗi Part.from_text
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            return self._get_mock_response(user_message, user)
            
    def _get_mock_response(self, user_message, user):
        """Hệ thống Trả lời Offline khi API lỗi hoặc hết hạn mức"""
        user_msg_lower = user_message.lower()
        user_status = self._get_user_status(user)
        remaining = user_status['remaining_quota']
        
        # Bắt từ khóa hỏi sách Free lúc Offline
        if any(word in user_msg_lower for word in ["free", "miễn phí"]):
            return "💡 Thư viện Alovu có rất nhiều sách Miễn phí (Free) nha! Bạn có thể vào mục 'Kho sách', chọn bộ lọc 'Sách Miễn phí' để xem toàn bộ nhé."

        if any(word in user_msg_lower for word in ["mượn thêm", "bao nhiêu cuốn"]):
            return f"📚 Theo hệ thống, bạn đang giữ {user_status['active_borrows']} cuốn. Bạn có thể mượn thêm tối đa {remaining} cuốn nữa nhé!"

        if any(word in user_msg_lower for word in ["mất sách", "đền", "bị mất", "làm mất"]):
            return "⚠️ Chào bạn, theo quy định nếu làm mất sách hoặc hỏng nặng, bạn sẽ phải đền 100% giá trị tiền gốc của cuốn sách đó. Bạn hãy ra quầy báo ngay cho Thủ thư để được hỗ trợ giải quyết nhé."

        if any(word in user_msg_lower for word in ["trễ", "muộn", "phạt"]):
            return "⚠️ Nếu trả sách trễ hạn 14 ngày, bạn sẽ bị phạt 5.000 VNĐ cho mỗi ngày trễ và bị trừ 5 điểm tích lũy. Nhớ trả sách đúng hạn để không bị khóa quyền mượn sách mới nha!"

        if any(word in user_msg_lower for word in ["mượn", "cách mượn"]):
            if not user_status['can_borrow']:
                return f"⚠️ Mình kiểm tra thấy bạn đang mượn {user_status['active_borrows']}/4 cuốn và nợ {user_status['fine']} VNĐ tiền phạt. Bạn cần hoàn tất các khoản này trước khi mượn thêm nhé!"
            return "📚 Rất dễ! Tìm sách ưng ý -> Bấm 'MƯỢN SÁCH' -> Xác nhận thanh toán (nếu có phí) -> Chờ Thủ thư duyệt."
            
        if any(word in user_msg_lower for word in ["gợi ý", "sách hay"]):
            return "💡 Bạn thử dạo một vòng trang chủ xem sao, hệ thống đang cập nhật rất nhiều đầu sách miễn phí và sách VIP mới đó! ✨"
            
        return "👋 Chào bạn! Trợ lý AI Alovu đây. Hệ thống đang hơi quá tải một chút do quá nhiều bạn sinh viên đang sử dụng, nhưng mình vẫn có thể giải đáp các quy định cơ bản. Bạn cần giúp gì nào? 😊"