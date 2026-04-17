/* =================================================================
   CÁC HÀM TIỆN ÍCH DÙNG CHUNG (UTILITIES)
   ================================================================= */

// Global helper to read CSRF cookie (used by AJAX calls)
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

// Read CSRF token from meta tag, cookie, or any hidden input on page
function getCSRFToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) return meta.getAttribute('content');
    var cookie = getCookie('csrftoken');
    if (cookie) return cookie;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;
    return '';
}

// Bảo mật XSS: Làm sạch dữ liệu trước khi render ra HTML
function escapeHTML(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
}

// Tối ưu hiệu suất: Giới hạn tần suất gọi hàm (dùng cho cuộn trang)
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

/* =================================================================
   HÀM BỔ TRỢ QUẢN LÝ MODAL & THÔNG BÁO AJAX
   ================================================================= */

// 1. Hàm dọn dẹp Modal để tránh lỗi đen màn hình (Zombie backdrop)
function forceCloseModals() {
    $('.modal').modal('hide'); 
    $('.modal-backdrop').remove();
    $('body').removeClass('modal-open').css('padding-right', '');
}

// 2. Hàm hiển thị thông báo trắng nhỏ giữa màn hình (Dạng Modal)
function showSingleNotify(type, message) {
    forceCloseModals(); 

    var icon = type === 'success' 
        ? '<i class="fas fa-check-circle text-success" style="font-size: 3.5rem;"></i>' 
        : '<i class="fas fa-exclamation-triangle text-warning" style="font-size: 3.5rem;"></i>';
    
    var html = `
    <div class="modal fade" id="ajaxNotifyModal" tabindex="-1" data-bs-backdrop="static" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-sm">
            <div class="modal-content border-0 shadow-lg text-center p-4" style="border-radius: 20px;">
                <div class="mb-3 animate__animated animate__zoomIn">${icon}</div>
                <h6 class="fw-bold text-dark mb-4" style="line-height: 1.5;">${escapeHTML(message)}</h6>
                <button type="button" class="btn btn-primary rounded-pill fw-bold px-4 w-100" data-bs-dismiss="modal">Đã hiểu</button>
            </div>
        </div>
    </div>`;
    
    $('#ajaxNotifyModal').remove();
    $('body').append(html);
    
    var modalEl = document.getElementById('ajaxNotifyModal');
    var notifyModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    notifyModal.show();
}

/* =================================================================
   RENDER HTML SÁCH TRÀN VIỀN (AJAX - ĐỒNG BỘ MODERN DASHBOARD)
   ================================================================= */
function renderBookHTML(book, is_premium) {
    // Làm sạch dữ liệu đầu vào tránh XSS
    var safeTitle = escapeHTML(book.title);
    var safeAuthor = escapeHTML(book.author || 'Chưa rõ');
    var safePrice = escapeHTML(String(book.price));
    var safeCategory = escapeHTML(book.category_name || '');
    
    // 1. Nhãn giá tiền (Sách VIP)
    var priceRibbon = (book.price && book.price > 0) 
        ? `<div class="position-absolute bg-danger text-white px-3 py-1 fw-bold small" style="top: 15px; left: 0; border-radius: 0 20px 20px 0; z-index: 2; box-shadow: 2px 2px 10px rgba(220, 53, 69, 0.3);">${safePrice} VNĐ</div>` 
        : '';
    
    // 2. Trạng thái số lượng
    var stockHtml = book.quantity > 0 
        ? `<span class="text-success fw-bold"><i class="fas fa-check-circle me-1"></i>Có sẵn</span>` 
        : `<span class="text-danger fw-bold"><i class="fas fa-times-circle me-1"></i>Hết sách</span>`;
        
    var categoryHtml = safeCategory 
        ? `<span class="badge bg-light text-secondary border-0 px-2 py-1">${safeCategory}</span>` 
        : '';
    
    // 3. Nút mượn sách & Form Modal
    var actionBtn = '';
    var modalHtml = '';
    var csrfToken = getCSRFToken();
    var todayString = new Date().toISOString().split('T')[0];

    if (book.btn_status === 'PENDING') {
        actionBtn = `<button class="btn btn-warning text-dark rounded-pill fw-bold w-100 py-2 shadow-none disabled" style="opacity: 0.8;"><i class="fas fa-spinner fa-spin me-1"></i>CHỜ XÁC NHẬN</button>`;
    } else if (book.btn_status === 'BORROWED') {
        actionBtn = `<button class="btn btn-secondary rounded-pill fw-bold w-100 py-2 disabled shadow-none">ĐANG GIỮ SÁCH</button>`;
    } else if (book.btn_status === 'OUT_OF_STOCK' || book.quantity <= 0) {
        actionBtn = `<button class="btn btn-light border rounded-pill fw-bold w-100 py-2 disabled text-muted">TẠM HẾT</button>`;
    } else { 
        // TRƯỜNG HỢP CÒN SÁCH -> TẠO 2 NÚT & BẬT MODAL
        actionBtn = `
        <div class="d-flex gap-2">
            <button type="button" class="btn btn-outline-primary fw-bold rounded-pill shadow-sm py-2 btn-add-to-cart transition-hover w-50" data-url="/api/cart/add/${book.id}/" title="Thêm vào giỏ sách">
                <i class="fas fa-cart-plus"></i> Giỏ
            </button>
            <button type="button" class="btn btn-primary fw-bold rounded-pill text-white shadow-sm py-2 transition-hover w-50" data-bs-toggle="modal" data-bs-target="#borrowModal${book.id}" title="Mượn sách này ngay">
                Mượn ngay
            </button>
        </div>`;
        
        var paymentHtml = '';

        // Phân nhánh logic thanh toán nếu sách VIP
        if (book.price && book.price > 0) {
            paymentHtml = `
                <div class="mt-4 pt-4 border-top">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <span class="fw-bold text-dark">Phí dịch vụ:</span>
                        <span class="h5 fw-bold text-danger mb-0">${safePrice} VNĐ</span>
                    </div>
                    
                    <div class="payment-methods">
                        <div class="form-check p-0 mb-2">
                            <input class="btn-check" type="radio" name="payment_method" id="payCashJS${book.id}" value="CASH" checked onchange="document.getElementById('qrCodeSectionJS${book.id}').style.display='none'">
                            <label class="btn btn-outline-secondary border-dashed w-100 text-start p-3 rounded-3" for="payCashJS${book.id}">
                                <i class="fas fa-wallet me-2 text-success"></i> Tiền mặt tại quầy
                            </label>
                        </div>
                        <div class="form-check p-0">
                            <input class="btn-check" type="radio" name="payment_method" id="payBankJS${book.id}" value="BANK" onchange="document.getElementById('qrCodeSectionJS${book.id}').style.display='block'">
                            <label class="btn btn-outline-secondary border-dashed w-100 text-start p-3 rounded-3" for="payBankJS${book.id}">
                                <i class="fas fa-qrcode me-2 text-primary"></i> Chuyển khoản QR
                            </label>
                        </div>
                    </div>

                    <div id="qrCodeSectionJS${book.id}" class="mt-3 animate__animated animate__fadeIn" style="display: none;">
                        <div class="p-3 bg-light border border-primary rounded-3 text-center shadow-sm">
                            <p class="fw-bold text-dark mb-2">Quét mã MoMo/Ngân hàng</p>
                            <img src="/static/img/qr.png" alt="Mã QR Thanh Toán" class="img-fluid rounded border mb-2" style="max-width: 140px;">
                            <div class="small text-dark mt-2 bg-white p-2 rounded border border-dashed">
                                Nội dung chuyển khoản:<br>
                                <strong class="text-danger fs-6">Sách ${book.id} - Ghi rõ MSSV</strong>
                            </div>
                        </div>
                    </div>
                </div>`;
        } else {
            paymentHtml = `<input type="hidden" name="payment_method" value="FREE">`;
        }

        // Render toàn bộ Modal MỚI
        modalHtml = `
        <div class="modal fade borrow-modal" id="borrowModal${book.id}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg rounded-5 overflow-hidden">
                    <div class="modal-header border-0 p-4 pb-0">
                        <h5 class="modal-title fw-bold text-dark">
                            <i class="fas fa-calendar-alt text-primary me-2"></i>Lịch hẹn lấy sách
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>

                    <form method="POST" action="${book.borrow_url}">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        <div class="modal-body p-4">
                            <div class="mb-4 text-center">
                                <img src="${book.cover_image}" class="rounded-3 shadow-sm mb-3 border" style="width: 80px; height: 110px; object-fit: cover;">
                                <h6 class="fw-bold text-dark">${safeTitle}</h6>
                            </div>
                            
                            <div class="mb-4">
                                <label class="form-label small fw-bold text-muted text-uppercase">1. Chọn ngày đến quầy</label>
                                <div class="input-group shadow-sm rounded-3">
                                    <span class="input-group-text bg-white border-end-0 rounded-start-3"><i class="far fa-calendar-check text-primary"></i></span>
                                    <input type="date" name="pickup_date" class="form-control border-start-0 rounded-end-3 py-2" min="${todayString}" required>
                                </div>
                            </div>

                            <div class="mb-4">
                                <label class="form-label small fw-bold text-muted text-uppercase">2. Chọn buổi (Ca trực)</label>
                                <div class="row g-3">
                                    <div class="col-6">
                                        <input type="radio" class="btn-check" name="pickup_shift" id="shiftSangJS${book.id}" value="SANG" required>
                                        <label class="btn btn-outline-info w-100 py-3 rounded-4 border-2 d-flex flex-column align-items-center" for="shiftSangJS${book.id}">
                                            <i class="fas fa-sun mb-2 fs-4"></i>
                                            <span class="fw-bold">Ca Sáng</span>
                                            <small class="opacity-75">07:30 - 11:30</small>
                                        </label>
                                    </div>
                                    <div class="col-6">
                                        <input type="radio" class="btn-check" name="pickup_shift" id="shiftChieuJS${book.id}" value="CHIEU" required>
                                        <label class="btn btn-outline-warning w-100 py-3 rounded-4 border-2 d-flex flex-column align-items-center" for="shiftChieuJS${book.id}">
                                            <i class="fas fa-cloud-sun mb-2 fs-4"></i>
                                            <span class="fw-bold text-dark">Ca Chiều</span>
                                            <small class="text-dark opacity-75">13:00 - 17:00</small>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <div class="alert alert-warning border border-warning rounded-4 small mb-0 d-flex align-items-center bg-white text-dark shadow-sm">
                                <i class="fas fa-info-circle me-3 fs-5 text-warning"></i>
                                <span>Đơn sẽ <b>tự động hủy</b> nếu bạn không đến đúng ngày & ca đã chọn.</span>
                            </div>

                            ${paymentHtml}
                        </div>

                        <div class="modal-footer border-0 p-4 pt-0">
                            <button type="submit" class="btn btn-primary w-100 py-3 rounded-pill fw-bold shadow-lg transition-hover">
                                XÁC NHẬN ĐĂNG KÝ
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>`;
        
        // Xóa modal cũ (nếu có) và gắn cái mới vào <body>
        $('#borrowModal' + book.id).remove();
        $('body').append(modalHtml);
    }

    var heartClass = book.is_wished ? 'fas text-danger' : 'far text-muted';
    
    // TRẢ VỀ HTML THẺ SÁCH HOÀN CHỈNH
    return `
        <div class="col-md-6 col-lg-4 d-flex align-items-stretch animate__animated animate__fadeInUp">
            <div class="bg-white border-0 shadow-sm rounded-4 w-100 d-flex flex-column overflow-hidden position-relative transition-hover">
                
                ${priceRibbon}
                
                <div class="text-center bg-light" style="height: 260px; overflow: hidden;">
                    <a href="${book.url}" class="d-block h-100">
                        <img src="${book.cover_image}" class="h-100 w-100 transition-zoom" style="object-fit: cover; object-position: top;">
                    </a>
                </div>

                <div class="p-4 text-center d-flex flex-column flex-grow-1">
                    <h6 class="fw-bold text-dark text-truncate-2 mb-2" style="min-height: 44px;">
                        <a href="${book.url}" class="text-dark text-decoration-none hover-primary">${safeTitle}</a>
                    </h6>
                    
                    <div class="small text-muted mb-3">
                        <div class="mb-1"><i class="far fa-user me-1"></i> ${safeAuthor}</div>
                        ${categoryHtml}
                    </div>

                    <div class="d-flex justify-content-between align-items-center mb-4 mt-auto p-2 bg-light rounded-3">
                        <div class="small text-muted">Còn lại: <strong class="text-dark">${book.quantity}</strong></div>
                        <div class="small">${stockHtml}</div>
                    </div>
                    
                    <div class="w-100">${actionBtn}</div>
                    
                    <div class="mt-3">
                        <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none text-muted btn-toggle-wishlist" data-url="${book.wishlist_api_url}" data-book-id="${book.id}">
                            <i class="${heartClass} fa-heart fs-5 heart-icon-${book.id}"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
}

// Ensure jQuery AJAX sends CSRF token for unsafe HTTP methods
if (typeof $ !== 'undefined' && $.ajaxSetup) {
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                var token = getCSRFToken();
                if (token) xhr.setRequestHeader('X-CSRFToken', token);
            }
        }
    });
}
/* =================================================================
   CHƯƠNG TRÌNH CHÍNH (CHẠY KHI TRANG ĐÃ LOAD XONG)
   ================================================================= */
$(document).ready(function() {

    // Đảm bảo main có chiều cao tối thiểu
    function adjustMainMinHeight() {
        try {
            var header = document.querySelector('header');
            var footer = document.querySelector('footer.full-footer');
            var main = document.querySelector('main');
            if (!main) return;
            var hh = header ? header.offsetHeight : 0;
            var fh = footer ? footer.offsetHeight : 0;
            main.style.minHeight = 'calc(100vh - ' + (hh + fh) + 'px)';
        } catch (e) {
            // silent
        }
    }

    adjustMainMinHeight();
    $(window).on('resize', adjustMainMinHeight);

    function updateFloatingBar() {
        var count = $('.book-checkbox:checked').length;
        if (count > 0) {
            $('#selected-count').text(count);
            $('#floating-action-bar').fadeIn(200).css('display', 'block !important'); 
        } else {
            $('#floating-action-bar').fadeOut(200);
        }
    }
// Khi người dùng bấm vào từng Checkbox của sách
    $(document).on('change', '.book-checkbox', function() {
        updateFloatingBar();
        // Cập nhật trạng thái của nút "Chọn tất cả"
        var allBoxes = $('.book-checkbox:not(:disabled)').length;
        var checkedBoxes = $('.book-checkbox:checked').length;
        if ($('#selectAll').length) {
            $('#selectAll').prop('checked', allBoxes > 0 && allBoxes === checkedBoxes);
        }
    });

    // Khi người dùng bấm vào nút "Chọn tất cả"
    $(document).on('change', '#selectAll', function() {
        var isChecked = $(this).is(':checked');
        $('.book-checkbox:not(:disabled)').prop('checked', isChecked);
        updateFloatingBar();
    });

    // =================================================================
    // HÀM TẠO POPUP XÁC NHẬN SIÊU ĐẸP (Thay thế confirm mặc định)
    // =================================================================
    function showBeautifulConfirm(message, callback) {
        $('#beautifulConfirmModal').remove(); 
        let html = `
        <div class="modal fade" id="beautifulConfirmModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow text-center p-4" style="border-radius: 20px;">
                    <div class="mb-3"><i class="fas fa-question-circle text-primary" style="font-size: 3.5rem;"></i></div>
                    <h6 class="fw-bold text-dark mb-4">${message}</h6>
                    <div class="d-flex justify-content-center gap-2">
                        <button type="button" class="btn btn-light rounded-pill px-4" data-bs-dismiss="modal">Hủy</button>
                        <button type="button" class="btn btn-primary text-white rounded-pill px-4 fw-bold" id="btn-beautiful-yes">Xác nhận</button>
                    </div>
                </div>
            </div>
        </div>`;
        $('body').append(html);
        let modal = new bootstrap.Modal(document.getElementById('beautifulConfirmModal'));
        modal.show();
        
        // Khi bấm xác nhận thì mới chạy hành động tiếp theo
        $('#btn-beautiful-yes').off('click').on('click', function() {
            modal.hide();
            callback();
        });
    }

    // =================================================================
    // Bắt sự kiện khi bấm nút Trả sách hàng loạt (ĐÃ SỬA THÀNH MODAL ĐẸP)
    // =================================================================
    $(document).on('submit', '#batchReturnForm', function(e) {
        e.preventDefault(); // CHẶN form tự động gửi đi ngay lập tức
        var form = this;
        var count = $('.book-checkbox:checked').length;
        
        // 1. Thay thế alert() bằng hàm thông báo vàng có sẵn của bạn
        if (count === 0) {
            showSingleNotify('warning', 'Vui lòng chọn ít nhất 1 cuốn sách!');
            return false;
        }
        
        // 2. Thay thế confirm() bằng Popup bo tròn sang trọng
        showBeautifulConfirm(`Bạn có chắc chắn muốn gửi yêu cầu báo trả ${count} cuốn sách đã chọn không?`, function() {
            form.submit(); // Khi người dùng bấm nút "Xác nhận" màu xanh thì mới thực sự gửi form
        });
    });
    // =======================================================
    // KẾT THÚC ĐOẠN CODE CHECKBOX
    // =======================================================

    // 1. CHUYỂN ĐỔI CHẾ ĐỘ XEM/SỬA PROFILE
    $('#btn-edit-toggle').on('click', function() {
        $('#profile-view-mode').addClass('d-none');
        $('#profile-edit-mode').removeClass('d-none');
        $(this).addClass('d-none');
    });

    $('#btn-cancel-edit').on('click', function() {
        $('#profile-view-mode').removeClass('d-none');
        $('#profile-edit-mode').addClass('d-none');
        $('#btn-edit-toggle').removeClass('d-none');
    });

    // 2. HIỂN THỊ MÃ QR THANH TOÁN (PROFILE / TẠI QUẦY)
    $('#methodTransfer').on('change', function() {
        if ($(this).is(':checked')) $('#qr-section').removeClass('d-none');
    });

    $('#methodCounter').on('change', function() {
        if ($(this).is(':checked')) $('#qr-section').addClass('d-none');
    });

    // 3. XỬ LÝ ẨN/HIỆN MÃ QR THANH TOÁN (MODAL MƯỢN SÁCH)
    $(document).on('change', '.radio-payment-toggle', function() {
        var bookId = $(this).data('book-id');
        var selectedValue = $(this).val();
        var modalBody = $(this).closest('.modal-body');
        
        modalBody.find('.payment-option').removeClass('selected-payment');
        $(this).closest('.payment-option').addClass('selected-payment');
        
        var qrBox = $('#qrCodeSection' + bookId);
        if (selectedValue === 'BANK') {
            qrBox.slideDown(300);
        } else {
            qrBox.slideUp(300);
        }
    });

    $(document).on('hidden.bs.modal', '.payment-modal', function () {
        $(this).find('input[value="CASH"]').prop('checked', true).trigger('change');
    });

    // 4. XỬ LÝ AJAX THẢ TIM (WISHLIST)
    $(document).on('click', '.btn-toggle-wishlist', function(e) {
        e.preventDefault(); 
        var btn = $(this);
        var url = btn.data('url');
        var bookId = btn.data('book-id');
        var icon = $('.heart-icon-' + bookId);
        
        $.ajax({
            type: 'POST',
            url: url,
            success: function(response) {
                if (response.status === 'success') {
                    if (response.is_wished) {
                        icon.removeClass('far').addClass('fas').css("transform", "scale(1.3)");
                        setTimeout(function() { icon.css("transform", "scale(1)"); }, 200);
                    } else {
                        icon.removeClass('fas').addClass('far');
                        var wishlistCard = btn.closest('.wishlist-card-item');
                        
                        if (wishlistCard.length > 0) {
                            wishlistCard.fadeOut(400, function() {
                                $(this).remove();
                                if ($('.wishlist-card-item').length === 0) location.reload();
                            });
                        } else {
                            icon.css("transform", "scale(1.3)");
                            setTimeout(function() { icon.css("transform", "scale(1)"); }, 200);
                        }
                    }
                }
            },
            error: function(xhr, errmsg) {
                if (xhr.status == 403) {
                    alert("Bạn cần đăng nhập để lưu sách yêu thích nhé!");
                } else {
                    console.log("Lỗi: " + errmsg);
                }
            }
        });
    });

    // 5. THANH TÌM KIẾM THÔNG MINH (LIVE SEARCH)
    let liveSearchTimeout = null;
    $('#live-search-input').on('input', function() {
        clearTimeout(liveSearchTimeout); 
        var input = $(this);
        var query = input.val().trim();
        var apiUrl = input.data('url'); 
        var resultBox = $('#search-results-box');

        if (query.length > 0) {
            resultBox.html('<div class="p-3 text-center text-muted small"><i class="fas fa-spinner fa-spin me-2 text-primary"></i>Đang tìm kiếm...</div>').stop(true, true).slideDown(200);

            liveSearchTimeout = setTimeout(function() {
                $.ajax({
                    url: apiUrl,
                    data: { 'q': query },
                    success: function(response) {
                        if (response.status === 'success' && response.data && response.data.length > 0) {
                            var html = '';
                            response.data.forEach(function(book) {
                                var priceTag = book.price > 0 ? `<span class="badge bg-danger ms-2" style="font-size: 0.65rem;">Có phí</span>` : '';
                                var safeTitle = escapeHTML(book.title);
                                var safeAuthor = escapeHTML(book.author || 'Chưa rõ');
                                
                                html += `
                                    <a href="${book.url}" class="d-flex align-items-center p-2 border-bottom text-decoration-none transition-hover" style="color: inherit; background-color: #fff;" onmouseover="this.style.backgroundColor='#f8f9fa'" onmouseout="this.style.backgroundColor='#fff'">
                                        <img src="${book.cover_image}" alt="${safeTitle}" style="width: 40px; height: 60px; object-fit: cover;" class="rounded shadow-sm me-3">
                                        <div class="overflow-hidden">
                                            <h6 class="mb-1 fw-bold text-truncate text-dark" style="font-size: 0.9rem;">${safeTitle} ${priceTag}</h6>
                                            <small class="text-muted text-truncate d-block" style="font-size: 0.8rem;"><i class="fas fa-pen-nib me-1"></i>${safeAuthor}</small>
                                        </div>
                                    </a>`;
                            });
                            
                            html += `<a href="/books/?q=${encodeURIComponent(query)}" class="d-block text-center p-2 text-primary fw-bold text-decoration-none" style="background-color: #f0f4f8; font-size: 0.85rem; transition: 0.3s;" onmouseover="this.style.backgroundColor='#e2e6ea'" onmouseout="this.style.backgroundColor='#f0f4f8'">Xem tất cả kết quả <i class="fas fa-arrow-right ms-1"></i></a>`;
                            resultBox.html(html);
                        } else {
                            resultBox.html(`<div class="p-3 text-center text-muted small"><i class="fas fa-search-minus me-2 fs-5 mb-2 d-block text-secondary"></i>Không tìm thấy sách cho "${escapeHTML(query)}"</div>`);
                        }
                    },
                    error: function() {
                        resultBox.html('<div class="p-3 text-center text-danger small"><i class="fas fa-exclamation-circle me-1"></i>Lỗi kết nối máy chủ.</div>');
                    }
                });
            }, 400); 
        } else {
            resultBox.stop(true, true).slideUp(200);
        }
    });

    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-container, #live-search-input, #search-results-box').length) {
            $('#search-results-box').slideUp(200);
        }
    });

    $('#live-search-input').on('focus', function() {
        if ($(this).val().trim().length > 0 && $('#search-results-box').html().trim().length > 0) {
            $('#search-results-box').stop(true, true).slideDown(200);
        }
    });

    // 6. GỬI ĐÁNH GIÁ (REVIEW) BẰNG AJAX
    $('#reviewForm').on('submit', function(e) {
        e.preventDefault(); 
        var form = $(this);
        var url = form.data('url');
        var submitBtn = form.find('button[type="submit"]');
        var originalBtnText = submitBtn.html(); 

        submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>Đang gửi...').prop('disabled', true);

        $.ajax({
            type: 'POST',
            url: url,
            data: form.serialize(),
            success: function(response) {
                if (response.status === 'success') {
                    var safeAuthor = escapeHTML(response.review.author);
                    var safeComment = escapeHTML(response.review.comment);
                    
                    var newReviewHtml = `
                        <div class="new-review-item d-flex mb-4 p-3 bg-white rounded-4 shadow border-start border-success border-4" style="display: none;">
                            <div class="flex-shrink-0">
                                <img src="${response.review.avatar}" class="rounded-circle shadow-sm" style="width: 50px; height: 50px; object-fit: cover;">
                            </div>
                            <div class="ms-3 w-100">
                                <div class="d-flex justify-content-between align-items-start mb-1">
                                    <h6 class="fw-bold mb-0 text-dark">
                                        ${safeAuthor} <span class="text-warning ms-2 small">${response.review.stars}</span>
                                    </h6>
                                    <small class="text-muted italic">${response.review.date}</small>
                                </div>
                                <p class="mt-2 text-secondary mb-0 small">${safeComment}</p>
                            </div>
                        </div>`;

                    form.slideUp(400, function() {
                        var thankYouMsg = `
                            <div class="alert alert-success border-0 shadow-sm rounded-4 mb-5 d-flex align-items-center animate__animated animate__fadeIn">
                                <i class="fas fa-check-circle text-success fs-4 me-3"></i>
                                <span class="text-dark fw-medium">Bạn đã để lại đánh giá cho cuốn sách này rồi. Cảm ơn đóng góp của bạn!</span>
                            </div>`;
                        $(thankYouMsg).insertAfter(form);
                    });

                    $('.review-list .text-center.py-4').remove();
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

   // 7. LỌC, SẮP XẾP VÀ TÌM KIẾM (ĐỒNG BỘ URL & DEBOUNCE)
    $('.ajax-category-link').click(function(e) {
        if ($('#category-filter').length > 0) {
            e.preventDefault(); 
            $('#category-filter').val($(this).data('category')).trigger('change'); 
            if ($('#allCat').hasClass('show')) $('#allCat').collapse('hide');
        }
    });

    var filterTimeout; // Biến dùng để đếm giờ cho Debounce

    // Hàm xử lý chung cho mọi thao tác Lọc/Sắp xếp/Tìm kiếm
    function applyFilters() {
        var category = $('#category-filter').length ? $('#category-filter').val() : '';
        var sort = $('#sort-filter').length ? $('#sort-filter').val() : 'newest';
        var query = $('input[name="q"]').val() || ''; 
        var is_premium = $('#btn-load-more').data('is-premium') || 'false';

        // 🔥 TÍNH NĂNG 1: ĐỒNG BỘ URL (Task 7.2.5)
        var newUrl = new URL(window.location.href);
        if (query) newUrl.searchParams.set('q', query); else newUrl.searchParams.delete('q');
        if (category) newUrl.searchParams.set('category', category); else newUrl.searchParams.delete('category');
        if (sort && sort !== 'newest') newUrl.searchParams.set('sort', sort); else newUrl.searchParams.delete('sort');
        window.history.pushState({path: newUrl.href}, '', newUrl.href);

        // Bật Loading
        $('#book-list-container').html('<div class="col-12 text-center py-5"><i class="fas fa-spinner fa-spin fa-3x text-primary mb-3"></i><p class="text-muted mt-2 fw-bold">Đang tìm sách cho bạn...</p></div>');

        // Gọi API
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

                    // Giữ lại hàm này để khung màn hình không bị giật (nhảy footer) khi thay đổi dữ liệu
                    if (typeof adjustMainMinHeight === 'function') adjustMainMinHeight();

                    // Cập nhật lại nút Load More với dữ liệu mới
                    if (response.has_next) {
                        $('#btn-load-more').data('page', 2).data('category', category).data('sort', sort).data('query', query);
                        $('#btn-load-more').html('<i class="fas fa-arrow-down me-2"></i>Xem thêm sách').prop('disabled', false);
                        $('#load-more-section').fadeIn();
                    } else {
                        $('#load-more-section').fadeOut();
                    }
                }
            },
            error: function(xhr) {
                $('#book-list-container').html(`<div class="col-12 text-center py-5 text-danger"><i class="fas fa-exclamation-triangle fa-3x mb-3"></i><p class="fw-bold">Lỗi kết nối. Vui lòng tải lại trang!</p></div>`);
            }
        });
    }

    // Lắng nghe thay đổi ở Select Box (Danh mục & Sắp xếp)
    $('#sort-filter, #category-filter').change(function() {
        applyFilters();
    });

    // 🔥 TÍNH NĂNG 2: TÌM KIẾM VỚI DEBOUNCE (Task 7.1.3 & 7.2.2)
    $('input[name="q"]').on('input', function(e) {
        // Nếu người dùng đang gõ liên tục -> Xóa cái hẹn giờ cũ đi (Không gọi API)
        clearTimeout(filterTimeout);
        
        // Đặt lại hẹn giờ: Chỉ khi người dùng DỪNG GÕ đúng 500ms (0.5 giây) thì mới gọi API
        filterTimeout = setTimeout(function() {
            applyFilters();
        }, 500); 
    });

    // Chặn hành vi bấm Enter (làm tải lại trang) ở ô tìm kiếm
    $('form:has(input[name="q"])').on('submit', function(e) {
        e.preventDefault(); 
        clearTimeout(filterTimeout); // Xóa đếm ngược
        applyFilters(); // Tìm ngay lập tức
    });

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
                    if (!response.data || response.data.length === 0) {
                        $('#load-more-section').fadeOut();
                        return;
                    }
                    var html = '';
                    response.data.forEach(function(book) { html += renderBookHTML(book, is_premium); });
                    $('#book-list-container').append(html);
                    adjustMainMinHeight();

                    if (response.has_next) {
                        btn.data('page', page + 1);
                    } else {
                        $('#load-more-section').fadeOut();
                    }
                }
            },
            complete: function() {
                if (btn.prop('disabled')) btn.prop('disabled', false).html(originalText);
            },
            error: function() {
                alert('Có lỗi xảy ra khi tải thêm sách. Hãy kiểm tra kết nối mạng!');
            }
        });
    });

    // 8. CẬP NHẬT THÔNG BÁO TỰ ĐỘNG
    function checkNewNotifications() {
        $.ajax({
            url: '/api/notifications/unread-count/', 
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    if (response.unread_count > 0) {
                        $('#unread-count-sidebar').text(response.unread_count).show();
                        $('#unread-count-header').show(); 
                    } else {
                        $('#unread-count-sidebar').hide();
                        $('#unread-count-header').hide();
                    }
                }
            }
        });
    }

    if ($('#unread-count-sidebar').length > 0) {
        setInterval(checkNewNotifications, 30000); 
    }
    
    // 9. INFINITE SCROLL (THÔNG BÁO, LỊCH SỬ, YÊU THÍCH)
    // Bỏ hàm throttle để tránh lỗi "hụt nhịp" ở đáy trang
    $(window).scroll(function() {
        // A. Cuộn Thông Báo
        var notifTrigger = $('#scroll-trigger');
        if (notifTrigger.length && notifTrigger.data('has-next') === true) {
            // Tăng từ 50 lên 300 để load trước khi người dùng chạm hẳn đáy
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 300) {
                if (notifTrigger.hasClass('loading')) return;
                notifTrigger.addClass('loading');
                $('#loading-spinner').show();

                $.ajax({
                    url: notifTrigger.data('url'),
                    type: 'GET',
                    data: { 'page': notifTrigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            response.data.forEach(function(n) {
                                var iconHtml = n.type === 'REMINDER' ? '<i class="fas fa-clock text-warning fs-4"></i>' :
                                               n.type === 'WARNING' ? '<i class="fas fa-exclamation-triangle text-danger fs-4"></i>' :
                                               '<i class="fas fa-info-circle text-primary fs-4"></i>';
                                var badgeHtml = n.status === 'UNREAD' ? '<span class="badge bg-primary rounded-circle p-1" style="width: 10px; height: 10px;"> </span>' : '';
                                var textClass = n.status === 'UNREAD' ? 'fw-bold text-dark' : 'text-muted';
                                var bgClass = n.status === 'UNREAD' ? 'bg-light border-primary' : 'border-secondary';

                                html += `
                                <div class="p-3 mb-3 rounded-3 border-start border-4 ${bgClass} animate__animated animate__fadeInUp" style="transition: 0.3s;">
                                    <div class="d-flex justify-content-between">
                                        <div class="d-flex align-items-start">
                                            <div class="me-3 mt-1">${iconHtml}</div>
                                            <div>
                                                <p class="mb-1 ${textClass}">${escapeHTML(n.message)}</p>
                                                <small class="text-muted"><i class="far fa-clock me-1"></i>${n.time_since}</small>
                                            </div>
                                        </div>
                                        ${badgeHtml}
                                    </div>
                                </div>`;
                            });
                            $('#notification-container').append(html);
                            
                            if (response.has_next) {
                                notifTrigger.data('page', notifTrigger.data('page') + 1).removeClass('loading');
                            } else {
                                notifTrigger.data('has-next', false);
                            }
                            $('#loading-spinner').hide();
                            adjustMainMinHeight();
                        }
                    }
                });
            }
        }

// B. Cuộn Lịch Sử Mượn (Đã đồng bộ giao diện Minimal Dashboard)
        var histTrigger = $('#history-scroll-trigger');
        if (histTrigger.length && histTrigger.data('has-next') === true) {
            // Không được dùng $(window).on('scroll') ở đây nữa vì đã nằm trong $(window).scroll rồi
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 300) {
                if (histTrigger.hasClass('loading') || histTrigger.data('has-next') === false) return;
                histTrigger.addClass('loading');
                $('#history-loading-spinner').show();

                $.ajax({
                    url: histTrigger.data('url'),
                    type: 'GET',
                    data: { 'page': histTrigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            response.data.forEach(function(item) {
                                var safeTitle = escapeHTML(item.book_title);
                                var safeAuthor = escapeHTML(item.book_author || 'Chưa rõ');
                                
                                // Lấy ID giao dịch từ return_url để bỏ vào value của Checkbox
                                var cbValue = item.return_url ? item.return_url.split('/').filter(Boolean).pop() : ''; 
                                var checkboxHtml = (item.status === 'BORROWED' || item.status === 'OVERDUE') 
                                    ? `<input class="form-check-input book-checkbox" type="checkbox" name="transaction_ids" value="${cbValue}" style="transform: scale(1.3); cursor: pointer;">`
                                    : `<input class="form-check-input" type="checkbox" disabled style="opacity: 0.3; transform: scale(1.3);">`;

                                var statusHtml = '';
                                var actionHtml = '';
                                
                                if (item.status === 'RETURNED') {
                                    if (item.is_late) {
                                        statusHtml = `<span class="badge bg-white border border-danger text-danger px-3 py-1 rounded-pill">Trả trễ</span>
                                                      <div class="mt-1 small text-danger fw-bold" style="font-size: 0.75rem;"><i class="fas fa-file-invoice-dollar me-1"></i>Phạt: ${item.penalty_amount}đ</div>`;
                                    } else {
                                        statusHtml = `<span class="badge bg-white border border-success text-success px-3 py-1 rounded-pill">Đã trả</span>`;
                                    }
                                } else if (item.status === 'BORROWED') {
                                    statusHtml = `<span class="badge bg-white border border-primary text-primary px-3 py-1 rounded-pill">Đang mượn</span>`;
                                } else if (item.status === 'PENDING') {
                                    statusHtml = `<span class="badge bg-white border border-warning text-warning px-3 py-1 rounded-pill">Chờ duyệt</span>`;
                                } else if (item.status === 'CANCELLED') {
                                    // Xác định ca trực từ API (nếu API của bạn trả về trường pickup_shift)
                                var shiftText = (item.pickup_shift === 'SANG') ? 'Sáng' : 'Chiều';
                                
                                statusHtml = `<span class="badge bg-light text-secondary border px-3 py-1 rounded-pill">Đã hủy</span>
                                            <div class="mt-1 small text-muted fw-medium" style="font-size: 0.75rem;">
                                                <i class="fas fa-info-circle me-1"></i>Bỏ hẹn ca ${shiftText}
                                            </div>`;
                                } else {
                                    statusHtml = `<span class="badge bg-white border border-danger text-danger px-3 py-1 rounded-pill shadow-sm">Quá hạn</span>`;
                                }

                                if (item.status === 'BORROWED' || item.status === 'OVERDUE') {
                                    actionHtml = `<a href="${item.return_url}" class="btn btn-outline-primary btn-sm rounded-pill px-4 fw-bold transition-hover custom-confirm" data-message="Bạn chắc chắn muốn báo trả cuốn sách [${safeTitle}]? Vui lòng mang sách đến quầy sau khi xác nhận.">Trả sách</a>`;
                                } else if (item.status === 'PENDING') {
                                    actionHtml = `<span class="text-warning small fw-medium"><i class="fas fa-spinner fa-spin me-1"></i>Chờ xử lý</span>`;
                                } else if (item.status === 'CANCELLED') {
                                    actionHtml = `<span class="text-muted small opacity-75"><i class="fas fa-ban me-1"></i>Đã hủy</span>`;
                                } else {
                                    actionHtml = `<span class="text-success small fw-medium"><i class="fas fa-check-double me-1"></i>Hoàn tất</span>`;
                                }
                                
                                var dateColor = (item.status === 'BORROWED' || item.status === 'OVERDUE') ? 'text-primary fw-bold' : 'text-secondary';
                                var returnDateHtml = item.return_date ? item.return_date : `<span class="text-muted opacity-50">-</span>`;

                                html += `
                                <tr class="transition-hover-row animate__animated animate__fadeIn">
                                    <td class="ps-4 text-center">${checkboxHtml}</td>
                                    <td class="py-3">
                                        <div class="d-flex align-items-center">
                                            <img src="${item.cover_image}" alt="" style="width: 45px; height: 65px; object-fit: cover;" class="rounded me-3 border shadow-sm">
                                            <div>
                                                <div class="fw-bold text-dark">${safeTitle}</div>
                                                <small class="text-muted"><i class="far fa-user me-1"></i>${safeAuthor}</small>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="small text-secondary">${item.borrow_date || '-'}</td>
                                    <td class="small"><span class="${dateColor}">${item.due_date || '-'}</span></td>
                                    <td class="small text-secondary">${returnDateHtml}</td>
                                    <td>${statusHtml}</td>
                                    <td class="text-center">${actionHtml}</td>
                                </tr>`;
                            });
                            
                            $('#history-container').append(html);
                            
                            if (response.has_next) {
                                histTrigger.data('page', histTrigger.data('page') + 1).removeClass('loading');
                            } else {
                                histTrigger.data('has-next', false);
                            }
                            $('#history-loading-spinner').hide();
                            
                            if (typeof adjustMainMinHeight === "function") {
                                adjustMainMinHeight();
                            }
                        }
                    }
                });
            }
        }
        // C. Cuộn Sách Yêu Thích
        var wishTrigger = $('#wishlist-scroll-trigger');
        if (wishTrigger.length && wishTrigger.data('has-next') === true) {
            // Tăng từ 50 lên 300
            if ($(window).scrollTop() + $(window).height() >= $(document).height() - 300) {
                if (wishTrigger.hasClass('loading')) return;
                wishTrigger.addClass('loading');
                $('#wishlist-loading-spinner').show();

                $.ajax({
                    url: wishTrigger.data('url'),
                    type: 'GET',
                    data: { 'page': wishTrigger.data('page') },
                    success: function(response) {
                        if (response.status === 'success') {
                            var html = '';
                            response.data.forEach(function(book) { html += renderBookHTML(book, false); });
                            $('#wishlist-container').append(html);

                            if (response.has_next) {
                                wishTrigger.data('page', wishTrigger.data('page') + 1).removeClass('loading');
                            } else {
                                wishTrigger.data('has-next', false);
                            }
                            $('#wishlist-loading-spinner').hide();
                            adjustMainMinHeight();
                        }
                    }
                });
            }
        }
    }); // Kết thúc $(window).scroll
    
    // 10. TÍNH NĂNG MƯỢN SÁCH BẰNG AJAX
    // Dành cho sách miễn phí
    $(document).on('click', '.ajax-borrow-btn', function(e) {
        e.preventDefault();
        e.stopImmediatePropagation(); 

        var btn = $(this);
        var url = btn.attr('href');
        var message = btn.data('message') || "Bạn muốn gửi yêu cầu mượn cuốn sách này?";

        var confirmHtml = `
        <div class="modal fade" id="ajaxConfirmModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow-lg text-center p-4" style="border-radius: 20px;">
                    <div class="mb-3"><i class="fas fa-question-circle text-primary fs-1"></i></div>
                    <h6 class="fw-bold text-dark mb-4">${escapeHTML(message)}</h6>
                    <div class="d-flex justify-content-center gap-2">
                        <button type="button" class="btn btn-light rounded-pill px-3" data-bs-dismiss="modal">Hủy</button>
                        <button type="button" class="btn btn-primary rounded-pill px-3 fw-bold text-white" id="confirm-do-borrow">Mượn ngay</button>
                    </div>
                </div>
            </div>
        </div>`;

        $('#ajaxConfirmModal').remove();
        $('body').append(confirmHtml);
        var confirmModal = new bootstrap.Modal(document.getElementById('ajaxConfirmModal'));
        confirmModal.show();

        $('#confirm-do-borrow').on('click', function() {
            $(this).html('<i class="fas fa-spinner fa-spin"></i>').prop('disabled', true);
            
            $.ajax({
                url: url,
                type: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                success: function(response) {
                    confirmModal.hide();
                    setTimeout(function() {
                        if (response.status === 'success') {
                            btn.replaceWith('<button class="btn btn-warning text-dark rounded-pill fw-bold w-100 py-2 disabled"><i class="fas fa-clock me-1"></i>CHỜ DUYỆT</button>');
                            if (typeof checkNewNotifications === "function") checkNewNotifications();
                            showSingleNotify('success', response.message);
                        } else if (response.redirect) {
                            showSingleNotify('warning', response.message);
                            setTimeout(function() { window.location.href = response.redirect; }, 2000);
                        } else {
                            showSingleNotify('warning', response.message);
                        }
                    }, 400);
                },
                error: function() {
                    confirmModal.hide();
                    setTimeout(function() { showSingleNotify('warning', 'Lỗi kết nối server!'); }, 400);
                }
            });
        });
    });

    // Dành cho sách VIP (Thanh toán Modal)
    $(document).on('submit', '.payment-modal form', function(e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        
        var form = $(this);
        var btn = form.find('button[type="submit"]');
        var originalText = btn.html();

        btn.html('<i class="fas fa-spinner fa-spin"></i> Đang xử lý...').prop('disabled', true);

        $.ajax({
            url: form.attr('action'),
            type: 'POST',
            data: form.serialize(),
            headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCSRFToken() },
            success: function(response) {
                var modalEl = form.closest('.modal')[0];
                var bsModal = bootstrap.Modal.getInstance(modalEl);
                if(bsModal) bsModal.hide(); 
                
                setTimeout(function() {
                    if (response.status === 'success') {
                        var modalId = $(modalEl).attr('id');
                        $('button[data-bs-target="#' + modalId + '"]').replaceWith('<button class="btn btn-warning text-dark rounded-pill fw-bold w-100 py-2 shadow-sm disabled"><i class="fas fa-clock me-1"></i>CHỜ DUYỆT</button>');
                        
                        if (typeof checkNewNotifications === "function") checkNewNotifications();
                        showSingleNotify('success', response.message);
                    } else if (response.redirect) {
                        showSingleNotify('warning', response.message);
                        setTimeout(function() { window.location.href = response.redirect; }, 2000);
                    } else {
                        showSingleNotify('warning', response.message);
                        btn.html(originalText).prop('disabled', false);
                    }
                }, 400);
            },
            error: function() {
                showSingleNotify('warning', 'Lỗi kết nối máy chủ!');
                btn.html(originalText).prop('disabled', false);
            }
        });
    });

    // Convert server-side Django messages into modal notifications
    try {
        var alertEl = $('.django-flash').first();
        if (alertEl.length) {
            var msg = alertEl.clone().children().remove().end().text().trim();
            var type = alertEl.hasClass('alert-success') ? 'success' : 'warning';
            alertEl.remove();
            showSingleNotify(type, msg);
        }
    } catch (e) {
        // silent
    }

});
