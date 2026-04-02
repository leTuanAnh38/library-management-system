(function ($) {
    "use strict";

    // 1. Loading Spinner
    var spinner = function () {
        setTimeout(function () {
            if ($('#spinner').length > 0) {
                $('#spinner').removeClass('show');
            }
        }, 1);
    };
    spinner();
    
    // 2. Khởi tạo hiệu ứng WOW.js
    new WOW().init();

    // 3. Navbar cố định khi cuộn trang
    $(window).scroll(function () {
        if ($(this).scrollTop() > 45) {
            $('.nav-bar').addClass('sticky-top shadow-sm');
        } else {
            $('.nav-bar').removeClass('sticky-top shadow-sm');
        }
    });

    // 4. Banner Sách Nổi Bật (Header Carousel)
    // Đã gộp và tối ưu hiệu ứng "Center" để cuốn ở giữa to hơn
    $(".header-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1500,
        center: true,       // Giúp cuốn sách nằm giữa
        dots: false,
        loop: true,
        margin: 25,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsive: {
            0:{ items:1 },      // Màn hình nhỏ hiện 1 cuốn
            768:{ items:2 },    // Màn hình vừa hiện 2 cuốn
            992:{ items:3 }     // Màn hình lớn hiện 3 cuốn (cuốn giữa sẽ nổi bật nhất)
        }
    });

    // 5. Danh sách Sách (ProductList Carousel)
    $(".productList-carousel, .related-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 2000,
        dots: false,
        loop: true,
        margin: 25,
        nav : true,
        navText : [
            '<i class="fas fa-chevron-left"></i>',
            '<i class="fas fa-chevron-right"></i>'
        ],
        responsive: {
            0:{ items:1 },
            576:{ items:1 },
            768:{ items:2 },
            992:{ items:3 },
            1200:{ items:4 }
        }
    });

    // 6. Ảnh chi tiết sách (Single Product Carousel)
    $(".single-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1500,
        dots: true,
        dotsData: true,
        loop: true,
        items: 1,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ]
    });

    // 7. Nút tăng giảm số lượng (Nếu dùng cho số lượng mượn)
    $('.quantity button').on('click', function () {
        var button = $(this);
        var oldValue = button.parent().parent().find('input').val();
        var newVal;
        if (button.hasClass('btn-plus')) {
            newVal = parseFloat(oldValue) + 1;
        } else {
            newVal = (oldValue > 0) ? parseFloat(oldValue) - 1 : 0;
        }
        button.parent().parent().find('input').val(newVal);
    });

    // 8. Nút Cuộn lên đầu trang (Back to top)
    $(window).scroll(function () {
        if ($(this).scrollTop() > 300) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });

   
})(jQuery);
/* ==========================================
   QUẢN LÝ HỒ SƠ (PROFILE PAGE)
   ========================================== */
document.addEventListener('DOMContentLoaded', function() {
    // 1. Chuyển đổi giữa chế độ Xem và Sửa
    const btnEditToggle = document.getElementById('btn-edit-toggle');
    const btnCancelEdit = document.getElementById('btn-cancel-edit');
    const viewMode = document.getElementById('profile-view-mode');
    const editMode = document.getElementById('profile-edit-mode');

    if (btnEditToggle && btnCancelEdit && viewMode && editMode) {
        btnEditToggle.addEventListener('click', function() {
            viewMode.classList.add('d-none');
            editMode.classList.remove('d-none');
        });
        btnCancelEdit.addEventListener('click', function() {
            editMode.classList.add('d-none');
            viewMode.classList.remove('d-none');
            // Reset lại ảnh preview nếu hủy bỏ
            const viewImg = document.querySelector('#profile-view-mode img');
            const previewImg = document.getElementById('avatar-preview');
            if (viewImg && previewImg) {
                previewImg.src = viewImg.src;
            }
        });
    }

    // 2. Logic Xem trước Avatar
    const avatarInput = document.getElementById('avatar-upload');
    const avatarPreview = document.getElementById('avatar-preview');
    const profileForm = document.getElementById('profile-edit-mode');
    const btnSave = document.getElementById('btn-save-profile');

    if (avatarInput && avatarPreview) {
        avatarInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            
            if (file) {
                // Ràng buộc dung lượng tối đa 2MB
                if (file.size > 2 * 1024 * 1024) {
                    alert('Ảnh hơi nặng! Vui lòng chọn ảnh dưới 2MB nhé.');
                    this.value = ''; 
                    return;
                }

                // Dùng FileReader để đọc ảnh và gán vào thẻ img
                const reader = new FileReader();
                reader.onload = function(event) {
                    avatarPreview.src = event.target.result;
                }
                reader.readAsDataURL(file);
            }
        });
    }

    // 3. Logic Loading khi Submit form
    if (profileForm && btnSave) {
        profileForm.addEventListener('submit', function() {
            btnSave.disabled = true;
            const btnText = btnSave.querySelector('.btn-text');
            const spinner = btnSave.querySelector('.spinner-border');
            
            if (btnText) btnText.textContent = 'Đang tải lên...';
            if (spinner) spinner.classList.remove('d-none');
        });
    }
});

/* ==========================================
   XỬ LÝ ẢNH BÌA SÁCH (BOOK FORM)
   ========================================== */
document.addEventListener('DOMContentLoaded', function() {
    const coverFileInput = document.getElementById('cover-file-upload');
    const coverUrlInput = document.getElementById('cover-url-input');
    const bookCoverPreview = document.getElementById('avatar-preview');

    // 1. Khi chọn file từ máy tính
    if (coverFileInput && bookCoverPreview) {
        coverFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Kiểm tra dung lượng (Tối đa 2MB)
                if (file.size > 2 * 1024 * 1024) {
                    alert('Ảnh hơi nặng! Vui lòng chọn ảnh dưới 2MB nhé.');
                    this.value = ''; 
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(event) {
                    bookCoverPreview.src = event.target.result;
                }
                reader.readAsDataURL(file);
            } else {
                // Nếu người dùng nhấn "Hủy" chọn file, khôi phục lại ảnh từ link nếu có
                if (coverUrlInput && coverUrlInput.value) {
                    bookCoverPreview.src = coverUrlInput.value;
                } else {
                    bookCoverPreview.src = 'https://placehold.co/150x220?text=Bia+Sach';
                }
            }
        });
    }

    // 2. Khi dán link mạng
    if (coverUrlInput && bookCoverPreview) {
        coverUrlInput.addEventListener('input', function() {
            // Chỉ cập nhật từ link nếu người dùng CHƯA chọn file từ máy tính
            if (!coverFileInput || !coverFileInput.value) {
                if (this.value) {
                    bookCoverPreview.src = this.value;
                } else {
                    bookCoverPreview.src = 'https://placehold.co/150x220?text=Bia+Sach';
                }
            }
        });
    }
});