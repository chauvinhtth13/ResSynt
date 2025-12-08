// frontends/static/js/default/auth_pages.js
// Combined authentication pages logic (login, password reset, etc.)
// Requires: auth_utils.js

(() => {
  'use strict';

  // ========================================
  // Login Page Handler
  // ========================================
  class LoginPageHandler {
    constructor() {
      // Check if we're on the login page
      this.passwordInput = document.getElementById('passwordInput');
      
      if (!this.passwordInput) {
        return; // Not on login page
      }
      
      this.init();
    }

    init() {
      // Initialize password toggle for login page
      new ResSyncAuthUtils.PasswordToggle({
        inputId: 'passwordInput',
        toggleId: 'togglePassword',
        iconId: 'toggleIcon'
      });
      
      console.log('[LoginPage] Initialized');
    }
  }

  // ========================================
  // Password Reset Page Handler
  // ========================================
  class PasswordResetPageHandler {
    constructor() {
      // Check if we're on the password reset page
      this.passwordInput1 = document.getElementById('new_password1');
      
      if (!this.passwordInput1) {
        return; // Not on password reset page
      }
      
      this.init();
    }

    init() {
      // Initialize password toggles for both password fields
      ResSyncAuthUtils.initPasswordToggles([
        {
          inputId: 'new_password1',
          toggleId: 'togglePassword1',
          iconId: 'toggleIcon1'
        },
        {
          inputId: 'new_password2',
          toggleId: 'togglePassword2',
          iconId: 'toggleIcon2'
        }
      ]);

      // Get username if available (might be in hidden field or data attribute)
      const getUsernameForValidation = () => {
        // Try to get username from various sources
        const usernameInput = document.getElementById('id_username') || 
                             document.querySelector('[name="username"]');
        if (usernameInput) return usernameInput.value;
        
        // Try from data attribute
        const usernameData = document.body.dataset.username;
        if (usernameData) return usernameData;
        
        return '';
      };

      // Initialize password strength monitor with username checking
      new ResSyncAuthUtils.PasswordStrengthMonitor(
        'new_password1',
        'passwordStrength',
        getUsernameForValidation  // Pass function to get username dynamically
      );

      // Initialize password match validator
      new ResSyncAuthUtils.PasswordMatchValidator(
        'new_password1',
        'new_password2'
      );

      // Initialize form loading handler (using base.js utility)
      if (window.ResSyncBase && window.ResSyncBase.FormLoadingHandler) {
        new ResSyncBase.FormLoadingHandler({
          formId: 'setPasswordForm',
          submitBtnId: 'submitBtn',
          btnTextId: 'btnText',
          loadingText: 'Processing...'
        });
      }
      
      console.log('[PasswordResetPage] Initialized with Django-synced validation');
    }
  }

  // ========================================
  // Password Reset Request Form Handler (form.html - Forgot Password)
  // ========================================
  class PasswordResetFormHandler {
    constructor() {
      // Check if we're on the forgot password form page
      this.form = document.getElementById('resetPasswordForm');
      
      if (!this.form) {
        return; // Not on forgot password page
      }
      
      this.init();
    }

    init() {
      // Initialize form loading handler (using base.js utility)
      if (window.ResSyncBase && window.ResSyncBase.FormLoadingHandler) {
        new ResSyncBase.FormLoadingHandler({
          formId: 'resetPasswordForm',
          submitBtnId: 'submitBtn',
          btnTextId: 'btnText',
          loadingText: 'Sending...'
        });
      }
      
      console.log('[PasswordResetFormPage] Initialized');
    }
  }

  // ========================================
  // Auto-Initialize on DOM Ready
  // ========================================
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize appropriate handler based on page
    // Each handler checks if it's on the correct page
    new LoginPageHandler();
    new PasswordResetPageHandler();
    new PasswordResetFormHandler();
  });

})();