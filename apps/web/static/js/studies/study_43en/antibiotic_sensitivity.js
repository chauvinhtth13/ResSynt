$(document).ready(function() {
    // Biến cần thiết
    const cultureId = $('#culture-id').val();
    const usubjid = $('#usubjid').val();
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
    let editingInProgress = false;
    
    // Xác định chế độ xem từ URL
    const urlParams = new URLSearchParams(window.location.search);
    const isViewOnly = urlParams.get('mode') === 'view';
    
    // Danh sách kháng sinh theo tier
    const antibioticsByTier = {
        'TIER1': ['Ampicillin', 'Cefazolin', 'Cefotaxime', 'Ceftriaxone', 'AmoxicillinClavulanate'],
        'TIER2': ['Cefepime', 'Imipenem', 'Meropenem', 'Cefuroxime', 'Ertapenem'],
        'TIER3': ['Cefiderocol', 'CeftazidimeAvibactam', 'ImipenemRelebactam'],
        'TIER4': ['Aztreonam', 'Ceftaroline', 'Ceftazidime', 'CeftolozaneTazobactam'],
        'COLISTIN': ['Colistin'],
        'URINE_ONLY': ['Cefazolin_Urine', 'Nitrofurantoin', 'Fosfomycin'],
        'OTHER': ['Ceftriazone', 'Tigecycline', 'TicarcillinClavulanic']
    };
    
    // Tải dữ liệu ban đầu
    loadAntibioticData();
    
    // SỰ KIỆN
    
    // Nếu đang ở chế độ view-only, không kích hoạt các sự kiện chỉnh sửa
    if (isViewOnly) {
        console.log("Đang ở chế độ view-only, đã tắt các chức năng chỉnh sửa");
    }
    
    // Sự kiện mở/đóng tier
    $(document).on('click', '.tier-header', function(e) {
        // Bỏ qua nếu click vào nút
        if ($(e.target).closest('button, .btn').length > 0) {
            return;
        }
        
        const target = $($(this).data('target'));
        target.collapse('toggle');
        
        // Chuyển đổi icon
        const toggleIcon = $(this).find('.tier-toggle');
        if (target.hasClass('show')) {
            toggleIcon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
        } else {
            toggleIcon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
            
            // Tự động tạo kháng sinh nếu tier trống và không phải chế độ view-only
            const tierCode = $(this).closest('.antibiotic-card').data('tier-code');
            const container = $('#antibiotics-' + tierCode);
            if (container.find('.antibiotic-item').length === 0 && !isViewOnly) {
                populateTierWithAntibiotics(tierCode);
            }
        }
    });
    
    // Ngăn click lan truyền từ các nút
    $(document).on('click', '.tier-actions .btn', function(e) {
        e.stopPropagation();
    });
    
    // Sự kiện nút chỉnh sửa tier
    $(document).on('click', '.btn-edit-tier', function(e) {
        e.stopPropagation();
        
        // Không cho phép chỉnh sửa khi ở chế độ view-only
        if (isViewOnly) {
            return;
        }
        
        const tierCode = $(this).data('tier');
        const tierElement = $('#tier-' + tierCode);
        
        // Đảm bảo tier được mở
        const collapseTarget = tierElement.find('.collapse');
        if (!collapseTarget.hasClass('show')) {
            collapseTarget.collapse('show');
            tierElement.find('.tier-toggle').removeClass('fa-chevron-down').addClass('fa-chevron-up');
        }
        
        // Chuyển sang chế độ chỉnh sửa
        tierElement.addClass('editing-tier');
        tierElement.find('.view-mode').hide();
        tierElement.find('.direct-edit-container').show();
        
        // Hiện nút lưu, ẩn nút chỉnh sửa
        $(this).hide();
        tierElement.find('.btn-save-tier').show();
        
        editingInProgress = true;
    });
    
    // Sự kiện nút lưu thay đổi
    $(document).on('click', '.btn-save-tier', function(e) {
        e.stopPropagation();
        
        const tierCode = $(this).data('tier');
        saveTierChanges(tierCode);
    });
    
    // Sự kiện thay đổi giá trị form
    $(document).on('change', '.edit-input, .edit-select', function() {
        editingInProgress = true;
    });
    
    // Cảnh báo khi rời trang có thay đổi chưa lưu
    $(window).on('beforeunload', function() {
        if (editingInProgress) {
            return 'Bạn có thay đổi chưa được lưu. Bạn có chắc muốn rời trang?';
        }
    });
    
    // CÁC HÀM
    
    // Tạo danh sách kháng sinh cho tier
    function populateTierWithAntibiotics(tierCode) {
        const antibioticsForTier = antibioticsByTier[tierCode] || [];
        if (antibioticsForTier.length === 0) return;
        
        const container = $('#antibiotics-' + tierCode);
        
        // Tạo các hàng kháng sinh
        antibioticsForTier.forEach((antibiotic, index) => {
            const tempId = 'new-' + Date.now() + '-' + index;
            const antibiotic_value = antibiotic;
            const antibiotic_display = antibiotic.replace(/([A-Z])/g, ' $1').trim();
            
            const newRowHtml = `
                <div class="list-group-item antibiotic-item" id="antibiotic-item-${tempId}">
                    <div class="row">
                        <div class="col-md-3">
                            <strong>${antibiotic_display}</strong>
                            <input type="hidden" name="antibiotic_name" value="${antibiotic_value}" data-antibiotic-id="${tempId}">
                        </div>
                        <div class="col-md-9">
                            <div class="direct-edit-container">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>Độ nhạy:</label>
                                            <select class="form-control edit-select" name="sensitivity_level" data-antibiotic-id="${tempId}">
                                                <option value="S">Nhạy cảm (S)</option>
                                                <option value="I">Trung gian (I)</option>
                                                <option value="R">Kháng thuốc (R)</option>
                                                <option value="U">Không biết (U)</option>
                                                <option value="ND" selected>Không xác định (ND)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>Vòng ức chế (mm):</label>
                                            <input type="text" class="form-control edit-input" name="inhibition_zone_diameter" value="" data-antibiotic-id="${tempId}">
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>MIC (μg/ml):</label>
                                            <input type="text" class="form-control edit-input" name="mic_value" value="" data-antibiotic-id="${tempId}">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            container.append(newRowHtml);
        });
        
        // Hiển thị nút lưu
        $('#tier-' + tierCode).find('.btn-save-tier').show();
        $('#tier-' + tierCode).find('.btn-edit-tier').hide();
        $('#tier-' + tierCode).addClass('editing-tier');
    }
    
    // Lưu thay đổi của tier
    function saveTierChanges(tierCode) {
        const tierElement = $('#tier-' + tierCode);
        const antibioticsList = tierElement.find('.antibiotic-item');
        const antibioticsData = [];
        
        // Biến để theo dõi lỗi
        let hasError = false;
        let errorMessages = [];
        
        // Thu thập dữ liệu
        antibioticsList.each(function() {
            const item = $(this);
            const antibioticId = item.attr('id').replace('antibiotic-item-', '');
            
            const antibioticName = item.find('input[name="antibiotic_name"]').val();
            const otherAntibioticName = antibioticName === 'OTHER' ? 
                item.find('input[name="other_antibiotic_name"]').val() : '';
            const sensitivityLevel = item.find('select[name="sensitivity_level"]').val();
            const inhibitionZone = item.find('input[name="inhibition_zone_diameter"]').val();
            const micValue = item.find('input[name="mic_value"]').val();
            
            // Bỏ qua nếu thiếu tên kháng sinh
            if (!antibioticName) return;
            if (antibioticName === 'OTHER' && !otherAntibioticName) return;
            
            // Kiểm tra logic mới: mỗi kháng sinh phải có ít nhất một trong hai giá trị
            if (!inhibitionZone && !micValue) {
                const displayName = antibioticName === 'OTHER' ? 
                    otherAntibioticName : 
                    antibioticName.replace(/([A-Z])/g, ' $1').trim();
                errorMessages.push(`Kháng sinh "${displayName}" chưa có giá trị Vòng ức chế hoặc MIC`);
                // Không đặt hasError = true để vẫn cho phép lưu
                // Không thêm class error-highlight để bỏ hiệu ứng CSS
            } else {
                // Dòng này vẫn giữ lại để đảm bảo xóa highlight nếu có
                item.removeClass('error-highlight');
            }
            
            // Không gửi ID tạm thời
            const idToSend = antibioticId.startsWith('new-') ? null : antibioticId;
            
            antibioticsData.push({
                id: idToSend,
                antibiotic_name: antibioticName,
                other_antibiotic_name: otherAntibioticName,
                sensitivity_level: sensitivityLevel,
                inhibition_zone_diameter: inhibitionZone,
                mic_value: micValue,
                tier: tierCode,
                sequence: antibioticsData.length + 1
            });
        });
        
        if (antibioticsData.length === 0) {
            showMessage('Không có dữ liệu kháng sinh để lưu.', 'warning');
            return;
        }
        
        // Hiển thị lỗi nếu có
        if (errorMessages.length > 0) {
            showMessage(`<strong>Lưu ý:</strong><br>${errorMessages.join('<br>')}`, 'warning');
        }

        // Hiển thị thông báo đã lưu
        showMessage('Đã lưu thay đổi', 'info');
        
        // Gửi dữ liệu lên server
        $.ajax({
            url: "/43en/" + usubjid + "/microbiology/" + cultureId + "/antibiotics/bulk-update/",
            type: 'POST',
            data: {
                bulk_data: JSON.stringify({ [tierCode]: antibioticsData }),
                replace_existing: false,
                csrfmiddlewaretoken: csrfToken
            },
            success: function(response) {
                if (response.success) {
                    showMessage('Đã lưu thay đổi thành công', 'success');
                    
                    if (response.tier_data && response.tier_data.length > 0) {
                        // Cập nhật giao diện với dữ liệu từ server
                        updateTierWithServerData(tierCode, response.tier_data);
                    } else {
                        // Chuyển về chế độ xem
                        tierElement.find('.btn-save-tier').hide();
                        tierElement.find('.btn-edit-tier').show();
                        tierElement.removeClass('editing-tier');
                    }
                } else {
                    showMessage(response.message || 'Có lỗi xảy ra khi lưu dữ liệu', 'error');
                }
                
                editingInProgress = false;
            },
            error: function() {
                showMessage('Có lỗi xảy ra khi lưu dữ liệu. Vui lòng thử lại.', 'error');
            }
        });
    }
    
    // Cập nhật dữ liệu tier từ server
    function updateTierWithServerData(tierCode, serverData) {
        const tierElement = $('#tier-' + tierCode);
        const container = $('#antibiotics-' + tierCode);
        
        // Ghi nhớ trạng thái mở/đóng
        const isExpanded = tierElement.find('.collapse').hasClass('show');
        
        // Xóa tất cả kháng sinh hiện tại
        container.empty();
        
        // Thêm các kháng sinh từ server
        serverData.forEach(sensitivity => {
            const antibioticId = sensitivity.id;
            const antibioticName = sensitivity.antibiotic_name;
            const antibioticDisplayName = sensitivity.antibiotic_display_name;
            const sensitivityLevel = sensitivity.sensitivity_level;
            const inhibitionZone = sensitivity.inhibition_zone_diameter;
            const micValue = sensitivity.mic_value;
            
            // Tạo HTML cho kháng sinh
            const rowHtml = `
                <div class="list-group-item antibiotic-item" id="antibiotic-item-${antibioticId}" data-has-server-data="true">
                    <div class="row">
                        <div class="col-md-3">
                            <strong>${antibioticDisplayName}</strong>
                            <input type="hidden" name="antibiotic_name" value="${antibioticName}" data-antibiotic-id="${antibioticId}">
                            <div class="mic-value">
                                ${inhibitionZone ? `Vòng ức chế: ${inhibitionZone} mm` : ''}
                                ${inhibitionZone && micValue ? ' | ' : ''}
                                ${micValue ? `MIC: ${micValue} μg/ml` : ''}
                            </div>
                        </div>
                        <div class="col-md-9">
                            <div class="view-mode">
                                <div class="sensitivity-result 
                                    ${sensitivityLevel === 'S' ? 'sensitive' : ''} 
                                    ${sensitivityLevel === 'R' ? 'resistant' : ''} 
                                    ${sensitivityLevel === 'I' ? 'intermediate' : ''}">
                                    ${getSensitivityText(sensitivityLevel)}
                                </div>
                            </div>
                            <div class="direct-edit-container" style="display:none;">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>Độ nhạy:</label>
                                            <select class="form-control edit-select" name="sensitivity_level" data-antibiotic-id="${antibioticId}">
                                                <option value="S" ${sensitivityLevel === 'S' ? 'selected' : ''}>Nhạy cảm (S)</option>
                                                <option value="I" ${sensitivityLevel === 'I' ? 'selected' : ''}>Trung gian (I)</option>
                                                <option value="R" ${sensitivityLevel === 'R' ? 'selected' : ''}>Kháng thuốc (R)</option>
                                                <option value="U" ${sensitivityLevel === 'U' ? 'selected' : ''}>Không biết (U)</option>
                                                <option value="ND" ${sensitivityLevel === 'ND' ? 'selected' : ''}>Không xác định (ND)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>Vòng ức chế (mm):</label>
                                            <input type="text" class="form-control edit-input" name="inhibition_zone_diameter" value="${inhibitionZone || ''}" data-antibiotic-id="${antibioticId}">
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label>MIC (μg/ml):</label>
                                            <input type="text" class="form-control edit-input" name="mic_value" value="${micValue || ''}" data-antibiotic-id="${antibioticId}">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            container.append(rowHtml);
        });
        
        // Chuyển về chế độ xem
        tierElement.removeClass('editing-tier');
        tierElement.find('.direct-edit-container').hide();
        tierElement.find('.view-mode').show();
        tierElement.find('.btn-save-tier').hide();
        
        // Hiển thị nút chỉnh sửa chỉ khi không phải ở chế độ view-only
        if (!isViewOnly) {
            tierElement.find('.btn-edit-tier').show();
        } else {
            tierElement.find('.btn-edit-tier').hide();
        }
        
        // Khôi phục trạng thái mở/đóng
        if (isExpanded) {
            tierElement.find('.collapse').collapse('show');
            tierElement.find('.tier-toggle').removeClass('fa-chevron-down').addClass('fa-chevron-up');
        }
    }
    
    // Tải dữ liệu từ server
    function loadAntibioticData() {
    // Thêm mode vào URL API khi ở chế độ view-only
    let apiUrl = "/43en/" + usubjid + "/microbiology/" + cultureId + "/antibiotics/api/";
    
    // Thêm tham số mode vào URL API
    if (isViewOnly) {
        apiUrl += "?mode=view";
    }
    
    console.log("Loading data from API:", apiUrl);
        $.ajax({
            url: apiUrl,
            type: 'GET',
            success: function(response) {
                if (response.success && response.results) {
                    // Cập nhật dữ liệu cho từng tier
                    for (const [tierCode, sensitivities] of Object.entries(response.results)) {
                        if (sensitivities && sensitivities.length > 0) {
                            updateTierWithServerData(tierCode, sensitivities);
                        }
                    }
                }
                
                // Mở tier đầu tiên
                setTimeout(function() {
                    $('.antibiotic-card:first .collapse').collapse('show');
                    $('.antibiotic-card:first .tier-toggle')
                        .removeClass('fa-chevron-down')
                        .addClass('fa-chevron-up');
                }, 100);
            },
            error: function() {
                showMessage("Không thể tải dữ liệu kháng sinh. Vui lòng tải lại trang.", "error");
                
                // Vẫn mở tier đầu tiên
                setTimeout(function() {
                    $('.antibiotic-card:first .collapse').collapse('show');
                    $('.antibiotic-card:first .tier-toggle')
                        .removeClass('fa-chevron-down')
                        .addClass('fa-chevron-up');
                }, 100);
            }
        });
    }
    
    // Trả về text hiển thị cho mã độ nhạy
    function getSensitivityText(code) {
        const map = {
            'S': 'Nhạy cảm (S)',
            'I': 'Trung gian (I)', 
            'R': 'Kháng thuốc (R)',
            'U': 'Không biết (U)',
            'ND': 'Không xác định'
        };
        return map[code] || code;
    }
    
    // Hiển thị thông báo
    function showMessage(message, type) {
        const $indicator = $('#saveIndicator');
        $indicator.removeClass('alert-success alert-danger alert-warning alert-info')
            .addClass('alert-' + type)
            .find('.message').html(message);  // Thay đổi .text() thành .html()
        $indicator.addClass('show').show();
        
        // Tự động ẩn thông báo thành công
        if (type === 'success') {
            setTimeout(function() {
                $indicator.removeClass('show');
                setTimeout(() => $indicator.hide(), 150);
            }, 5000);
        }
    }
});