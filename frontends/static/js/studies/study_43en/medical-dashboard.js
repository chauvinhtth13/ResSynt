// /**
//  * Medical Dashboard JavaScript - Các chức năng bổ sung cho dashboard quản lý bệnh nhân
//  * 
//  * File này cung cấp các chức năng tương tác cho dashboard y tế
//  */

// // Xử lý thông báo thời gian thực cho lịch hẹn
// const MedicalDashboard = {
  
//   // Khởi tạo tất cả các chức năng dashboard
//   init: function() {
//     this.setupNotifications();
//     this.setupQuickActions();
//     this.setupTableSearch();
//     this.setupDateRangePicker();
//     console.log("Medical Dashboard initialized");
//   },
  
//   // Thiết lập thông báo thời gian thực
//   setupNotifications: function() {
//     // Giả lập nhận thông báo mới mỗi 30 giây (trong môi trường thực tế sẽ sử dụng WebSocket)
//     setInterval(function() {
//       // Chỉ hiển thị thông báo nếu có dữ liệu mới (từ server)
//       if (Math.random() > 0.8) { // 20% cơ hội hiển thị thông báo mới (demo)
//         const notifications = [
//           "Bệnh nhân Nguyễn Văn A đã đặt lịch hẹn mới",
//           "Kết quả xét nghiệm từ phòng lab đã sẵn sàng",
//           "Có 3 bệnh nhân đang đợi trong phòng chờ",
//           "Dr. Minh yêu cầu tham khảo ý kiến cho ca bệnh #103",
//           "Cảnh báo: Phát hiện K. pneumoniae kháng Carbapenem"
//         ];
//         const randomIndex = Math.floor(Math.random() * notifications.length);
//         const notification = notifications[randomIndex];
        
//         // Kiểm tra xem thông báo có được kích hoạt không
//         if (Notification.permission === "granted") {
//           new Notification("Thông báo y tế", { 
//             body: notification,
//             icon: '/static/img/hospital-logo.png'
//           });
//         } else if (Notification.permission !== "denied") {
//           Notification.requestPermission().then(permission => {
//             if (permission === "granted") {
//               new Notification("Thông báo y tế", { 
//                 body: notification,
//                 icon: '/static/img/hospital-logo.png'
//               });
//             }
//           });
//         }
        
//         // Cập nhật UI thông báo
//         const notificationCount = $('.navbar-badge').first();
//         const currentCount = parseInt(notificationCount.text()) || 0;
//         notificationCount.text(currentCount + 1);
//       }
//     }, 30000); // 30 giây
//   },
  
//   // Thiết lập các hành động nhanh
//   setupQuickActions: function() {
//     // Xử lý các nút tác vụ nhanh
//     $('.quick-action-btn').on('click', function(e) {
//       e.preventDefault();
//       const action = $(this).data('action');
      
//       switch(action) {
//         case 'add-patient':
//           window.location.href = '/screening/create/';
//           break;
//         case 'view-appointments':
//           // Mở modal lịch hẹn
//           $('#upcomingAppointmentsModal').modal('show');
//           break;
//         case 'refresh-stats':
//           // Giả lập tải lại dữ liệu thống kê
//           $('.refresh-spinner').removeClass('d-none').addClass('d-inline-block');
//           setTimeout(function() {
//             $('.refresh-spinner').removeClass('d-inline-block').addClass('d-none');
//             // Hiển thị thông báo thành công
//             toastr.success('Dữ liệu thống kê đã được cập nhật!');
//           }, 1500);
//           break;
//       }
//     });
//   },
  
//   // Thiết lập tìm kiếm trong bảng
//   setupTableSearch: function() {
//     // Tìm kiếm trong bảng bệnh nhân
//     $('#table-search').on('keyup', function() {
//       const value = $(this).val().toLowerCase();
//       $('.table-appointments tbody tr').filter(function() {
//         $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
//       });
//     });
    
//     // Tìm kiếm trong bảng modal
//     $('#patient-table-search').on('keyup', function() {
//       const value = $(this).val().toLowerCase();
//       $('.table-appointments tbody tr').filter(function() {
//         $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
//       });
//     });
    
//     // Tìm kiếm tổng quát (trên thanh tìm kiếm đầu trang)
//     $('#patient-search').on('keyup', function(e) {
//       if (e.key === 'Enter' || e.keyCode === 13) {
//         const searchValue = $(this).val().trim();
//         if (searchValue) {
//           // Trong thực tế, điều này sẽ chuyển hướng đến trang kết quả tìm kiếm
//           toastr.info(`Đang tìm kiếm "${searchValue}"...`);
          
//           // Giả lập tìm kiếm (có thể thay thế bằng AJAX trong môi trường thực tế)
//           setTimeout(() => {
//             if (searchValue.toLowerCase().includes('khương') || 
//                 searchValue.toLowerCase().includes('beta') ||
//                 searchValue.toLowerCase().includes('pneumoniae')) {
//               toastr.success(`Tìm thấy 5 kết quả cho "${searchValue}"`);
//               // Có thể thêm mã JavaScript để thêm kết quả tìm kiếm vào DOM
//             } else {
//               toastr.warning(`Không tìm thấy kết quả cho "${searchValue}"`);
//             }
//           }, 1000);
//         }
//       }
//     });
//   },
  
//   // Thiết lập bộ chọn phạm vi ngày tháng
//   setupDateRangePicker: function() {
//     if ($('#appointment-daterange').length) {
//       $('#appointment-daterange').daterangepicker({
//         ranges: {
//           'Hôm nay': [moment(), moment()],
//           'Hôm qua': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
//           '7 ngày qua': [moment().subtract(6, 'days'), moment()],
//           '30 ngày qua': [moment().subtract(29, 'days'), moment()],
//           'Tháng này': [moment().startOf('month'), moment().endOf('month')],
//           'Tháng trước': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
//         },
//         startDate: moment().subtract(29, 'days'),
//         endDate: moment(),
//         locale: {
//           format: 'DD/MM/YYYY',
//           applyLabel: 'Áp dụng',
//           cancelLabel: 'Hủy',
//           customRangeLabel: 'Phạm vi tùy chỉnh'
//         }
//       }, function(start, end) {
//         $('#appointment-daterange span').html(start.format('DD/MM/YYYY') + ' - ' + end.format('DD/MM/YYYY'));
//         // Tại đây có thể gửi AJAX request để lấy dữ liệu dựa trên phạm vi ngày
//       });
//     }
//   }
// };

// // Khởi tạo khi tài liệu đã sẵn sàng
// $(document).ready(function() {
//   MedicalDashboard.init();
  
//   // Khởi tạo Toast Notifications
//   toastr.options = {
//     closeButton: true,
//     progressBar: true,
//     positionClass: "toast-top-right",
//     timeOut: 3000
//   };
  
//   // Khởi tạo tooltip và popover
//   $('[data-toggle="tooltip"]').tooltip();
//   $('[data-toggle="popover"]').popover();
// });
