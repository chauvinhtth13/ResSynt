/**
 * contact-enrollment-form.js - Contact Enrollment Form v1.0
 * ONLY UI interactions - NO validation (backend handles it)
 * 
 * Differences from Patient:
 * - RELATIONSHIP field
 * - SPECIFYIFOTHERETHNI field
 * - ThreeStateChoices for risk factors (yes/no/unknown)
 * - No hospital transfer section
 * - No geographic fields (WARD, DISTRICT, PROVINCECITY)
 */

(function() {
  'use strict';
  
  const state = {
    isReadonly: false,
    isCreate: false,
    initialized: false
  };
  
  $(document).ready(function() {
    console.log(' Contact enrollment form initializing...');
    
    state.isReadonly = window.contactEnrollmentFormState?.isReadonly || false;
    state.isCreate = window.contactEnrollmentFormState?.isCreate || false;
    
    // Initialize modules
    initConditionalSections();
    initAgeCalculation();
    initMedicationFormset();
    initUIEnhancements();
    
    state.initialized = true;
    console.log(' Contact enrollment form ready');
  });
  
  // ==========================================
  // CONDITIONAL SECTIONS - Simple show/hide
  // ==========================================
  function initConditionalSections() {
    console.log(' Init conditional sections...');
    
    //  CONTACT-SPECIFIC: Other ethnicity specification
    $('#id_ETHNICITY').on('change', function() {
      const val = $(this).val();
      const show = val === 'Other' || val === 'other';
      
      $('#other-ethnicity-section').toggle(show);
      console.log('🌍 Other ethnicity:', show ? 'show' : 'hide');
      
      // Clear field if hiding
      if (!show) {
        $('#id_SPECIFYIFOTHERETHNI').val('');
      }
    }).trigger('change');
    
    //  Medication history (ThreeStateChoices)
    $('input[name="CORTICOIDPPI"]').on('change', function() {
      const show = $('input[name="CORTICOIDPPI"]:checked').val() === 'yes';
      
      $('#medication-history-section').toggle(show);
      console.log(' Medication:', show ? 'show' : 'hide');
      
      // If hiding, clear medication formset
      if (!show && !state.isReadonly) {
        // Keep management form but remove extra rows
        const initialForms = parseInt($('input[name="medhisdrug_set-INITIAL_FORMS"]').val()) || 0;
        const totalForms = parseInt($('input[name="medhisdrug_set-TOTAL_FORMS"]').val()) || 0;
        
        // Remove rows beyond initial forms
        $('#medication-formset-body tr.formset-row').each(function(index) {
          if (index >= initialForms) {
            $(this).remove();
          }
        });
        
        // Update TOTAL_FORMS to match INITIAL_FORMS
        $('input[name="medhisdrug_set-TOTAL_FORMS"]').val(initialForms);
      }
    }).trigger('change');
    
    //  Underlying conditions
    $('input[name="UNDERLYINGCONDS"]').on('change', function() {
      const show = $('input[name="UNDERLYINGCONDS"]:checked').val() === 'True';
      
      $('#underlying-conditions-section').toggle(show);
      console.log('🩺 Underlying conditions:', show ? 'show' : 'hide');
      
      // If hiding, uncheck all underlying checkboxes
      if (!show) {
        $('#underlying-conditions-section input[type="checkbox"]').prop('checked', false);
        $('#id_OTHERDISEASESPECIFY').val('');
        $('#other-disease-detail').hide();
      }
    }).trigger('change');
    
    //  Other disease specification
    $('#id_OTHERDISEASE').on('change', function() {
      $('#other-disease-detail').toggle(this.checked);
      console.log('📝 Other disease:', this.checked ? 'show' : 'hide');
      
      // Clear field if unchecking
      if (!this.checked) {
        $('#id_OTHERDISEASESPECIFY').val('');
      }
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
    const $display = $('#calculated-age-contact');
    
    if (!$day.length || !$display.length) {
      console.log(' Age calculation fields not found');
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
        
        // Basic validation
        if (birth > today) {
          $display.html('<i class="fas fa-exclamation-triangle text-warning"></i><span class="ml-2 text-warning">Future date</span>');
          return;
        }
        
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
          age--;
        }
        
        // Display result
        $display.html(`<i class="fas fa-check-circle text-success"></i><span class="ml-2"><strong>${age} years old</strong></span>`);
        console.log('🎂 Calculated age:', age);
        
      } catch (e) {
        $display.html('<i class="fas fa-times-circle text-danger"></i><span class="ml-2 text-danger">Invalid date</span>');
        console.error('Age calculation error:', e);
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
    const $initialInput = $('input[name="medhisdrug_set-INITIAL_FORMS"]');
    
    if (!$tbody.length) {
      console.log(' Medication tbody not found');
      return;
    }
    
    if (!$totalInput.length) {
      console.error(' medhisdrug_set-TOTAL_FORMS not found!');
      return;
    }
    
    console.log(' Formset state:', {
      total: $totalInput.val(),
      initial: $initialInput.val(),
      prefix: 'medhisdrug_set'
    });
    
    //  Add row button
    if ($addBtn.length && !state.isReadonly) {
      $addBtn.on('click', function() {
        const total = parseInt($totalInput.val()) || 0;
        
        // Limit to 20 medications
        if (total >= 20) {
          alert('Maximum 20 medications allowed');
          console.warn(' Maximum medications reached');
          return;
        }
        
        //  CRITICAL: Proper Django formset format with prefix
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
                     placeholder="Drug name">
            </td>
            <td>
              <input type="text" 
                     name="medhisdrug_set-${total}-DOSAGE" 
                     id="id_medhisdrug_set-${total}-DOSAGE"
                     class="form-control form-control-sm" 
                     placeholder="e.g., 500mg">
            </td>
            <td>
              <input type="text" 
                     name="medhisdrug_set-${total}-USAGETIME" 
                     id="id_medhisdrug_set-${total}-USAGETIME"
                     class="form-control form-control-sm" 
                     placeholder="e.g., 2 weeks">
            </td>
            <td>
              <textarea name="medhisdrug_set-${total}-USAGEREASON" 
                        id="id_medhisdrug_set-${total}-USAGEREASON"
                        class="form-control form-control-sm" 
                        rows="2" 
                        placeholder="Medical condition"></textarea>
            </td>
          </tr>
        `;
        
        $tbody.append(html);
        $totalInput.val(total + 1);
        
        console.log(' Added medication row', total + 1);
        
        // Auto-focus on drug name field
        $(`#id_medhisdrug_set-${total}-DRUGNAME`).focus();
      });
    }
    
    console.log(' Medication formset ready');
  }
  
  // ==========================================
  // UI ENHANCEMENTS
  // ==========================================
  function initUIEnhancements() {
    console.log('🎨 Init UI enhancements...');
    
    //  Ethnicity autocomplete
    const $ethnicity = $('#id_ETHNICITY');
    if ($ethnicity.length && typeof Awesomplete !== 'undefined') {
      new Awesomplete($ethnicity[0], {
        list: [
          "Kinh", "Hoa", "Thái", "Chăm", "Tày", "Mường", 
          "H'Mông", "Khơ-me", "Nùng", "Dao", "Gia Rai", 
          "Ê Đê", "Ba Na", "Sán Chay", "Cơ Ho", "Other"
        ],
        minChars: 0,
        maxItems: 15,
        autoFirst: true
      });
      
      console.log('📝 Ethnicity autocomplete enabled');
    }
    
    //  Relationship autocomplete
    const $relationship = $('#id_RELATIONSHIP');
    if ($relationship.length && typeof Awesomplete !== 'undefined') {
      new Awesomplete($relationship[0], {
        list: [
          "Spouse", "Child", "Parent", "Sibling", 
          "Grandparent", "Grandchild", "Uncle/Aunt", 
          "Nephew/Niece", "Cousin", "Friend", "Caregiver", "Other"
        ],
        minChars: 0,
        maxItems: 15,
        autoFirst: true
      });
      
      console.log('👥 Relationship autocomplete enabled');
    }
    
    //  Occupation autocomplete
    const $occupation = $('#id_OCCUPATION');
    if ($occupation.length && typeof Awesomplete !== 'undefined') {
      new Awesomplete($occupation[0], {
        list: [
          "Student", "Teacher", "Doctor", "Nurse", "Engineer", 
          "Farmer", "Worker", "Business owner", "Office staff", 
          "Driver", "Retired", "Unemployed", "Other"
        ],
        minChars: 0,
        maxItems: 15,
        autoFirst: true
      });
      
      console.log('💼 Occupation autocomplete enabled');
    }
    
    //  Read-only mode
    if (state.isReadonly) {
      console.log('Applying read-only mode...');
      
      $('input, select, textarea').not('[type="hidden"]').prop('disabled', true);
      $('button[type="submit"]').hide();
      $('.btn-success, .btn-danger').hide();
      
      console.log(' Read-only mode applied');
    }
    
    //  Form styling enhancements
    $('input[required]').closest('.form-group').find('label').append(' <span class="text-danger">*</span>');
    
    //  Smooth scroll to errors
    if ($('.alert-danger').length) {
      $('html, body').animate({
        scrollTop: $('.alert-danger').offset().top - 100
      }, 500);
    }
    
    console.log(' UI enhancements ready');
  }
  
  // ==========================================
  // UTILITY FUNCTIONS
  // ==========================================
  
  /**
   * Get form data summary for logging
   */
  function getFormSummary() {
    return {
      usubjid: $('#contactEnrollmentForm').data('screening-id'),
      relationship: $('#id_RELATIONSHIP').val(),
      hasEthnicity: $('#id_ETHNICITY').val() ? 'yes' : 'no',
      hasAge: $('#id_AGEIFDOBUNKNOWN').val() || 'calculated',
      hasUnderlying: $('input[name="UNDERLYINGCONDS"]:checked').val() === 'True',
      medicationCount: $('#medication-formset-body tr.formset-row').length
    };
  }
  
  /**
   * Log form state (for debugging)
   */
  function logFormState() {
    if (window.location.search.includes('debug=1')) {
      console.log(' Contact Enrollment Form State:', {
        initialized: state.initialized,
        readonly: state.isReadonly,
        create: state.isCreate,
        summary: getFormSummary()
      });
    }
  }
  
  // Log on load
  $(window).on('load', logFormState);
  
  console.log(' Contact enrollment form module loaded');
  
})();