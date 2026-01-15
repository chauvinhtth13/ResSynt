/**
 * screening-form.js
 * JavaScript cho Screening Form (study_43en)
 * Chỉ xử lý UI interactions - Backend xử lý validation
 */

(function() {
  'use strict';
  
  // Global variables
  var isReadonly = false;
  var isCreate = false;
  
  // ========================================
  // ELIGIBILITY CHECKING
  // ========================================
  function checkEligibilityCriteria() {
    var upper16age = $('input[name="UPPER16AGE"]:checked').val();
    var infprior = $('input[name="INFPRIOR2OR48HRSADMIT"]:checked').val();
    var isolated = $('input[name="ISOLATEDKPNFROMINFECTIONORBLOOD"]:checked').val();
    var untreated = $('input[name="KPNISOUNTREATEDSTABLE"]:checked').val();

    var eligible = (upper16age === '1' && infprior === '1' && isolated === '1' && untreated === '0');

    var statusDiv = $('.eligibility-status');
    
    if (upper16age && infprior && isolated && untreated) {
      statusDiv.show();
      
      if (eligible) {
        statusDiv.removeClass('not-eligible').addClass('eligible')
          .html('<i class="fas fa-check-circle mr-2"></i> Patient is eligible for the study');
      } else {
        statusDiv.removeClass('eligible').addClass('not-eligible')
          .html('<i class="fas fa-times-circle mr-2"></i> Patient is not eligible for the study');
        
        // Auto-select "No" for consent if not eligible
        $('#id_CONSENTTOSTUDY_0').prop('checked', true);
      }
      
      updateNextStepInfo();
    } else {
      statusDiv.hide();
      $('#nextStepInfo').addClass('d-none');
    }
  }

  function updateNextStepInfo() {
    var upper16age = $('input[name="UPPER16AGE"]:checked').val();
    var infprior = $('input[name="INFPRIOR2OR48HRSADMIT"]:checked').val();
    var isolated = $('input[name="ISOLATEDKPNFROMINFECTIONORBLOOD"]:checked').val();
    var untreated = $('input[name="KPNISOUNTREATEDSTABLE"]:checked').val();
    var consent = $('input[name="CONSENTTOSTUDY"]:checked').val();

    var eligible = (upper16age === '1' && infprior === '1' && isolated === '1' && untreated === '0');

    if (eligible && consent === '1') {
      $('#nextStepInfo').removeClass('d-none');
      $('#submitButton')
        .removeClass('btn-primary')
        .addClass('btn-success btn-pulse')
        .html('<i class="fas fa-arrow-circle-right mr-1"></i> Save & Continue');
    } else {
      $('#nextStepInfo').addClass('d-none');
      $('#submitButton')
        .removeClass('btn-success btn-pulse')
        .addClass('btn-primary')
        .html('<i class="fas fa-save mr-1"></i> Save');
    }
  }
  
  // ========================================
  // SET DEFAULT RADIO VALUES
  // ========================================
  function setDefaultRadioValues() {
    var criteriaFields = [
      'UPPER16AGE', 
      'INFPRIOR2OR48HRSADMIT', 
      'ISOLATEDKPNFROMINFECTIONORBLOOD', 
      'KPNISOUNTREATEDSTABLE', 
      'CONSENTTOSTUDY'
    ];
    
    criteriaFields.forEach(function(fieldName) {
      if (!$('input[name="' + fieldName + '"]:checked').length) {
        $('#id_' + fieldName + '_0').prop('checked', true);
      }
    });
  }
  
  // ========================================
  // EVENT HANDLERS
  // ========================================
  function initEventHandlers() {
    // Eligibility criteria change
    $('input[name="UPPER16AGE"], input[name="INFPRIOR2OR48HRSADMIT"], input[name="ISOLATEDKPNFROMINFECTIONORBLOOD"], input[name="KPNISOUNTREATEDSTABLE"]')
      .change(function() {
        checkEligibilityCriteria();
      });
    
    // Consent change
    $('input[name="CONSENTTOSTUDY"]').change(function() {
      updateNextStepInfo();
    });
    
    // Reset button
    $('.btn-reset').click(function() {
      setTimeout(function() {
        setDefaultRadioValues();
        checkEligibilityCriteria();
        $('.eligibility-status').hide();
        $('#nextStepInfo').addClass('d-none');
        $('#submitButton')
          .removeClass('btn-success btn-pulse')
          .addClass('btn-primary')
          .html('<i class="fas fa-save mr-1"></i> Save');
      }, 10);
    });
  }
  
  // ========================================
  // INITIALIZATION
  // ========================================
  function init() {
    console.log('🔍 Screening form init - readonly:', isReadonly, 'create:', isCreate);
    
    setDefaultRadioValues();
    checkEligibilityCriteria();
    
    // Highlight required fields
    $('input[required]:not([type="radio"]), select[required]')
      .closest('.form-group')
      .addClass('required-field');
    
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    initEventHandlers();
    
    console.log(' Screening form initialized');
  }
  
  // ========================================
  // DOCUMENT READY
  // ========================================
  $(document).ready(function() {
    // Get state from template
    if (typeof window.screeningFormState !== 'undefined') {
      isReadonly = window.screeningFormState.isReadonly || false;
      isCreate = window.screeningFormState.isCreate || false;
    }
    
    init();
  });
  
})();