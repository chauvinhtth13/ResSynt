/**
 * Form Validation Error Modal
 * ============================
 * 
 * Simple validation error modal for Django forms.
 * Automatically detects form errors and displays them in a popup.
 * 
 * IMPORTANT: This script checks for changeReasonModal to avoid conflicts
 * with the change-reason-handler.js
 * 
 * === ERROR DETECTION LOGIC ===
 * This script detects 3 types of Django form errors:
 * 
 * 1. INLINE ERRORS (.text-danger)
 *    - Django renders these next to fields with errors
 *    - Example: <small class="text-danger">This field is required</small>
 *    - Backend: form.field.errors in template, or ValidationError in form clean()
 * 
 * 2. INVALID FEEDBACK (.invalid-feedback.d-block)
 *    - Bootstrap's default validation feedback class
 *    - Example: <div class="invalid-feedback d-block">Error message</div>
 *    - Backend: Django form field validation errors
 * 
 * 3. ALERT BOX ERRORS (.alert-danger ul li, .alert-warning ul li)
 *    - Error lists displayed at top of form
 *    - Example: {% if form.errors %}<ul>{% for e in form.errors %}<li>{{ e }}</li>{% endfor %}</ul>
 *    - Backend: form.errors, form.non_field_errors, formset.non_form_errors
 * 
 * === WHEN MODAL SHOWS ===
 * Modal only shows when:
 * 1. Page was loaded via POST request (form was submitted)
 * 2. AND there are validation errors present
 * 
 * This prevents false positives on GET requests (initial page load, edit forms with old data)
 * 
 * Version: 1.3 - Fixed false positive on page load
 */

(function () {
    'use strict';

    const CONFIG = {
        MODAL_ID: 'validationErrorModal',
        ERROR_LIST_ID: 'validationErrorList',
        HIGHLIGHT_DURATION: 2000,
    };

    // Modal HTML template - using standard Bootstrap classes
    const modalTemplate = `
    <div class="modal fade" id="${CONFIG.MODAL_ID}" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content border-0 shadow-lg">
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-exclamation-triangle mr-2"></i> Errors Found
                    </h5>
                </div>
                <div class="modal-body bg-light">
                    <div class="d-flex align-items-center mb-3">
                        <span id="errorCount" class="text-dark me-2" style="font-size: 1rem; font-weight: 700; margin-right: 0.5rem;">0</span>
                        <span class="text-dark" style="font-size: 1rem; font-weight: 700; letter-spacing: 0.3px;">validation errors found</span>
                    </div>
                    <ul class="list-unstyled" id="${CONFIG.ERROR_LIST_ID}"></ul>
                </div>
                <div class="modal-footer bg-white">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
    `;

    const FormValidation = {
        modal: null,
        errors: [],

        init: function () {
            // Inject modal if not exists
            if (!document.getElementById(CONFIG.MODAL_ID)) {
                document.body.insertAdjacentHTML('beforeend', modalTemplate);
            }

            // Get modal instance
            const modalEl = document.getElementById(CONFIG.MODAL_ID);
            if (modalEl && typeof bootstrap !== 'undefined') {
                this.modal = new bootstrap.Modal(modalEl);
            }

            // Add close button handler to properly hide modal and backdrop
            const closeBtn = modalEl ? modalEl.querySelector('[data-dismiss="modal"], [data-bs-dismiss="modal"]') : null;
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.hideModal();
                });
            }

            console.log('[FormValidation] Initialized');
            return true;
        },

        hideModal: function () {
            const modalEl = document.getElementById(CONFIG.MODAL_ID);
            if (!modalEl) return;

            // Try Bootstrap 5 first
            if (this.modal && typeof this.modal.hide === 'function') {
                this.modal.hide();
            }
            // Try Bootstrap 4 / jQuery
            else if (typeof $ !== 'undefined' && typeof $.fn.modal !== 'undefined') {
                $(modalEl).modal('hide');
            }

            // Force remove backdrop and modal-open class after a short delay
            setTimeout(() => {
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) backdrop.remove();
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('padding-right');
                document.body.style.removeProperty('overflow');
                modalEl.classList.remove('show');
                modalEl.style.display = 'none';
            }, 200);
        },

        /**
         * Check if this page was loaded via POST request (form submission)
         * Uses a hidden marker added by Django when form has errors
         */
        isPostRequest: function () {
            // 1. Check for backend marker (most reliable)
            const marker = document.getElementById('django-form-has-errors');
            if (marker) {
                console.log('[FormValidation] POST marker found - showing modal');
                return true;
            }

            // 2. Fallback: check for alert boxes (also reliable)
            const hasAlerts = document.querySelector('.alert-danger, .alert-warning');
            if (hasAlerts) {
                console.log('[FormValidation] Alert boxes found - showing modal');
                return true;
            }

            // 3. Check for errorlist with ID (field-specific errors from Django)
            const hasErrorlist = document.querySelector('.errorlist[id]');
            if (hasErrorlist) {
                console.log('[FormValidation] Errorlist found - showing modal');
                return true;
            }

            console.log('[FormValidation] No POST markers - skipping modal');
            return false;
        },

        /**
         * Try to find the form field element by field name
         * This is used for errors from alert boxes where we only have the field name
         */
        findFieldByName: function (fieldName) {
            if (!fieldName || fieldName === 'Form') return null;

            // Clean the field name
            const cleanName = fieldName.replace(/[^a-zA-Z0-9_]/g, '').toLowerCase();

            // Try to find by id (Django default: id_FIELDNAME)
            let field = document.getElementById('id_' + cleanName);
            if (field) return field;

            // Try case-insensitive match
            field = document.getElementById('id_' + fieldName);
            if (field) return field;

            // Try to find by name attribute
            field = document.querySelector(`[name="${cleanName}"]`);
            if (field) return field;

            field = document.querySelector(`[name="${fieldName}"]`);
            if (field) return field;

            // Try partial match on labels
            const labels = document.querySelectorAll('label');
            for (const label of labels) {
                if (label.textContent.toLowerCase().includes(cleanName)) {
                    const forId = label.getAttribute('for');
                    if (forId) {
                        field = document.getElementById(forId);
                        if (field) return field;
                    }
                    // Or find input in same container
                    const container = label.closest('.form-group, .numbered-item, .mb-3');
                    if (container) {
                        field = container.querySelector('input, select, textarea');
                        if (field) return field;
                    }
                }
            }

            return null;
        },

        collectErrors: function () {
            const errors = [];
            const seenMessages = new Set();

            // 1. Check for inline text-danger errors (not inside alerts and not excluded)
            document.querySelectorAll('.text-danger:not(.alert .text-danger):not(.no-validation-detect)').forEach(el => {
                const text = el.textContent.trim();
                // Skip if hidden or has no-validation-detect parent
                if (el.style.display === 'none' || el.closest('.no-validation-detect')) return;
                if (text && text.length > 2 && !seenMessages.has(text) && !el.closest('.alert')) {
                    const fieldLabel = this.findFieldLabel(el);
                    const targetField = this.findTargetField(el);
                    errors.push({ field: fieldLabel, message: text, element: targetField || el });
                    seenMessages.add(text);
                }
            });

            // 2. Check for invalid-feedback elements
            // 2. Check for invalid-feedback elements
            document.querySelectorAll('.invalid-feedback.d-block').forEach(el => {
                // If the invalid-feedback contains a list (ul/li), iterate the items
                const listItems = el.querySelectorAll('li');
                if (listItems.length > 0) {
                    listItems.forEach(li => {
                        const text = li.textContent.trim();
                        if (text && !seenMessages.has(text)) {
                            const fieldLabel = this.findFieldLabel(el);
                            const targetField = this.findTargetField(el);
                            errors.push({ field: fieldLabel, message: text, element: targetField || el });
                            seenMessages.add(text);
                        }
                    });
                } else {
                    // Fallback for simple text content
                    const text = el.textContent.trim();
                    if (text && !seenMessages.has(text)) {
                        const fieldLabel = this.findFieldLabel(el);
                        const targetField = this.findTargetField(el);
                        errors.push({ field: fieldLabel, message: text, element: targetField || el });
                        seenMessages.add(text);
                    }
                }
            });

            // 3. Check for Django errorlist (field-specific errors)
            // Django structure: <ul class="errorlist"><li>FIELDNAME<ul class="errorlist" id="id_FIELDNAME_error"><li>message</li></ul></li></ul>
            // We only want the INNER errorlist (with ID), not the outer wrapper
            document.querySelectorAll('.errorlist[id]').forEach(el => {
                // Skip if this is inside an alert (we handle those separately)
                if (el.closest('.alert')) return;

                const items = el.querySelectorAll('li');
                items.forEach(li => {
                    const text = li.textContent.trim();
                    if (text && !seenMessages.has(text)) {
                        // Extract field name from errorlist ID (e.g., id_STOOLDATE_error)
                        const errorlistId = el.id;
                        let fieldLabel = 'Field';
                        let targetField = null;

                        if (errorlistId) {
                            // Extract field name from ID like "id_STOOLDATE_error"
                            const match = errorlistId.match(/id_(.+)_error/);
                            if (match) {
                                const fieldName = match[1];
                                targetField = this.findFieldByName(fieldName);
                                if (targetField) {
                                    fieldLabel = this.findFieldLabel(targetField) || fieldName;
                                } else {
                                    fieldLabel = fieldName;
                                }
                            }
                        }

                        errors.push({ field: fieldLabel, message: text, element: targetField || el });
                        seenMessages.add(text);
                    }
                });
            });

            // 4. Check for alert box errors (form-level or non-field errors)
            document.querySelectorAll('.alert-danger ul li, .alert-warning ul li').forEach(el => {
                const text = el.textContent.trim();
                if (text && !seenMessages.has(text)) {
                    const parts = text.split(':');
                    const field = parts.length > 1 ? parts[0].trim() : 'Form';

                    // Try to find the actual field element by name
                    const fieldElement = this.findFieldByName(field);

                    errors.push({
                        field: field,
                        message: text,
                        element: fieldElement  // Now this can be the actual field!
                    });
                    seenMessages.add(text);
                }
            });

            this.errors = errors;
            return errors;
        },

        findFieldLabel: function (errorEl) {
            const formGroup = errorEl.closest('.form-group, .numbered-item, .mb-3, .col-md-6, .col-md-4, .col-md-3, .col-md-12');
            if (formGroup) {
                const label = formGroup.querySelector('label');
                if (label) return label.textContent.replace('*', '').trim();
            }
            return 'Field';
        },

        findTargetField: function (errorEl) {
            const formGroup = errorEl.closest('.form-group, .numbered-item, .mb-3, .col-md-6, .col-md-4, .col-md-3, .col-md-12');
            if (formGroup) {
                return formGroup.querySelector('input, select, textarea') || formGroup;
            }
            return null;
        },

        showErrors: function (errors) {
            if (!errors) errors = this.collectErrors();
            if (errors.length === 0) return;

            // Update error count
            const countEl = document.getElementById('errorCount');
            if (countEl) countEl.textContent = errors.length;

            // Build error list (display only, no click navigation)
            const listEl = document.getElementById(CONFIG.ERROR_LIST_ID);
            if (listEl) {
                listEl.innerHTML = errors.map((err) => `
                    <li class="alert alert-white border mb-2 p-2 shadow-sm rounded">
                        <div class="text-danger font-weight-bold">
                            <i class="fas fa-exclamation-circle mr-1"></i> ${this.escapeHtml(err.field)}
                        </div>
                        <div class="small text-dark mt-1 pl-4">${this.escapeHtml(err.message)}</div>
                    </li>
                `).join('');
            }

            // Show modal
            const modalEl = document.getElementById(CONFIG.MODAL_ID);
            if (modalEl) {
                // Remove aria-hidden when showing to fix accessibility warning
                modalEl.removeAttribute('aria-hidden');
            }
            if (this.modal) this.modal.show();

            console.log('[FormValidation] Showing', errors.length, 'errors');
        },

        goToError: function (index) {
            if (index >= 0 && index < this.errors.length) {
                const error = this.errors[index];

                // Try to find element if not set
                if (!error.element && error.field) {
                    error.element = this.findFieldByName(error.field);
                }

                if (error.element) {
                    if (this.modal) this.modal.hide();
                    setTimeout(() => {
                        // Instant scroll without animation
                        error.element.scrollIntoView({ behavior: 'auto', block: 'center' });
                        // No highlight, no focus
                    }, 200);
                } else {
                    // If no element found, just scroll to first form
                    if (this.modal) this.modal.hide();
                    const form = document.querySelector('form');
                    if (form) {
                        setTimeout(() => {
                            form.scrollIntoView({ behavior: 'auto', block: 'start' });
                        }, 200);
                    }
                }
            }
        },

        goToFirstError: function () {
            this.goToError(0);
        },

        highlightElement: function (element) {
            // Removed all highlight and focus effects
        },

        checkAndShowErrors: function () {
            // IMPORTANT: Only show modal if this is a POST request (form was submitted)
            if (!this.isPostRequest()) {
                console.log('[FormValidation] GET request detected - skipping modal (no form submission yet)');
                return;
            }

            const errors = this.collectErrors();
            console.log('[FormValidation] Collected errors:', errors.length, errors);
            if (errors.length > 0) {
                console.log('[FormValidation] POST request with errors detected - showing modal');
                setTimeout(() => this.showErrors(errors), 300);
            } else {
                console.log('[FormValidation] No errors found in DOM');
            }
        },

        escapeHtml: function (text) {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return String(text).replace(/[&<>"']/g, m => map[m]);
        }
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        if (FormValidation.init() && document.querySelector('form')) {
            FormValidation.checkAndShowErrors();
        }
    });

    // Export to global scope
    window.FormValidation = FormValidation;

})();
