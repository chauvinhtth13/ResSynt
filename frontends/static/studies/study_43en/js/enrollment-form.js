/**
 * enrollment-form.js - FIXED v5.0
 * ONLY UI interactions - NO validation (backend handles it)
 */

(function() {
  'use strict';
  
  const state = {
    isReadonly: false,
    isCreate: false,
    initialized: false
  };
  
  // ==========================================
  // CONDITIONAL SECTIONS - Simple show/hide
  // ==========================================
  function initConditionalSections() {
    console.log(' Init conditional sections...');
    
    // Hospital transfer
    $('input[name="FROMOTHERHOSPITAL"], select#id_FROMOTHERHOSPITAL').on('change', function() {
      const val = $('input[name="FROMOTHERHOSPITAL"]:checked').val() || $('#id_FROMOTHERHOSPITAL').val();
      const show = ['True', 'true', '1', 1].includes(val);
      
      $('#hospital-transfer-details').toggle(show);
      console.log('🏥 Hospital transfer:', show ? 'show' : 'hide');
    }).trigger('change');
    
    // Medication history
    $('input[name="CORTICOIDPPI"]').on('change', function() {
      const show = $('input[name="CORTICOIDPPI"]:checked').val() === 'yes';
      
      $('#medication-history-section').toggle(show);
      console.log(' Medication:', show ? 'show' : 'hide');
    }).trigger('change');
    
    // Underlying conditions
    $('input[name="UNDERLYINGCONDS"]').on('change', function() {
      const show = $('input[name="UNDERLYINGCONDS"]:checked').val() === 'True';
      
      $('#underlying-conditions-section').toggle(show);
      console.log('🩺 Underlying conditions:', show ? 'show' : 'hide');
      
      // If hiding, uncheck all underlying checkboxes
      if (!show) {
        $('#underlying-conditions-section input[type="checkbox"]').prop('checked', false);
        $('#id_OTHERDISEASESPECIFY').val('');
      }
    }).trigger('change');
    
    // Other disease specification
    $('#id_OTHERDISEASE').on('change', function() {
      $('#other-disease-detail').toggle(this.checked);
      console.log('📝 Other disease:', this.checked ? 'show' : 'hide');
    }).trigger('change');
    
    console.log(' Conditional sections ready');
  }
  
  // ==========================================
  // AGE CALCULATION - Display only
  // ==========================================
  function initAgeCalculation() {
    console.log('🎂 Init age calculation...');
    
    const $day = $('#id_DAYOFBIRTH');
    const $month = $('#id_MONTHOFBIRTH');
    const $year = $('#id_YEAROFBIRTH');
    const $display = $('#calculated-age');
    
    if (!$day.length || !$display.length) {
      console.log(' Age calculation elements not found');
      return;
    }
    
    function calculate() {
      const d = parseInt($day.val());
      const m = parseInt($month.val());
      const y = parseInt($year.val());
      
      if (!d || !m || !y) {
        $display.html('<i class="fas fa-calculator text-muted"></i><span class="ml-2 text-muted">--</span>');
        return;
      }
      
      try {
        const birth = new Date(y, m - 1, d);
        const today = new Date();
        
        // Check if date is valid
        if (birth.getDate() !== d || birth.getMonth() !== (m - 1)) {
          $display.html('<i class="fas fa-exclamation-triangle text-danger"></i><span class="ml-2 text-danger">Invalid date</span>');
          return;
        }
        
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
          age--;
        }
        
        $display.html(`<i class="fas fa-check-circle text-success"></i><span class="ml-2"><strong>${age} years old</strong></span>`);
      } catch (e) {
        $display.html('<i class="fas fa-exclamation-triangle text-danger"></i><span class="ml-2 text-danger">Invalid date</span>');
      }
    }
    
    $day.add($month).add($year).on('input change', calculate);
    calculate();
    
    console.log(' Age calculation ready');
  }
  
  // ==========================================
  // MEDICATION FORMSET - Add rows ONLY
  // ==========================================
  function initMedicationFormset() {
    console.log(' Init medication formset...');
    
    const $tbody = $('#medication-formset-body');
    const $addBtn = $('#add-medication-btn');
    const $totalInput = $('input[name="medhisdrug_set-TOTAL_FORMS"]');
    
    if (!$tbody.length) {
      console.log(' Medication tbody not found');
      return;
    }
    
    console.log('Found medication elements:', {
      tbody: $tbody.length,
      addBtn: $addBtn.length,
      totalInput: $totalInput.length,
      currentTotal: $totalInput.val()
    });
    
    //  Add row
    if ($addBtn.length) {
      $addBtn.on('click', function() {
        const total = parseInt($totalInput.val()) || 0;
        
        console.log('Adding medication row, current total:', total);
        
        if (total >= 20) {
          alert('Tối đa 20 loại thuốc');
          return;
        }
        
        //  FIX: Proper Django formset format
        const html = `
          <tr class="formset-row">
            <input type="hidden" name="medhisdrug_set-${total}-id" value="" id="id_medhisdrug_set-${total}-id">
            <td>
              <input type="number" 
                     name="medhisdrug_set-${total}-SEQUENCE" 
                     id="id_medhisdrug_set-${total}-SEQUENCE"
                     class="form-control form-control-sm" 
                     value="${total + 1}" 
                     readonly>
            </td>
            <td>
              <input type="text" 
                     name="medhisdrug_set-${total}-DRUGNAME" 
                     id="id_medhisdrug_set-${total}-DRUGNAME"
                     class="form-control form-control-sm" 
                     required 
                     placeholder="Tên thuốc">
            </td>
            <td>
              <input type="text" 
                     name="medhisdrug_set-${total}-DOSAGE" 
                     id="id_medhisdrug_set-${total}-DOSAGE"
                     class="form-control form-control-sm" 
                     placeholder="Liều lượng">
            </td>
            <td>
              <input type="text" 
                     name="medhisdrug_set-${total}-USAGETIME" 
                     id="id_medhisdrug_set-${total}-USAGETIME"
                     class="form-control form-control-sm" 
                     placeholder="Thời gian">
            </td>
            <td>
              <textarea name="medhisdrug_set-${total}-USAGEREASON" 
                        id="id_medhisdrug_set-${total}-USAGEREASON"
                        class="form-control form-control-sm" 
                        rows="2" 
                        placeholder="Lý do"></textarea>
            </td>
          </tr>
        `;
        
        $tbody.append(html);
        $totalInput.val(total + 1);
        console.log(' Added medication row', total + 1);
      });
    }
    
    console.log(' Medication formset ready');
  }
  
  // ==========================================
  // ADDRESS SYSTEM TOGGLE
  // ==========================================
  function initAddressSystemToggle() {
    console.log('🗺️ Initializing address system toggle...');
    
    const $newAddressFields = $('#new-address-fields');
    const $oldAddressFields = $('#old-address-fields');
    const $addressPreview = $('#address-preview');
    
    console.log('Address elements found:', {
      newFields: $newAddressFields.length,
      oldFields: $oldAddressFields.length,
      preview: $addressPreview.length,
      radios: $('.address-system-radio').length
    });
    
    if (!$newAddressFields.length || !$oldAddressFields.length) {
      console.error(' Address field containers not found!');
      return;
    }
    
    // Toggle address fields based on selection
    $('.address-system-radio').on('change', function() {
      const selectedValue = $(this).val();
      console.log('📍 Address system selected:', selectedValue);
      
      // Hide all first with animation
      $newAddressFields.slideUp(200);
      $oldAddressFields.slideUp(200);
      
      // Show based on selection after hide animation completes
      setTimeout(() => {
        if (selectedValue === 'new' || selectedValue === 'both') {
          $newAddressFields.slideDown(300);
          console.log(' Showing NEW address fields');
        }
        if (selectedValue === 'old' || selectedValue === 'both') {
          $oldAddressFields.slideDown(300);
          console.log(' Showing OLD address fields');
        }
      }, 250);
      
      updateAddressPreview();
    });
    
    // Update preview on input
    const addressInputs = [
      'input[name="STREET_NEW"]',
      'input[name="WARD_NEW"]', 
      'input[name="DISTRICT_NEW"]',
      'input[name="CITY_NEW"]',
      'input[name="STREET"]',
      'input[name="WARD"]',
      'input[name="DISTRICT"]',
      'input[name="PROVINCECITY"]'
    ].join(', ');
    
    $(addressInputs).on('input', function() {
      updateAddressPreview();
    });
    
    // Initialize on page load
    const $checkedRadio = $('.address-system-radio:checked');
    if ($checkedRadio.length) {
      console.log('Initial address system:', $checkedRadio.val());
      $checkedRadio.trigger('change');
    } else {
      // Default to 'new' if nothing selected
      console.log('No address system selected, defaulting to NEW');
      $('#id_PRIMARY_ADDRESS_new').prop('checked', true).trigger('change');
    }
    
    console.log(' Address system toggle ready');
  }
  
  /**
   * Update address preview with enhanced formatting
   */
  function updateAddressPreview() {
    const selectedSystem = $('input[name="PRIMARY_ADDRESS"]:checked').val();
    const $preview = $('#address-preview');
    
    if (!$preview.length) {
      console.log(' Preview element not found');
      return;
    }
    
    let previewHTML = '';
    let hasNewAddress = false;
    let hasOldAddress = false;
    
    // NEW ADDRESS
    if (selectedSystem === 'new' || selectedSystem === 'both') {
      const streetNew = $('input[name="STREET_NEW"]').val()?.trim();
      const wardNew = $('input[name="WARD_NEW"]').val()?.trim();
      const districtNew = $('input[name="DISTRICT_NEW"]').val()?.trim();
      const cityNew = $('input[name="CITY_NEW"]').val()?.trim();
      
      if (streetNew || wardNew || districtNew || cityNew) {
        hasNewAddress = true;
        const newAddressParts = [streetNew, wardNew, districtNew, cityNew].filter(Boolean);
        
        previewHTML += `
          <div class="address-preview-section">
            <span class="address-preview-label">
              <i class="fas fa-map-marked-alt mr-1"></i>Địa chỉ mới:
            </span>
            <span class="address-preview-value">${newAddressParts.join(', ')}</span>
          </div>
        `;
      }
    }
    
    // OLD ADDRESS
    if (selectedSystem === 'old' || selectedSystem === 'both') {
      const street = $('input[name="STREET"]').val()?.trim();
      const ward = $('input[name="WARD"]').val()?.trim();
      const district = $('input[name="DISTRICT"]').val()?.trim();
      const city = $('input[name="PROVINCECITY"]').val()?.trim();
      
      if (street || ward || district || city) {
        hasOldAddress = true;
        const oldAddressParts = [street, ward, district, city].filter(Boolean);
        
        previewHTML += `
          <div class="address-preview-section">
            <span class="address-preview-label">
              <i class="fas fa-archive mr-1"></i>Địa chỉ cũ:
            </span>
            <span class="address-preview-value">${oldAddressParts.join(', ')}</span>
          </div>
        `;
      }
    }
    
    // Update preview
    if (hasNewAddress || hasOldAddress) {
      $preview.html(previewHTML).addClass('has-address');
    } else {
      $preview.html('<span class="text-muted font-italic">Địa chỉ sẽ hiển thị tại đây khi bạn nhập...</span>')
              .removeClass('has-address');
    }
  }
  
  // ==========================================
  // UI ENHANCEMENTS
  // ==========================================
  function initUIEnhancements() {
    console.log('🎨 Init UI...');
    
    // Ethnicity autocomplete
    const $ethnicity = $('#id_ETHNICITY');
    if ($ethnicity.length && typeof Awesomplete !== 'undefined') {
      new Awesomplete($ethnicity[0], {
        list: ["Kinh", "Hoa", "Thái", "Chăm", "Tày", "Mường", "H'Mông", "Khơ-me", "Nùng", "Dao"],
        minChars: 0,
        maxItems: 10,
        autoFirst: true
      });
      console.log(' Ethnicity autocomplete initialized');
    }
    
    // Read-only mode
    if (state.isReadonly) {
      console.log('Setting read-only mode');
      $('input, select, textarea').not('[type="hidden"]').prop('disabled', true);
      $('button[type="submit"]').hide();
      $('.address-system-radio').prop('disabled', true);
    }
    
    // Form reset handler
    $('button[type="reset"]').on('click', function(e) {
      if (!confirm('Bạn có chắc muốn đặt lại form? Tất cả dữ liệu chưa lưu sẽ bị mất.')) {
        e.preventDefault();
        return false;
      }
      
      // After reset, re-trigger conditional sections
      setTimeout(() => {
        $('input[name="FROMOTHERHOSPITAL"]:checked').trigger('change');
        $('input[name="CORTICOIDPPI"]:checked').trigger('change');
        $('input[name="UNDERLYINGCONDS"]:checked').trigger('change');
        $('.address-system-radio:checked').trigger('change');
      }, 100);
    });
    
    console.log(' UI enhancements ready');
  }
  
  // ==========================================
  // INITIALIZATION
  // ==========================================
  $(document).ready(function() {
    console.log('===  ENROLLMENT FORM INITIALIZING ===');
    console.log('jQuery version:', $.fn.jquery);
    console.log('Window state:', window.enrollmentFormState);
    
    state.isReadonly = window.enrollmentFormState?.isReadonly || false;
    state.isCreate = window.enrollmentFormState?.isCreate || false;
    
    console.log('State:', state);
    
    // Initialize all modules
    try {
      initConditionalSections();
      initAgeCalculation();
      initMedicationFormset();
      initAddressSystemToggle(); //  Important!
      initUIEnhancements();
      
      state.initialized = true;
      console.log('===  ENROLLMENT FORM READY ===');
    } catch (error) {
      console.error(' Initialization error:', error);
    }
  });
  
  console.log(' Enrollment form module loaded');
  
})();