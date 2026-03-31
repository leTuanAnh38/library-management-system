// ==========================================
// FILE: core/static/js/auth_system.js
// Gộp toàn bộ logic xử lý Yêu cầu 3, 4, 5
// ==========================================

// ------------------------------------------
// 1. CẤU HÌNH AXIOS INTERCEPTOR (Yêu cầu 3)
// Tự động đính kèm Token vào mọi request gửi lên server
// ------------------------------------------
if (typeof axios !== 'undefined') {
    axios.interceptors.request.use(
        function (config) {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers['Authorization'] = 'Bearer ' + token;
            }
            return config;
        }, 
        function (error) {
            return Promise.reject(error);
        }
    );
}

// ------------------------------------------
// 2. HÀM BẢO VỆ TRANG (Yêu cầu 5 - Protected Route)
// Hàm này chỉ chạy khi chúng ta chủ động gọi nó
// ------------------------------------------
function requireLogin() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert('Hệ thống an ninh: Bạn cần đăng nhập để sử dụng chức năng này!');
        window.location.href = '/login/'; 
    }
}

// ------------------------------------------
// 3. LOGIC XỬ LÝ ĐĂNG NHẬP (Yêu cầu 4)
// Tự động nhận diện form đăng nhập để kích hoạt
// ------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    // Chỉ tìm form nằm trong class 'login-box' (class có sẵn trong login.html của bạn)
    const loginForm = document.querySelector('.login-box form');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const usernameInput = document.querySelector('input[name="username"]').value;
            const passwordInput = document.querySelector('input[name="password"]').value;

            axios.post('/api/login/', {
                username: usernameInput,
                password: passwordInput
            })
            .then(function (response) {
                // Cất thẻ vào két sắt localStorage
                localStorage.setItem('access_token', response.data.access);
                localStorage.setItem('refresh_token', response.data.refresh);
                
                alert('Đăng nhập thành công! Chào mừng trở lại Thư viện Alovu.');
                window.location.href = '/'; // Đẩy về trang chủ
            })
            .catch(function (error) {
                console.error('Lỗi đăng nhập:', error);
                alert('Sai tên đăng nhập hoặc mật khẩu. Vui lòng thử lại!');
            });
        });
    }
});