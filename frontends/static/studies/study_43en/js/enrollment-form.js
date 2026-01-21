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
      console.log(' Hospital transfer:', show ? 'show' : 'hide');
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
      console.log(' Underlying conditions:', show ? 'show' : 'hide');
      
      // If hiding, uncheck all underlying checkboxes
      if (!show) {
        $('#underlying-conditions-section input[type="checkbox"]').prop('checked', false);
        $('#id_OTHERDISEASESPECIFY').val('');
      }
    }).trigger('change');
    
    // Other disease specification
    $('#id_OTHERDISEASE').on('change', function() {
      $('#other-disease-detail').toggle(this.checked);
      console.log(' Other disease:', this.checked ? 'show' : 'hide');
    }).trigger('change');
    
    console.log(' Conditional sections ready');
  }
  
  // ==========================================
  // AGE CALCULATION - Display only
  // ==========================================
  function initAgeCalculation() {
    console.log(' Init age calculation...');
    
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
    console.log('✓ Init address toggle (with smart address integration)...');
    
    const $newFields = $('#new-address-fields');
    const $oldFields = $('#old-address-fields');
    
    if (!$newFields.length || !$oldFields.length) {
      console.error('✗ Address containers not found');
      return;
    }
    
    // Toggle on radio change
    $('.address-system-radio').on('change', function() {
      const mode = $(this).val();
      console.log('✓ Mode selected:', mode);
      
      // Hide all
      $newFields.slideUp(200);
      $oldFields.slideUp(200);
      
      // Show selected and trigger smart address
      setTimeout(() => {
        if (mode === 'new') {
          $newFields.slideDown(300);
          console.log('✓ Showing NEW address fields');
        } else if (mode === 'old') {
          $oldFields.slideDown(300);
          console.log('✓ Showing OLD address fields');
        }
        
        // CRITICAL: Re-initialize smart address after visibility change
        setTimeout(() => {
          if (window.SmartAddress && window.SmartAddress.reinitialize) {
            console.log('✓ Triggering smart address re-init...');
            window.SmartAddress.reinitialize();
          }
          updateAddressPreview();
        }, 350); // Wait for slideDown to complete
        
      }, 250);
    });
    
    // Initialize - trigger on page load
    const $checked = $('.address-system-radio:checked');
    if ($checked.length) {
      console.log('Initial mode:', $checked.val());
      
      // Show the correct container immediately (no animation on load)
      if ($checked.val() === 'new') {
        $newFields.show();
      } else if ($checked.val() === 'old') {
        $oldFields.show();
      }
      
      // Let smart address initialize after a moment
      setTimeout(() => {
        if (window.SmartAddress && window.SmartAddress.init) {
          console.log('✓ Initial smart address init...');
          window.SmartAddress.init();
        }
      }, 100);
    } else {
      // Default to NEW
      console.log('No selection, defaulting to NEW');
      $('#id_PRIMARY_ADDRESS_new').prop('checked', true);
      $newFields.show();
      
      setTimeout(() => {
        if (window.SmartAddress && window.SmartAddress.init) {
          window.SmartAddress.init();
        }
      }, 100);
    }
    
    console.log('✓ Toggle ready');
  }

  /**
   * Update preview - READ from smart address hidden fields
   */
  function updateAddressPreview() {
    const selectedSystem = $('input[name="PRIMARY_ADDRESS"]:checked').val();
    const $preview = $('#address-preview');
    
    if (!$preview.length) {
      console.log('Preview element not found');
      return;
    }
    
    let previewHTML = '';
    let hasNewAddress = false;
    let hasOldAddress = false;
    
    // NEW ADDRESS (Direct wards, no districts)
    if (selectedSystem === 'new') {
      const houseNumber = $('#house-number-new').val()?.trim();      // NEW: House number
      const street = $('input[name="STREET_NEW"]').val()?.trim() || $('#street-input-new').val()?.trim();
      const ward = $('#ward-hidden-input-new').val()?.trim();        // From smart address
      const city = $('input[name="CITY_NEW"]').val()?.trim();
      
      if (houseNumber || street || ward || city) {
        hasNewAddress = true;
        const addressParts = [];
        
        // Combine house number and street
        if (houseNumber && street) {
          addressParts.push(houseNumber + ', ' + street);
        } else if (houseNumber) {
          addressParts.push(houseNumber);
        } else if (street) {
          addressParts.push(street);
        }
        
        if (ward) addressParts.push(ward);
        if (city) addressParts.push(city);
        
        previewHTML = `
          <div class="address-preview-section">
            <span class="address-preview-label">
              <i class="fas fa-map-marked-alt mr-1"></i>Địa chỉ mới:
            </span>
            <span class="address-preview-value">${addressParts.join(', ')}</span>
          </div>
        `;
      }
    }
    
    // OLD ADDRESS (With districts - smart address)
    else if (selectedSystem === 'old') {
      const houseNumber = $('#full-address-input').val()?.trim();    // OLD: House number in STREET field
      const street = $('#street-autocomplete').val()?.trim();        // From autocomplete
      const ward = $('#ward-hidden-input').val()?.trim();            // From smart address hidden field
      const district = $('#district-hidden-input').val()?.trim();    // From smart address hidden field
      const city = $('input[name="PROVINCECITY"]').val()?.trim();

      if (houseNumber || street || ward || district || city) {
        hasOldAddress = true;
        const addressParts = [];
        
        // Combine house number and street
        if (houseNumber && street) {
          addressParts.push(houseNumber + ', ' + street);
        } else if (houseNumber) {
          addressParts.push(houseNumber);
        } else if (street) {
          addressParts.push(street);
        }
        
        if (ward) addressParts.push(ward);
        if (district) addressParts.push(district);
        if (city) addressParts.push(city);

        previewHTML = `
          <div class="address-preview-section">
            <span class="address-preview-label">
              <i class="fas fa-archive mr-1"></i>Địa chỉ cũ:
            </span>
            <span class="address-preview-value">${addressParts.join(', ')}</span>
          </div>
        `;
      }
    }
    
    // Update preview display
    if (hasNewAddress || hasOldAddress) {
      $preview.html(previewHTML).addClass('has-address');
    } else {
      $preview.html('<span class="text-muted font-italic">Địa chỉ sẽ hiển thị tại đây...</span>')
              .removeClass('has-address');
    }
  }

  // Listen to ALL address inputs including house numbers
  $(document).on('change', '#ward-hidden-input, #ward-hidden-input-new, #district-hidden-input', function() {
    console.log('✓ Smart address updated:', this.id);
    updateAddressPreview();
  });

  // Listen to manual inputs including house numbers
  $(document).on('input change', 
    'input[name="STREET_NEW"], input[name="CITY_NEW"], #street-autocomplete, input[name="PROVINCECITY"], #house-number-new, #full-address-input, #street-input-new', 
    function() {
      updateAddressPreview();
  });
  
  // ==========================================
  // UI ENHANCEMENTS
  // ==========================================
  function initUIEnhancements() {
    console.log(' Init UI...');
    
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