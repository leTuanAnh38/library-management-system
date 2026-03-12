from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .models import User, Book # Thêm Book vào đây

class CustomUserCreationForm(UserCreationForm):
    # Thêm các trường email, số điện thoại vào form đăng ký
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'first_name', 'last_name')

# --- THÊM PHẦN NÀY ĐỂ QUẢN LÝ SÁCH ---
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        # Các trường dữ liệu từ bảng BOOKS
        fields = [
            'title', 'category', 'publisher', 'author', 'cover_image', 
            'price', 'initial_quantity', 'quantity', 'published_year', 
            'location', 'description', 'status'
        ]
        
        # Gắn class Bootstrap để giao diện Thêm/Sửa sách đẹp hơn
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
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vị trí kệ sách'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }