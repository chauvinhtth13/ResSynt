/**
 * Clinical Form JavaScript - Study 43EN
 * Handles conditional sections, calculations, and formset management
 * Version: 3.0 - Fixed formset handlers
 */

console.log(' Clinical form module loaded v3.0');

(function($) {
  'use strict';

  // ========== STATE MANAGEMENT ==========
  const ClinicalForm = {
    state: {
      isReadonly: false,
      isCreate: false,
      enrollmentId: null,
      initialized: false
    },

    init: function() {
      console.log('=== CLINICAL FORM INITIALIZING ===');
      
      // Get state from HTML
      const $form = $('#clinicalForm');
      this.state.isReadonly = $form.attr('data-read-only') === 'true';
      this.state.enrollmentId = $form.attr('data-enrollment-id');
      
      console.log('State:', this.state);

      // Initialize modules in sequence
      setTimeout(() => {
        this.initTabNavigation();
        this.initConditionalSections();
        this.initAutoCalculations();
        this.initFormsets();
        this.initValidation();
        this.initUIEnhancements();
        this.initPage3Conditionals();  // NEW: Page 3 specific logic
        
        this.state.initialized = true;
        console.log(' Clinical form ready');
      }, 100);
    },

    // ========== TAB NAVIGATION ==========
    initTabNavigation: function() {
      console.log(' Init tab navigation...');

      // Scroll to top when tab changes
      $('.custom-tabs .nav-link').on('shown.bs.tab', function(e) {
        const targetTab = $(e.target).attr('href');
        console.log('Tab switched to:', targetTab);
        
        $('html, body').animate({
          scrollTop: $('#clinicalTabs').offset().top - 100
        }, 400);
      });

      // Previous/Next button handlers
      $('[data-tab-action="next"]').on('click', function(e) {
        e.preventDefault();
        const currentTab = $(this).closest('.tab-pane').attr('id');
        let nextTab;
        
        if (currentTab === 'page1') {
          nextTab = '#page2-tab';
        } else if (currentTab === 'page2') {
          nextTab = '#page3-tab';
        }
        
        if (nextTab) {
          console.log('Next button clicked - switching to:', nextTab);
          $(nextTab).tab('show');
        }
      });

      $('[data-tab-action="prev"]').on('click', function(e) {
        e.preventDefault();
        const currentTab = $(this).closest('.tab-pane').attr('id');
        let prevTab;
        
        if (currentTab === 'page2') {
          prevTab = '#page1-tab';
        } else if (currentTab === 'page3') {
          prevTab = '#page2-tab';
        }
        
        if (prevTab) {
          console.log('Previous button clicked - switching to:', prevTab);
          $(prevTab).tab('show');
        }
      });

      // Direct tab click
      $('.custom-tabs .nav-link').on('click', function(e) {
        e.preventDefault();
        const targetTab = $(this).attr('href');
        console.log('Direct tab click:', targetTab);
        $(this).tab('show');
      });

      console.log(' Tab navigation ready');
    },

    // ========== CONDITIONAL SECTIONS ==========
    initConditionalSections: function() {
      console.log(' Init conditional sections...');

      // ===== Other Symptom Toggles =====
      $('#id_OTHERSYMPTOM').on('change', function() {
        $('#othersymptom_detail').toggle(this.checked);
      }).trigger('change');

      $('#id_OTHERSYMPTOM_2').on('change', function() {
        $('#othersymptom_2_detail').toggle(this.checked);
      }).trigger('change');

      // ===== Respiratory Support =====
      $('input[name="RESPISUPPORT"]').on('change', function() {
        const isYes = $(this).val() === 'true' || $(this).val() === '1';
        $('#respi-support-section').toggle(isYes);
      }).filter(':checked').trigger('change');

      // ===== Resuscitation Fluid =====
      $('input[name="RESUSFLUID"]').on('change', function() {
        const isYes = $(this).val() === 'true' || $(this).val() === '1';
        $('#resus-fluid-section').toggle(isYes);
      }).filter(':checked').trigger('change');

      // ===== Vasoinotropes =====
      $('input[name="VASOINOTROPES"]').on('change', function() {
        const isYes = $(this).val() === 'true' || $(this).val() === '1';
        $('#vasodrug-section').toggle(isYes);
      }).filter(':checked').trigger('change');

      // ===== Dialysis =====
      $('input[name="dialysis_radio"]').on('change', function() {
        $('#id_DIALYSIS').prop('checked', $(this).val() === 'yes');
      });

      // ===== Drainage =====
      $('input[name="drainage_radio"]').on('change', function() {
        const isYes = $(this).val() === 'yes';
        $('#id_DRAINAGE').prop('checked', isYes);
        $('#drainage_type_section').toggle(isYes);
      });

      //  Initialize drainage section visibility on page load
      const drainageChecked = $('input[name="drainage_radio"]:checked').val();
      if (drainageChecked === 'yes') {
        $('#drainage_type_section').show();
      } else {
        $('#drainage_type_section').hide();
      }

      //  DRAINAGE TYPE SYNC - Fix validation error
      $('input[name="drainage_type_radio"]').on('change', function() {
        $('#id_DRAINAGETYPE').val($(this).val());
        console.log('Drainage type synced:', $(this).val());
      });

      //  Initialize drainage type radio based on saved value
      const savedDrainageType = $('#id_DRAINAGETYPE').val();
      if (savedDrainageType) {
        $('input[name="drainage_type_radio"][value="' + savedDrainageType + '"]').prop('checked', true);
        console.log('Drainage type initialized from DB:', savedDrainageType);
      }

      // ===== Antibiotics =====
      $('#id_PRIORANTIBIOTIC').on('change', function() {
        $('#prior-antibiotic-section').toggle(this.checked);
      }).trigger('change');

      $('#id_INITIALANTIBIOTIC').on('change', function() {
        $('#initial-antibiotic-section').toggle(this.checked);
      }).trigger('change');

      // ===== Infection Focus =====
      $('#id_INFECTFOCUS48H, select[name="INFECTFOCUS48H"]').on('change', function() {
        $('#infectfocus-other-section').toggle($(this).val() === 'Other');
      }).trigger('change');

      // ===== Respiratory Pattern =====
      $('input[name="RESPPATTERN"]').on('change', function() {
        $('#resppattern_other_detail').toggle($('#id_RESPPATTERN_OTHER').is(':checked'));
      });

      // ===== Adverse Events & Improvements =====
      $('input[name="has_aehospevent"]').on('change', function() {
        $('#aehospevent-formset').toggle($(this).val() === 'yes');
      });

      $('input[name="has_improvesympt"]').on('change', function() {
        $('#improvesympt-formset').toggle($(this).val() === 'yes');
      });

      // ===== Sepsis Scores =====
      $('input[name="BLOODINFECT"]').on('change', function() {
        $('#sepsis-scores-section').toggle($(this).val() === 'yes');
      }).filter(':checked').trigger('change');

      console.log(' Conditional sections ready');
    },

    // ========== AUTO CALCULATIONS ==========
    initAutoCalculations: function() {
      console.log('🧮 Init auto calculations...');

      // ===== BMI Calculation =====
      const calculateBMI = () => {
        const weight = parseFloat($('input[name="WEIGHT"]').val());
        const height = parseFloat($('input[name="HEIGHT"]').val());
        
        if (weight > 0 && height > 0) {
          const heightM = height / 100;
          const bmi = weight / (heightM * heightM);
          //  FIX: Round to 1 decimal place (31.75 → 31.8)
          $('input[name="BMI"]').val(bmi.toFixed(1));
        } else {
          $('input[name="BMI"]').val('');
        }
      };

      $('input[name="WEIGHT"], input[name="HEIGHT"]').on('input change', calculateBMI);

      // ===== GCS Calculation =====
      const calculateGCS = () => {
        const eyes = parseInt($('input[name="EYES"]').val()) || 0;
        const motor = parseInt($('input[name="MOTOR"]').val()) || 0;
        const verbal = parseInt($('input[name="VERBAL"]').val()) || 0;
        
        if (eyes > 0 && motor > 0 && verbal > 0) {
          $('input[name="GCS"]').val(eyes + motor + verbal);
        } else {
          $('input[name="GCS"]').val('');
        }
      };

      $('input[name="EYES"], input[name="MOTOR"], input[name="VERBAL"]').on('input change', calculateGCS);

      // Trigger on load
      calculateBMI();
      calculateGCS();

      console.log(' Auto calculations ready');
    },

    // ========== FORMSET MANAGEMENT ==========
    initFormsets: function() {
      console.log(' Init formsets...');

      // ===== UNIVERSAL ADD BUTTON HANDLER =====
      $(document).on('click', '[data-formset][data-tbody], #add-vasodrug-btn, #add-improvesympt-btn, #add-prior-antibiotic-btn, #add-initial-antibiotic-btn, #add-main-antibiotic-btn', function(e) {
        e.preventDefault();
        
        let formsetPrefix, tbodySelector;
        
        // Check for data attributes first
        if ($(this).data('formset')) {
          formsetPrefix = $(this).data('formset');
          tbodySelector = $(this).data('tbody');
        } else {
          //  UPDATED: Fallback to ID-based mapping with CORRECT prefixes
          const btnId = $(this).attr('id');
          const mapping = {
            'add-vasodrug-btn': {
              prefix: 'vasoidrug_set',  //  Matches backend
              tbody: '#vasodrug-formset-body'
            },
            'add-improvesympt-btn': {
              prefix: 'improvesympt_set',  //  Matches backend
              tbody: '#improvesympt-formset-body'
            },
            'add-prior-antibiotic-btn': {
              prefix: 'priorantibiotic_set',  //  Matches backend
              tbody: '#prior-antibiotic-formset-body'
            },
            'add-initial-antibiotic-btn': {
              prefix: 'initialantibiotic_set',  //  Matches backend
              tbody: '#initial-antibiotic-formset-body'
            },
            'add-main-antibiotic-btn': {
              prefix: 'mainantibiotic_set',  //  Matches backend (NEW)
              tbody: '#main-antibiotic-formset-body'
            }
          };
          
          if (mapping[btnId]) {
            formsetPrefix = mapping[btnId].prefix;
            tbodySelector = mapping[btnId].tbody;
          }
        }
        
        if (!formsetPrefix || !tbodySelector) {
          console.error(' Missing formset configuration');
          return;
        }
        
        ClinicalForm.addFormsetRow($(tbodySelector), formsetPrefix);
      });

      // ===== DELETE ROW HANDLER =====
      //  REMOVED: User requested to delete all DELETE buttons
      // Users will only add new rows, not delete existing ones

      console.log(' Formsets ready');
    },

    addFormsetRow: function($tbody, formsetPrefix) {
      console.log('➕ Adding row to:', formsetPrefix);
      
      if (!$tbody.length) {
        console.error(' Tbody not found');
        alert('Error: Table body not found');
        return;
      }

      // Get TOTAL_FORMS input
      const $totalFormsInput = $(`input[name="${formsetPrefix}-TOTAL_FORMS"]`);
      if (!$totalFormsInput.length) {
        console.error(' TOTAL_FORMS not found for:', formsetPrefix);
        alert('Configuration error: formset management form not found. Please ensure the formset is properly initialized.');
        return;
      }
      
      const currentTotal = parseInt($totalFormsInput.val()) || 0;
      const newIndex = currentTotal;
      
      console.log(`Current forms: ${currentTotal}, New index: ${newIndex}`);

      // Find last visible row to use as template
      const $lastRow = $tbody.find('tr.formset-row:visible').last();
      
      if (!$lastRow.length) {
        console.error(' No template row found');
        alert('Cannot add row: no template available. Please add at least one record first.');
        return;
      }

      // Clone the row
      const $newRow = $lastRow.clone();
      
      // Update all form fields with new index
      $newRow.find(':input, label').each(function() {
        const $el = $(this);
        
        // Update name
        const name = $el.attr('name');
        if (name) {
          const newName = name.replace(/-\d+-/, `-${newIndex}-`);
          $el.attr('name', newName);
          console.log(`Name: ${name} → ${newName}`);
        }
        
        // Update id
        const id = $el.attr('id');
        if (id) {
          const newId = id.replace(/-\d+-/, `-${newIndex}-`);
          $el.attr('id', newId);
        }
        
        // Update for attribute (labels)
        const forAttr = $el.attr('for');
        if (forAttr) {
          const newFor = forAttr.replace(/-\d+-/, `-${newIndex}-`);
          $el.attr('for', newFor);
        }
        
        // Clear values
        if ($el.attr('type') === 'checkbox' || $el.attr('type') === 'radio') {
          if (!name?.includes('DELETE')) {
            $el.prop('checked', false);
          }
        } else if ($el.is('select')) {
          $el.val('');
        } else if ($el.is('textarea') || ($el.is('input') && !$el.attr('readonly'))) {
          $el.val('');
        }
      });

      // Update TOTAL_FORMS
      $totalFormsInput.val(newIndex + 1);
      console.log(`Updated TOTAL_FORMS to: ${newIndex + 1}`);

      // Remove error messages
      $newRow.find('.invalid-feedback, .error').remove();
      $newRow.find('.is-invalid').removeClass('is-invalid');
      $newRow.removeClass('deleted-row');

      // Append
      $newRow.hide().appendTo($tbody).fadeIn(300);

      // Re-init datepickers
      if (typeof $.fn.datepicker !== 'undefined') {
        $newRow.find('.datepicker').datepicker({
          format: 'yyyy-mm-dd',
          autoclose: true,
          todayHighlight: true,
          forceParse: false
        });
      }

      console.log(' Row added successfully');
    },

    // ========== VALIDATION ==========
    initValidation: function() {
      console.log(' Init validation...');

      $('#clinicalForm').on('submit', function(e) {
        let isValid = true;
        const errors = [];

        // GCS validation
        const gcs = parseInt($('input[name="GCS"]').val());
        if (gcs && (gcs < 3 || gcs > 15)) {
          $('input[name="GCS"]').addClass('is-invalid');
          errors.push('GCS score must be between 3 and 15');
          isValid = false;
        }

        // Blood pressure validation
        const sysBP = parseFloat($('input[name="BLOODPRESSURE_SYS"]').val());
        const diasBP = parseFloat($('input[name="BLOODPRESSURE_DIAS"]').val());
        
        if (sysBP && diasBP && diasBP >= sysBP) {
          $('input[name="BLOODPRESSURE_DIAS"]').addClass('is-invalid');
          errors.push('Diastolic BP must be less than Systolic BP');
          isValid = false;
        }

        if (!isValid) {
          e.preventDefault();
          alert('Validation errors:\n' + errors.join('\n'));
          
          // Scroll to first error
          const $firstError = $('.is-invalid:visible').first();
          if ($firstError.length) {
            $('html, body').animate({
              scrollTop: $firstError.offset().top - 150
            }, 500);
          }
        }
      });
    },

    // ========== UI ENHANCEMENTS ==========
    initUIEnhancements: function() {
      console.log(' Init UI enhancements...');

      // Form dirty detection
      if (!this.state.isReadonly) {
        let formDirty = false;
        
        $('#clinicalForm :input').on('change', function() {
          formDirty = true;
        });

        //  FIX: Disable beforeunload when audit modal is shown
        $(window).on('beforeunload', function(e) {
          // Don't show warning if audit modal is visible
          if ($('#changeReasonModal').is(':visible')) {
            return undefined;
          }
          
          if (formDirty) {
            const message = 'You have unsaved changes. Are you sure you want to leave?';
            e.returnValue = message;
            return message;
          }
        });

        $('#clinicalForm').on('submit', function() {
          formDirty = false;
        });
        
        //  NEW: Clear dirty flag when reason confirmed
        $('#confirmReason').on('click', function() {
          formDirty = false;
        });
      }

      console.log(' UI enhancements ready');
    },

    // ========== PAGE 3 CONDITIONAL SECTIONS & SYNC ==========
    initPage3Conditionals: function() {
      console.log('📋 Init Page 3 conditionals...');
      
      // ==========================================
      // SYNC Yes/No radio with formset data on page load
      // ==========================================
      
      const syncRadioWithFormset = (formsetPrefix, radioName, formsetSelector) => {
        console.log(` Syncing ${radioName} with ${formsetPrefix} formset...`);
        
        // Count non-deleted forms with data
        let validFormsCount = 0;
        
        $(`${formsetSelector} tbody tr`).each(function() {
          const deleteCheckbox = $(this).find('input[name$="-DELETE"]');
          const isDeleted = deleteCheckbox.is(':checked');
          
          // Check if form has any data (excluding empty forms)
          let hasData = false;
          $(this).find('input[type="text"], input[type="date"], input[type="number"], select, textarea').each(function() {
            if ($(this).val() && $(this).val().trim() !== '') {
              hasData = true;
              return false; // break
            }
          });
          
          if (!isDeleted && hasData) {
            validFormsCount++;
          }
        });
        
        console.log(`  Valid forms count: ${validFormsCount}`);
        
        // Set radio based on formset data
        if (validFormsCount > 0) {
          $(`input[name="${radioName}"][value="yes"]`).prop('checked', true);
          $(`input[name="${radioName}"][value="no"]`).prop('checked', false);
          $(formsetSelector).show();
          console.log(`   Set ${radioName} to YES (has ${validFormsCount} forms)`);
        } else {
          $(`input[name="${radioName}"][value="no"]`).prop('checked', true);
          $(`input[name="${radioName}"][value="yes"]`).prop('checked', false);
          $(formsetSelector).hide();
          console.log(`  ❌ Set ${radioName} to NO (no forms)`);
        }
      };
      
      // Sync on page load (after short delay to ensure forms are rendered)
      setTimeout(() => {
        syncRadioWithFormset('aehospevent_set', 'has_aehospevent', '#aehospevent-formset');
        syncRadioWithFormset('improvesympt_set', 'has_improvesympt', '#improvesympt-formset');
      }, 100);
      
      // ==========================================
      // Handle conditional sections toggle
      // ==========================================
      
      // Adverse Events
      $('input[name="has_aehospevent"]').on('change', function() {
        if ($(this).val() === 'yes') {
          $('#aehospevent-formset').slideDown();
        } else {
          $('#aehospevent-formset').slideUp();
        }
      });
      
      // Symptom Improvement
      $('input[name="has_improvesympt"]').on('change', function() {
        if ($(this).val() === 'yes') {
          $('#improvesympt-formset').slideDown();
        } else {
          $('#improvesympt-formset').slideUp();
        }
      });
      
      // Infection Focus Other
      $('#id_INFECTFOCUS48H, select[name="INFECTFOCUS48H"]').on('change', function() {
        if ($(this).val() === 'Khác' || $(this).val() === 'Other') {
          $('#infectfocus-other-section').show();
        } else {
          $('#infectfocus-other-section').hide();
        }
      }).trigger('change');
      
      // Bloodstream Infection (Sepsis)
      $('input[name="BLOODSTREAMINFECTION"]').on('change', function() {
        if ($(this).val() === 'True' || $(this).val() === 'true' || $(this).val() === '1') {
          $('#sepsis-scores-section').show();
        } else {
          $('#sepsis-scores-section').hide();
        }
      }).filter(':checked').trigger('change');
      
      // Respiratory Support
      $('input[name="RESPISUPPORTREQ"]').on('change', function() {
        if ($(this).val() === 'True' || $(this).val() === 'true' || $(this).val() === '1') {
          $('#respi-support-section').show();
        } else {
          $('#respi-support-section').hide();
        }
      }).filter(':checked').trigger('change');
      
      // Resuscitation Fluid
      $('input[name="RESUSFLUIDREQ"]').on('change', function() {
        if ($(this).val() === 'True' || $(this).val() === 'true' || $(this).val() === '1') {
          $('#resus-fluid-section').show();
        } else {
          $('#resus-fluid-section').hide();
        }
      }).filter(':checked').trigger('change');
      
      // Vasoinotropes
      $('input[name="VASOINOTROPEREQ"]').on('change', function() {
        if ($(this).val() === 'True' || $(this).val() === 'true' || $(this).val() === '1') {
          $('#vasodrug-section').show();
        } else {
          $('#vasodrug-section').hide();
        }
      }).filter(':checked').trigger('change');
      
      // Prior Antibiotics
      $('input[name="has_prior_antibiotic"]').on('change', function() {
        if ($(this).val() === 'yes') {
          $('#prior-antibiotic-section').slideDown();
        } else {
          $('#prior-antibiotic-section').slideUp();
        }
      });
      
      // Initial Antibiotics
      $('input[name="has_initial_antibiotic"]').on('change', function() {
        if ($(this).val() === 'yes') {
          $('#initial-antibiotic-section').slideDown();
        } else {
          $('#initial-antibiotic-section').slideUp();
        }
      });
      
      console.log(' Page 3 conditionals ready');
    }
  };

  // ========== INITIALIZE ON DOM READY ==========
  $(document).ready(function() {
    ClinicalForm.init();
  });

  // Expose to global scope
  window.ClinicalForm = ClinicalForm;

})(jQuery);