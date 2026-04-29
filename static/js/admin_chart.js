window.onload = function() {
    // 1. Kiểm tra xem có phải là Admin HOẶC Staff Dashboard không
    const path = window.location.pathname;
    const isDashboard = path.includes('/admin/') || path.includes('/staff/');
    
    if (isDashboard) {
        console.log("📊 Khởi động hệ thống thống kê cho nhân sự...");

        setTimeout(function() {
            // 2. Tìm vị trí chèn (Ưu tiên tìm thẻ có ID 'staff-chart-area' nếu bạn đặt sẵn)
            let container = document.getElementById('staff-chart-area') || 
                            document.querySelector('.content .container-fluid') || 
                            document.querySelector('.container');

            // Chiến thuật tìm theo tiêu đề nếu là trang Staff chưa có ID
            if (!container) {
                const headers = document.querySelectorAll('h1, h2, h3, h4');
                headers.forEach(el => {
                    if (el.textContent.includes('DANH SÁCH') || el.textContent.includes('Dashboard')) {
                        container = el.parentElement;
                    }
                });
            }

            if (container) {
                const chartHtml = `
                    <div id="alovu-chart-section" class="mb-4">
                        <div class="card shadow-sm border-0" style="border-radius: 15px;">
                            <div class="card-header bg-white py-3 d-flex align-items-center justify-content-between" style="border-left: 5px solid #28a745;">
                                <h5 class="m-0 font-weight-bold text-dark">
                                    <i class="fas fa-chart-line mr-2 text-success"></i> TÌNH HÌNH MƯỢN TRẢ HÔM NAY
                                </h5>
                                <button id="btnExportPDF" class="btn btn-sm btn-outline-danger">Xuất PDF</button>
                            </div>
                            <div class="card-body bg-white">
                                <div style="height: 300px;"><canvas id="borrowChart"></canvas></div>
                            </div>
                        </div>
                    </div>
                `;
                
                if (!document.getElementById('alovu-chart-section')) {
                    container.insertAdjacentHTML('afterbegin', chartHtml);
                }

                // 3. Vẽ biểu đồ (Vẫn dùng chung API admin_chart_data bạn đã viết)
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
                script.onload = function() {
                    fetch('/api/admin-chart/')
                        .then(res => res.json())
                        .then(serverData => {
                            const ctx = document.getElementById('borrowChart').getContext('2d');
                            new Chart(ctx, {
                                type: 'bar', // Trang thủ thư mình đổi sang biểu đồ CỘT cho chuyên nghiệp nhé!
                                data: {
                                    labels: serverData.labels,
                                    datasets: [{
                                        label: 'Số lượng',
                                        data: serverData.data,
                                        backgroundColor: ['#17a2b8', '#ffc107', '#28a745', '#dc3545'],
                                        borderRadius: 8
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                                }
                            });
                        });
                };
                document.head.appendChild(script);
            }
        }, 500);
    }
};