/**
 * Authentication Module - ResSync Platform
 * Handles password visibility toggle, form submission states, and auto-dismiss alerts
 */

(function () {
    'use strict';

    // =============================================
    // IMMEDIATE: Prevent Form Resubmission
    // Must run BEFORE DOMContentLoaded to prevent POST on refresh
    // =============================================

    if (window.history.replaceState) {
        window.history.replaceState(null, '', window.location.href);
    }

    // =============================================
    // IMMEDIATE: Clear Password Fields on Load
    // Prevents browser from caching/restoring password values
    // which could trigger form resubmission with credentials
    // =============================================

    // Clear password fields as early as possible
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('input[type="password"]').forEach(function(input) {
            input.value = '';
            // Also set autocomplete to prevent browser fill on refresh
            input.setAttribute('autocomplete', 'new-password');
        });
    });

    // Also clear on pageshow (handles bfcache scenarios)
    window.addEventListener('pageshow', function(e) {
        if (e.persisted) {
            document.querySelectorAll('input[type="password"]').forEach(function(input) {
                input.value = '';
            });
        }
    });

    // =============================================
    // Password Toggle
    // =============================================

    window.togglePassword = function (button) {
        const wrapper = button.closest('.input-icon-wrapper');
        if (!wrapper) return;

        const input = wrapper.querySelector('input[type="password"], input[type="text"]');
        const icon = button.querySelector('i');
        if (!input || !icon) return;

        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        icon.classList.toggle('fa-eye-slash', !isPassword);
        icon.classList.toggle('fa-eye', isPassword);
        button.setAttribute('aria-pressed', String(isPassword));
        input.focus();
    };

    // =============================================
    // Form Submit Handler
    // =============================================

    function initFormSubmit() {
        document.querySelectorAll('.auth-card form').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                const btn = form.querySelector('button[type="submit"]');
                if (!btn || !form.checkValidity()) {
                    if (!form.checkValidity()) e.preventDefault();
                    return;
                }

                btn.disabled = true;
                const text = btn.querySelector('.btn-text');
                const loading = btn.querySelector('.btn-loading');
                if (text) text.classList.add('d-none');
                if (loading) loading.classList.remove('d-none');
            });
        });
    }

    // =============================================
    // Auto-Dismiss Alerts (30s)
    // =============================================

    function initAlertAutoDismiss() {
        document.querySelectorAll('.auth-card .alert').forEach(function (alert) {
            // Skip lockout alerts (critical - must stay visible)
            if (alert.querySelector('.bi-shield-lock-fill')) return;

            setTimeout(function () {
                alert.style.transition = 'opacity 0.3s ease-out';
                alert.style.opacity = '0';
                setTimeout(function () {
                    alert.remove();
                }, 100);
            }, 10000);
        });
    }

    // =============================================
    // Unsaved Form Data Warning
    // =============================================

    function initUnsavedDataWarning() {
        let formHasData = false;

        document.querySelectorAll('.auth-card form').forEach(function (form) {
            // Track if form has any user input
            form.addEventListener('input', function () {
                formHasData = Array.from(form.querySelectorAll('input:not([type="hidden"])')).some(function (input) {
                    return input.value.trim() !== '';
                });
            });

            // Clear flag on successful submit
            form.addEventListener('submit', function () {
                formHasData = false;
            });
        });

        // Only show warning if form has data
        window.addEventListener('beforeunload', function (e) {
            if (formHasData) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    // =============================================
    // Initialize
    // =============================================

    document.addEventListener('DOMContentLoaded', function () {
        // Password toggle keyboard support
        document.querySelectorAll('.password-toggle-btn').forEach(function (btn) {
            btn.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    window.togglePassword(this);
                }
            });
        });

        initFormSubmit();
        initAlertAutoDismiss();
        initUnsavedDataWarning();
    });

    // Reset buttons on back navigation (bfcache)
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) {
            document.querySelectorAll('.auth-card button[type="submit"]').forEach(function (btn) {
                btn.disabled = false;
                var text = btn.querySelector('.btn-text');
                var loading = btn.querySelector('.btn-loading');
                if (text) text.classList.remove('d-none');
                if (loading) loading.classList.add('d-none');
            });
        }
    });

})();