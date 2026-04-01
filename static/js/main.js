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

$(document).ready(function() {

    /* =================================================================
       1. XỬ LÝ ẨN/HIỆN MÃ QR THANH TOÁN (EVENT DELEGATION)
       ================================================================= */
    $(document).on('change', '.radio-payment-toggle', function() {
        var bookId = $(this).data('book-id');
        var selectedValue = $(this).val();
        var modalBody = $(this).closest('.modal-body');
        
        // Xóa class highlight màu vàng
        modalBody.find('.payment-option').removeClass('selected-payment');
        $(this).closest('.payment-option').addClass('selected-payment');
        
        var qrBox = $('#qrCodeSection' + bookId);
        if (selectedValue === 'BANK') {
            qrBox.slideDown(300); // Trượt xuống mượt mà
        } else {
            qrBox.slideUp(300); // Kéo lên ẩn đi
        }
    });

    // Tự động gán lại Tiền Mặt khi tắt Modal
    $(document).on('hidden.bs.modal', '.payment-modal', function () {
        $(this).find('input[value="CASH"]').prop('checked', true).trigger('change');
    });


    /* =================================================================
       2. XỬ LÝ AJAX THẢ TIM (WISHLIST) KHÔNG LOAD LẠI TRANG
       ================================================================= */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Dùng $(document).on('click') để không bao giờ bị liệt nút
    $(document).on('click', '.btn-toggle-wishlist', function(e) {
        e.preventDefault(); // Ngăn load lại trang
        
        var btn = $(this);
        var url = btn.data('url');
        var bookId = btn.data('book-id');
        var icon = $('.heart-icon-' + bookId);
        const csrftoken = getCookie('csrftoken'); 
        
        $.ajax({
            type: 'POST',
            url: url,
            headers: {
                'X-CSRFToken': csrftoken 
            },
            success: function(response) {
                if (response.status === 'success') {
                    if (response.is_wished) {
                        // NẾU THẢ TIM: Đổi màu đỏ và nảy nhẹ
                        icon.removeClass('far').addClass('fas');
                        icon.css("transform", "scale(1.3)");
                        setTimeout(function() { icon.css("transform", "scale(1)"); }, 200);
                    } else {
                        // NẾU BỎ TIM: Đổi thành tim rỗng
                        icon.removeClass('fas').addClass('far');
                        
                        // [TÍNH NĂNG MỚI]: Xử lý riêng cho trang Wishlist
                        var wishlistCard = btn.closest('.wishlist-card-item');
                        
                        if (wishlistCard.length > 0) {
                            // Nếu đang ở trang Yêu thích -> Cho thẻ sách từ từ mờ đi và biến mất
                            wishlistCard.fadeOut(400, function() {
                                $(this).remove(); // Xóa hẳn khỏi màn hình
                                
                                // Nếu xóa hết sạch sách thì tự động load lại trang để hiện câu "Chưa có sách nào"
                                if ($('.wishlist-card-item').length === 0) {
                                    location.reload();
                                }
                            });
                        } else {
                            // Nếu ở trang khác (Trang chủ, Kho sách) thì chỉ cần nảy icon thôi
                            icon.css("transform", "scale(1.3)");
                            setTimeout(function() { icon.css("transform", "scale(1)"); }, 200);
                        }
                    }
                }
            },
            error: function(xhr, errmsg, err) {
                if (xhr.status == 403) {
                    alert("Bạn cần đăng nhập để lưu sách yêu thích nhé!");
                } else {
                    console.log("Lỗi: " + errmsg);
                }
            }
        });
    });

});

 document.addEventListener("DOMContentLoaded", function() {
        // 1. CHUYỂN ĐỔI CHẾ ĐỘ XEM/SỬA
        const btnToggle = document.getElementById('btn-edit-toggle');
        const btnCancel = document.getElementById('btn-cancel-edit');
        const viewSection = document.getElementById('profile-view-mode');
        const editSection = document.getElementById('profile-edit-mode');

        if (btnToggle && btnCancel && viewSection && editSection) {
            btnToggle.addEventListener('click', function() {
                viewSection.classList.add('d-none');
                editSection.classList.remove('d-none');
                btnToggle.classList.add('d-none');
            });

            btnCancel.addEventListener('click', function() {
                viewSection.classList.remove('d-none');
                editSection.classList.add('d-none');
                btnToggle.classList.remove('d-none');
            });
        }

        // 2. HIỂN THỊ MÃ QR THANH TOÁN
        const methodTransfer = document.getElementById('methodTransfer');
        const methodCounter = document.getElementById('methodCounter');
        const qrSection = document.getElementById('qr-section');

        if (methodTransfer && methodCounter && qrSection) {
            methodTransfer.addEventListener('change', function() {
                if (this.checked) {
                    qrSection.classList.remove('d-none');
                }
            });

            methodCounter.addEventListener('change', function() {
                if (this.checked) {
                    qrSection.classList.add('d-none');
                }
            });
        }
    });

/* =================================================================
       3. THANH TÌM KIẾM THÔNG MINH (LIVE SEARCH AUTOCOMPLETE)
       ================================================================= */
    let searchTimeout = null;

    $('#live-search-input').on('keyup', function() {
        // Hủy lệnh gọi cũ nếu người dùng vẫn đang gõ liên tục
        clearTimeout(searchTimeout); 
        
        var input = $(this);
        var query = input.val().trim();
        var apiUrl = input.data('url');
        var resultBox = $('#search-results-box');

        if (query.length > 0) {
            // Hiển thị chữ đang tìm kiếm (Tuỳ chọn)
            resultBox.html('<div class="p-3 text-center text-muted small"><i class="fas fa-spinner fa-spin me-2"></i>Đang tìm kiếm...</div>').slideDown(200);

            // Chờ 300ms sau khi ngừng gõ mới gọi API
            searchTimeout = setTimeout(function() {
                $.ajax({
                    url: apiUrl,
                    data: { 'q': query },
                    success: function(response) {
                        if (response.status === 'success' && response.data.length > 0) {
                            var html = '';
                            
                            // Duyệt qua từng cuốn sách API trả về và vẽ giao diện HTML
                            response.data.forEach(function(book) {
                                var priceTag = book.price > 0 ? `<span class="badge bg-danger ms-2" style="font-size: 0.7rem;">Có trả phí</span>` : '';
                                
                                html += `
                                    <a href="${book.url}" class="d-flex align-items-center p-2 border-bottom text-decoration-none hover-bg-light transition-hover" style="color: inherit;">
                                        <img src="${book.cover_image}" alt="${book.title}" style="width: 45px; height: 65px; object-fit: cover;" class="rounded shadow-sm me-3">
                                        <div class="overflow-hidden">
                                            <h6 class="mb-0 fw-bold text-truncate" style="font-size: 0.9rem;">${book.title} ${priceTag}</h6>
                                            <small class="text-muted text-truncate d-block" style="font-size: 0.8rem;"><i class="fas fa-pen-nib me-1"></i>${book.author}</small>
                                        </div>
                                    </a>
                                `;
                            });
                            
                            // Thêm nút Xem tất cả ở dưới cùng
                            html += `<a href="/books/?q=${query}" class="d-block text-center p-2 text-primary fw-bold text-decoration-none" style="background-color: #f8f9fa; font-size: 0.85rem;">Xem tất cả kết quả <i class="fas fa-arrow-right ms-1"></i></a>`;
                            
                            resultBox.html(html);
                        } else {
                            resultBox.html('<div class="p-3 text-center text-muted small"><i class="fas fa-search me-2"></i>Không tìm thấy sách nào khớp với từ khóa.</div>');
                        }
                    },
                    error: function() {
                        resultBox.html('<div class="p-3 text-center text-danger small">Có lỗi xảy ra khi tìm kiếm.</div>');
                    }
                });
            }, 300); // 300 milliseconds
        } else {
            // Nếu xóa trắng ô tìm kiếm thì ẩn hộp kết quả đi
            resultBox.slideUp(200);
        }
    });

    // Ẩn hộp kết quả khi người dùng click chuột ra ngoài vùng tìm kiếm
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-container').length) {
            $('#search-results-box').slideUp(200);
        }
    });

/* =================================================================
       4. GỬI ĐÁNH GIÁ (REVIEW) BẰNG AJAX
       ================================================================= */
    $('#reviewForm').on('submit', function(e) {
        e.preventDefault(); // Ngăn trình duyệt load lại trang
        
        var form = $(this);
        var url = form.data('url');
        var submitBtn = form.find('button[type="submit"]');
        var originalBtnText = submitBtn.html(); // Lưu lại chữ cũ của nút

        // Biến nút thành trạng thái "Đang gửi..."
        submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>Đang gửi...').prop('disabled', true);

        $.ajax({
            type: 'POST',
            url: url,
            data: form.serialize(), // Gom toàn bộ số sao và chữ trong form
            success: function(response) {
                if (response.status === 'success') {
                    // 1. Tạo HTML cho cái bình luận mới toanh vừa gửi
                    var newReviewHtml = `
                        <div class="new-review-item d-flex mb-4 p-3 bg-white rounded-4 shadow border-start border-success border-4" style="display: none;">
                            <div class="flex-shrink-0">
                                <img src="${response.review.avatar}" class="rounded-circle shadow-sm" style="width: 50px; height: 50px; object-fit: cover;">
                            </div>
                            <div class="ms-3 w-100">
                                <div class="d-flex justify-content-between align-items-start mb-1">
                                    <h6 class="fw-bold mb-0 text-dark">
                                        ${response.review.author}
                                        <span class="text-warning ms-2 small">${response.review.stars}</span>
                                    </h6>
                                    <small class="text-muted italic">${response.review.date}</small>
                                </div>
                                <p class="mt-2 text-secondary mb-0 small">${response.review.comment}</p>
                            </div>
                        </div>
                    `;

                    // 2. Thu nhỏ form lại và hiện lời cảm ơn
                    form.slideUp(400, function() {
                        var thankYouMsg = `
                            <div class="alert alert-success border-0 shadow-sm rounded-4 mb-5 d-flex align-items-center animate__animated animate__fadeIn">
                                <i class="fas fa-check-circle text-success fs-4 me-3"></i>
                                <span class="text-dark fw-medium">Bạn đã để lại đánh giá cho cuốn sách này rồi. Cảm ơn đóng góp của bạn!</span>
                            </div>`;
                        $(thankYouMsg).insertAfter(form);
                    });

                    // 3. Xóa dòng chữ "Chưa có nhận xét nào" (nếu đây là người đầu tiên)
                    $('.review-list .text-center.py-4').remove();

                    // 4. Nhét bình luận mới lên ĐẦU danh sách và cho nó trượt xuống từ từ
                    var newElement = $(newReviewHtml);
                    $('.review-list').prepend(newElement);
                    newElement.slideDown(500);

                } else {
                    alert(response.message);
                    submitBtn.html(originalBtnText).prop('disabled', false);
                }
            },
            error: function() {
                alert("Có lỗi xảy ra, không thể gửi nhận xét lúc này!");
                submitBtn.html(originalBtnText).prop('disabled', false);
            }
        });
    });


       
    // Hàm dùng chung để vẽ HTML từng cuốn sách (tránh lặp code)
    function renderBookHTML(book, is_premium) {
        var priceRibbon = book.price > 0 ? `<div class="position-absolute bg-danger text-white px-3 py-1 fw-bold" style="top: 15px; right: -5px; border-radius: 20px 0 0 20px; z-index: 2; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">${book.price} VNĐ</div>` : '';
        var stockHtml = book.quantity > 0 ? `<span class="text-success small fw-bold"><i class="fas fa-check-circle me-1"></i>Có sẵn: ${book.quantity} cuốn</span>` : `<span class="text-danger small fw-bold"><i class="fas fa-times-circle me-1"></i>Hết sách</span>`;
        
        var actionBtn = '';
        if (book.btn_status === 'PENDING') {
            actionBtn = `<button class="btn btn-warning text-dark rounded-pill fw-bold w-100 py-2 shadow-sm disabled" style="opacity: 0.85;"><i class="fas fa-clock me-1"></i>CHỜ DUYỆT</button>`;
        } else if (book.btn_status === 'BORROWED') {
            actionBtn = `<button class="btn btn-secondary rounded-pill fw-bold w-100 py-2 shadow-sm disabled">ĐANG MƯỢN</button>`;
        } else if (book.btn_status === 'OUT_OF_STOCK') {
            actionBtn = `<button class="btn btn-danger rounded-pill fw-bold w-100 py-2 shadow-sm disabled">HẾT SÁCH</button>`;
        } else if (book.btn_status === 'VIP') {
            actionBtn = `<a href="${book.url}" class="btn btn-warning w-100 fw-bold rounded-pill text-dark shadow-sm py-2"><i class="fas fa-crown me-1"></i> XEM SÁCH VIP</a>`;
        } else {
            actionBtn = `<a href="${book.borrow_url}" class="btn btn-primary rounded-pill fw-bold w-100 py-2 shadow-sm" onclick="return confirm('Bạn chắc chắn muốn mượn sách [${book.title}] này không?')">MƯỢN SÁCH</a>`;
        }

        var heartClass = book.is_wished ? 'fas' : 'far';
        var categoryHtml = (is_premium === true || is_premium === 'true') ? `<p class="small text-muted mb-2"><i class="fas fa-tags me-1"></i> Thể loại: ${book.category_name}</p>` : '';

        return `
            <div class="col-md-6 col-lg-4 d-flex align-items-stretch animate__animated animate__fadeInUp">
                <div class="product-item bg-white border rounded shadow-sm w-100 d-flex flex-column p-2 transition-hover position-relative">
                    ${priceRibbon}
                    <div class="text-center p-3 bg-light rounded" style="height: 200px; overflow: hidden;">
                        <a href="${book.url}"><img src="${book.cover_image}" class="h-100 rounded" style="object-fit: contain;"></a>
                    </div>
                    <div class="p-3 text-center d-flex flex-column flex-grow-1">
                        <h6 class="fw-bold text-dark text-truncate-2 mb-2"><a href="${book.url}" class="text-dark text-decoration-none">${book.title}</a></h6>
                        <p class="small text-muted mb-1">Tác giả: <b>${book.author}</b></p>
                        ${categoryHtml}
                        <div class="mb-3 mt-1">${stockHtml}</div>
                        <div class="mt-auto">${actionBtn}</div>
                        <div class="text-center mt-2">
                            <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none text-muted btn-toggle-wishlist" data-url="${book.wishlist_api_url}" data-book-id="${book.id}">
                                <i class="${heartClass} fa-heart text-danger fs-5 heart-icon-${book.id}"></i> Yêu thích
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // --- A. BẮT SỰ KIỆN KHI BẤM DANH MỤC Ở SIDEBAR MÀU CAM ---
    $('.ajax-category-link').click(function(e) {
        // Chỉ áp dụng AJAX nếu người dùng ĐANG Ở TRANG KHO SÁCH
        if ($('#category-filter').length > 0) {
            e.preventDefault(); // Ngăn trình duyệt chuyển trang
            
            var catId = $(this).data('category');
            // Cập nhật giá trị vào thanh Select Lọc và tự động kích hoạt lọc
            $('#category-filter').val(catId).trigger('change'); 
            
            // Đóng danh mục thả xuống (nếu đang xem trên điện thoại)
            if ($('#allCat').hasClass('show')) {
                $('#allCat').collapse('hide');
            }
        }
        // Nếu ở Trang chủ, cứ để thẻ <a> hoạt động bình thường (nó sẽ link tới kho sách)
    });

    // --- B. BẮT SỰ KIỆN KHI LỌC BẰNG THANH SELECT (SẮP XẾP & DANH MỤC) ---
    $('#sort-filter, #category-filter').change(function() {
        var category = $('#category-filter').val();
        var sort = $('#sort-filter').val();
        var query = $('input[name="q"]').val() || ''; 
        var is_premium = $('#btn-load-more').data('is-premium') || 'false';

        // Xóa sách cũ, hiện Loading quay quay
        $('#book-list-container').html('<div class="col-12 text-center py-5"><i class="fas fa-spinner fa-spin fa-3x text-primary mb-3"></i><p class="text-muted mt-2 fw-bold">Đang tìm sách cho bạn...</p></div>');

        $.ajax({
            url: '/api/books/load-more/',
            type: 'GET',
            data: { 'page': 1, 'q': query, 'category': category, 'sort': sort, 'is_premium': is_premium },
            success: function(response) {
                if (response.status === 'success') {
                    var html = '';
                    if (response.data.length > 0) {
                        response.data.forEach(function(book) { html += renderBookHTML(book, is_premium); });
                    } else {
                        html = `<div class="col-12 text-center py-5 animate__animated animate__fadeIn"><i class="fas fa-book-open fa-3x text-muted opacity-25 mb-3"></i><p class="text-muted">Không tìm thấy sách phù hợp.</p></div>`;
                    }
                    $('#book-list-container').html(html);

                    // Reset lại Nút Xem Thêm về trang 2 để bắt đầu cuộn tiếp
                    if (response.has_next) {
                        $('#btn-load-more').data('page', 2).data('category', category).data('sort', sort);
                        $('#load-more-section').fadeIn();
                    } else {
                        $('#load-more-section').fadeOut();
                    }
                }
            }
        });
    });

    // --- C. BẮT SỰ KIỆN NÚT LOAD MORE (DÙNG CHUNG HÀM RENDER) ---
    $('#btn-load-more').click(function() {
        var btn = $(this);
        var page = btn.data('page');
        var category = $('#category-filter').length ? $('#category-filter').val() : btn.data('category');
        var sort = $('#sort-filter').length ? $('#sort-filter').val() : btn.data('sort');
        var query = $('input[name="q"]').val() || btn.data('query');
        var is_premium = btn.data('is-premium') || 'false'; 
        
        var originalText = btn.html();
        btn.html('<i class="fas fa-spinner fa-spin me-2"></i>Đang tải...').prop('disabled', true);

        $.ajax({
            url: btn.data('url'),
            type: 'GET',
            data: { 'page': page, 'q': query, 'category': category, 'sort': sort, 'is_premium': is_premium },
            success: function(response) {
                if (response.status === 'success') {
                    var html = '';
                    response.data.forEach(function(book) { html += renderBookHTML(book, is_premium); });
                    $('#book-list-container').append(html);

                    if (response.has_next) {
                        btn.data('page', page + 1);
                        btn.html(originalText).prop('disabled', false);
                    } else {
                        $('#load-more-section').fadeOut();
                    }
                }
            }
        });
    });
/* =================================================================
       6. CẬP NHẬT THÔNG BÁO TỰ ĐỘNG (REAL-TIME POLLING)
       ================================================================= */
    function checkNewNotifications() {
        $.ajax({
            url: '/api/notifications/unread-count/', // Link API đã tạo ở Bước 1
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    var count = response.unread_count;
                    
                    // Cập nhật số ở Sidebar
                    if (count > 0) {
                        $('#unread-count-sidebar').text(count).show();
                        $('#unread-count-header').show(); // Hiện chấm đỏ ở Header
                    } else {
                        $('#unread-count-sidebar').hide();
                        $('#unread-count-header').hide();
                    }
                }
            }
        });
    }

    // Nếu user đã đăng nhập thì cứ 30 giây kiểm tra 1 lần
    if ($('#unread-count-sidebar').length > 0) {
        setInterval(checkNewNotifications, 30000); 
    }

/* =================================================================
       7. TỰ ĐỘNG TẢI THÊM KHI CUỘN TRANG (INFINITE SCROLL - THÔNG BÁO)
       ================================================================= */
    $(window).scroll(function() {
        var trigger = $('#scroll-trigger');
        
        // Nếu có thẻ trigger và vẫn còn trang tiếp theo
        if (trigger.length && trigger.data('has-next') === true) {
            
            // Tính toán: Nếu cuộn cách đáy màn hình 50px thì kích hoạt tải thêm
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 50) {
                
                // Chặn việc gọi API liên tục khi đang tải
                if (trigger.hasClass('loading')) return;
                trigger.addClass('loading');
                
                $('#loading-spinner').show(); // Hiện spinner quay quay

                $.ajax({
                    url: trigger.data('url'),
                    type: 'GET',
                    data: { 'page': trigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            
                            // Vẽ từng thông báo mới
                            response.data.forEach(function(n) {
                                var iconHtml = '';
                                if (n.type === 'REMINDER') iconHtml = '<i class="fas fa-clock text-warning fs-4"></i>';
                                else if (n.type === 'WARNING') iconHtml = '<i class="fas fa-exclamation-triangle text-danger fs-4"></i>';
                                else iconHtml = '<i class="fas fa-info-circle text-primary fs-4"></i>';
                                
                                var badgeHtml = n.status === 'UNREAD' ? '<span class="badge bg-primary rounded-circle p-1" style="width: 10px; height: 10px;"> </span>' : '';
                                var textClass = n.status === 'UNREAD' ? 'fw-bold text-dark' : 'text-muted';
                                var bgClass = n.status === 'UNREAD' ? 'bg-light border-primary' : 'border-secondary';

                                html += `
                                <div class="p-3 mb-3 rounded-3 border-start border-4 ${bgClass} animate__animated animate__fadeInUp" style="transition: 0.3s;">
                                    <div class="d-flex justify-content-between">
                                        <div class="d-flex align-items-start">
                                            <div class="me-3 mt-1">${iconHtml}</div>
                                            <div>
                                                <p class="mb-1 ${textClass}">${n.message}</p>
                                                <small class="text-muted"><i class="far fa-clock me-1"></i>${n.time_since}</small>
                                            </div>
                                        </div>
                                        ${badgeHtml}
                                    </div>
                                </div>`;
                            });

                            // Nối thông báo mới vào đuôi danh sách
                            $('#notification-container').append(html);

                            // Cập nhật trang tiếp theo
                            if (response.has_next) {
                                trigger.data('page', trigger.data('page') + 1);
                                trigger.removeClass('loading'); // Mở khóa để cuộn tiếp
                            } else {
                                trigger.data('has-next', false); // Hết thông báo thì khóa luôn
                            }
                            $('#loading-spinner').hide();
                        }
                    }
                });
            }
        }
    });

    /* =================================================================
       8. TỰ ĐỘNG TẢI THÊM LỊCH SỬ MƯỢN (INFINITE SCROLL - HISTORY)
       ================================================================= */
    $(window).scroll(function() {
        var trigger = $('#history-scroll-trigger');
        
        if (trigger.length && trigger.data('has-next') === true) {
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 50) {
                if (trigger.hasClass('loading')) return;
                trigger.addClass('loading');
                
                $('#history-loading-spinner').show();

                $.ajax({
                    url: trigger.data('url'),
                    type: 'GET',
                    data: { 'page': trigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            
                            response.data.forEach(function(item) {
                                // Xử lý cột trạng thái
                                var statusHtml = '';
                                if (item.status === 'RETURNED') {
                                    if (item.is_late) {
                                        statusHtml = `<span class="badge bg-danger px-3 py-2 rounded-pill shadow-sm">Trả trễ</span>
                                                      <div class="mt-1 small text-danger fw-bold"><i class="fas fa-hand-holding-usd me-1"></i>Phạt: ${item.penalty_amount} VNĐ</div>`;
                                    } else {
                                        statusHtml = `<span class="badge bg-success px-3 py-2 rounded-pill shadow-sm">Đã trả</span>`;
                                    }
                                } else if (item.status === 'BORROWED') {
                                    statusHtml = `<span class="badge bg-primary px-3 py-2 rounded-pill shadow-sm">Đang mượn</span>`;
                                } else if (item.status === 'PENDING') {
                                    statusHtml = `<span class="badge bg-warning text-dark px-3 py-2 rounded-pill shadow-sm">Đang chờ duyệt</span>`;
                                } else {
                                    statusHtml = `<span class="badge bg-dark px-3 py-2 rounded-pill shadow-sm">Quá hạn</span>`;
                                }

                                // Xử lý cột hành động
                                var actionHtml = '';
                                if (item.status === 'BORROWED') {
                                    actionHtml = `<a href="${item.return_url}" class="btn btn-warning btn-sm rounded-pill px-4 fw-bold shadow-sm text-white transition-hover" onclick="return confirm('Khanh chắc chắn muốn trả cuốn sách [${item.book_title}] này chứ?')">Trả sách</a>`;
                                } else if (item.status === 'PENDING') {
                                    actionHtml = `<button class="btn btn-secondary btn-sm rounded-pill px-3 fw-bold shadow-sm" disabled style="opacity: 0.7;"><i class="fas fa-clock me-1"></i>Chờ xác nhận...</button>`;
                                } else {
                                    actionHtml = `<span class="text-muted small"><i class="fas fa-check-double text-success me-1"></i>Xong</span>`;
                                }
                                
                                var dateColor = item.status === 'BORROWED' ? 'text-primary fw-bold' : '';

                                html += `
                                <tr class="animate__animated animate__fadeIn">
                                    <td class="ps-4">
                                        <div class="d-flex align-items-center">
                                            <img src="${item.cover_image}" alt="" style="width: 45px; height: 60px; object-fit: cover;" class="rounded me-3 border shadow-sm">
                                            <div>
                                                <div class="fw-bold text-dark">${item.book_title}</div>
                                                <small class="text-muted italic">Tác giả: ${item.book_author}</small>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="small">${item.borrow_date}</td>
                                    <td class="small"><span class="${dateColor}">${item.due_date}</span></td>
                                    <td class="small">${item.return_date}</td>
                                    <td>${statusHtml}</td>
                                    <td class="text-center">${actionHtml}</td>
                                </tr>`;
                            });

                            $('#history-container').append(html);

                            if (response.has_next) {
                                trigger.data('page', trigger.data('page') + 1);
                                trigger.removeClass('loading');
                            } else {
                                trigger.data('has-next', false);
                            }
                            $('#history-loading-spinner').hide();
                        }
                    }
                });
            }
        }
    });

/* =================================================================
       9. TỰ ĐỘNG TẢI THÊM SÁCH YÊU THÍCH (INFINITE SCROLL - WISHLIST)
       ================================================================= */
    $(window).scroll(function() {
        var trigger = $('#wishlist-scroll-trigger');
        
        if (trigger.length && trigger.data('has-next') === true) {
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 50) {
                if (trigger.hasClass('loading')) return;
                trigger.addClass('loading');
                
                $('#wishlist-loading-spinner').show();

                $.ajax({
                    url: trigger.data('url'),
                    type: 'GET',
                    data: { 'page': trigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            
                            // Sử dụng lại hàm renderBookHTML cực xịn của Kho Sách
                            response.data.forEach(function(book) {
                                html += renderBookHTML(book, false);
                            });

                            $('#wishlist-container').append(html);

                            if (response.has_next) {
                                trigger.data('page', trigger.data('page') + 1);
                                trigger.removeClass('loading');
                            } else {
                                trigger.data('has-next', false);
                            }
                            $('#wishlist-loading-spinner').hide();
                        }
                    }
                });
            }
        }
    });