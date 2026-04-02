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

