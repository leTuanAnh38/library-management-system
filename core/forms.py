from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .models import User, Book,Category, Publisher # Thêm Book vào đây

class CustomUserCreationForm(UserCreationForm):
    # Thêm các trường email, số điện thoại vào form đăng ký
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'first_name', 'last_name')
# --- 2. FORM QUẢN LÝ DANH MỤC (MỚI) ---
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên danh mục'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả danh mục...'}),
        }

# --- 3. FORM QUẢN LÝ NHÀ XUẤT BẢN (ĐÃ SỬA LỖI EMAIL) ---
class PublisherForm(forms.ModelForm):
    class Meta:
        model = Publisher
        # Chỉ dùng name và address theo đúng Model của bạn
        fields = ['name', 'address'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên nhà xuất bản'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Địa chỉ trụ sở'}),
        }
# --- THÊM PHẦN NÀY ĐỂ QUẢN LÝ SÁCH ---
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        # 1. THÊM 3 trường mới (floor, shelf, area) vào danh sách fields
        fields = [
            'title', 'category', 'publisher', 'author', 'cover_image', 
            'price', 'initial_quantity', 'quantity', 'published_year', 
            'floor', 'shelf', 'area', 'location', 'description', 'status'
        ]
        
        # 2. Cấu hình Widgets để giao diện có class Bootstrap đẹp như Admin
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên sách'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên tác giả'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'publisher': forms.Select(attrs={'class': 'form-select'}),
            'cover_image': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dán link ảnh bìa'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'initial_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'published_year': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # --- BA TRƯỜNG VỊ TRÍ MỚI ---
            'floor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Tầng'}),
            'shelf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kệ sách'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Khu vực/Phòng'}),
            
            # Giữ lại location (nó sẽ bị ẩn ở giao diện HTML đã sửa trước đó)
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['avatar', 'msv', 'lop', 'dia_chi', 'first_name', 'last_name', 'email']
        widgets = {
            'dia_chi': forms.Textarea(attrs={'rows': 3}),
        }

