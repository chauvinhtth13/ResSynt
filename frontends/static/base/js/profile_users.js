// frontends/static/js/default/profile_users.js
// Optimized - Uses auth_utils.js and base.js utilities
'use strict';

(() => {
  // Check dependencies
  if (typeof window.ResSyncBase === 'undefined') {
    console.error('[profile_users.js] ResSyncBase not found. Load base.js first.');
    return;
  }

  if (typeof window.ResSyncAuthUtils === 'undefined') {
    console.error('[profile_users.js] ResSyncAuthUtils not found. Load auth_utils.js first.');
    return;
  }

  const { qs, ajax, toast } = window.ResSyncBase;
  const { PasswordStrengthMonitor, PasswordMatchValidator } = window.ResSyncAuthUtils;

  /**
   * Profile Manager - Optimized with shared utilities
   */
  class ProfileManager {
    constructor() {
      // Get all required elements
      this.elements = {
        // Profile form
        profileForm: qs('#profileForm'),
        
        // Password form
        passwordForm: qs('#passwordForm'),
        resetPasswordBtn: qs('#resetPasswordBtn'),
        
        // Email change modal
        changeEmailForm: qs('#changeEmailForm'),
        changeEmailModal: qs('#changeEmailModal'),
        newEmailInput: qs('#newEmail'),
        sendEmailChangeBtn: qs('#sendEmailChangeBtn'),
        sendEmailChangeText: qs('#sendEmailChangeText'),
        sendEmailChangeSpinner: qs('#sendEmailChangeSpinner'),
        emailError: qs('#emailError')
      };
      
      // Check required elements
      if (!this.elements.profileForm || !this.elements.passwordForm) {
        console.warn('[profile_users.js] Required forms not found');
        return;
      }
      
      // Bind methods
      this.handleProfileSubmit = this.handleProfileSubmit.bind(this);
      this.handlePasswordSubmit = this.handlePasswordSubmit.bind(this);
      this.handlePasswordReset = this.handlePasswordReset.bind(this);
      this.handleEmailChangeSubmit = this.handleEmailChangeSubmit.bind(this);
      this.handleEmailModalClose = this.handleEmailModalClose.bind(this);
      
      this.init();
    }

    init() {
      this.initFormHandlers();
      this.initPasswordValidation();
      this.bindEvents();
      console.log('[profile_users.js]  ProfileManager initialized');
    }

    /**
     * Initialize form loading handlers using base.js
     * NOTE: Don't use FormLoadingHandler for AJAX forms - handle loading manually
     */
    initFormHandlers() {
      // Don't use FormLoadingHandler - it interferes with AJAX submissions
      // We'll handle loading states manually in submit handlers
      console.log('[profile_users.js]  Using manual loading states for AJAX forms');
    }

    /**
     * Initialize password validation using auth_utils.js
     */
    initPasswordValidation() {
      // Get username for similarity check
      const getUsernameForValidation = () => {
        const usernameInput = qs('#username');
        return usernameInput ? usernameInput.value : '';
      };

      // Password strength monitor
      this.passwordStrengthMonitor = new PasswordStrengthMonitor(
        'newPassword',
        'passwordHelpText',
        getUsernameForValidation
      );

      // Password match validator
      this.passwordMatchValidator = new PasswordMatchValidator(
        'newPassword',
        'confirmPassword'
      );
      
      console.log('[profile_users.js]  Password validation initialized');
    }

    bindEvents() {
      const { profileForm, passwordForm, resetPasswordBtn, changeEmailForm, changeEmailModal } = this.elements;
      
      // Profile form
      if (profileForm) {
        profileForm.addEventListener('submit', this.handleProfileSubmit);
      }
      
      // Password form
      if (passwordForm) {
        passwordForm.addEventListener('submit', this.handlePasswordSubmit);
      }
      
      // Password reset button
      if (resetPasswordBtn) {
        resetPasswordBtn.addEventListener('click', this.handlePasswordReset);
      }
      
      // Email change form
      if (changeEmailForm) {
        changeEmailForm.addEventListener('submit', this.handleEmailChangeSubmit);
      }
      
      // Email modal close
      if (changeEmailModal) {
        changeEmailModal.addEventListener('hidden.bs.modal', this.handleEmailModalClose);
      }
      
      console.log('[profile_users.js]  Events bound');
    }

    // ============================================
    // PROFILE UPDATE
    // ============================================
    async handleProfileSubmit(e) {
      e.preventDefault();
      e.stopPropagation();
      
      console.log('[profile_users.js] 🔵 Profile form submitted');
      
      const { profileForm } = this.elements;
      const saveBtn = qs('#saveProfileBtn');
      const saveText = qs('#saveProfileText');
      const saveSpinner = qs('#saveProfileSpinner');
      
      // Validate form
      if (!profileForm.checkValidity()) {
        profileForm.reportValidity();
        return;
      }
      
      // Show loading
      this.setLoading(saveBtn, saveText, saveSpinner, true);
      
      try {
        const formData = new FormData(profileForm);
        const action = profileForm.getAttribute('action');
        
        console.log('[profile_users.js] 📤 POST to:', action);
        
        const response = await ajax.post(action, formData);
        
        console.log('[profile_users.js] 📥 Response:', response);
        
        if (response.success || response.status === 'success') {
          toast.success('Profile updated successfully');
          
          // Reload page to show updated data
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          throw new Error(response.message || 'Update failed');
        }
      } catch (error) {
        console.error('[profile_users.js]  Error:', error);
        toast.error(error.message || 'Failed to update profile');
        this.setLoading(saveBtn, saveText, saveSpinner, false);
      }
    }

    // ============================================
    // PASSWORD CHANGE
    // ============================================
    async handlePasswordSubmit(e) {
      e.preventDefault();
      e.stopPropagation();
      
      console.log('[profile_users.js] 🔵 Password form submitted');
      
      const { passwordForm } = this.elements;
      const changeBtn = qs('#changePasswordBtn');
      const changeText = qs('#changePasswordText');
      const changeSpinner = qs('#changePasswordSpinner');
      
      // Validate form
      if (!passwordForm.checkValidity()) {
        passwordForm.reportValidity();
        return;
      }
      
      // Check password match
      const newPassword = qs('#newPassword')?.value;
      const confirmPassword = qs('#confirmPassword')?.value;
      
      if (newPassword !== confirmPassword) {
        toast.error('Passwords do not match');
        return;
      }
      
      // Show loading
      this.setLoading(changeBtn, changeText, changeSpinner, true);
      
      try {
        const formData = new FormData(passwordForm);
        const action = passwordForm.getAttribute('action');
        
        const response = await ajax.post(action, formData);
        
        if (response.success || response.status === 'success') {
          toast.success('Password updated successfully');
          passwordForm.reset();
          this.handlePasswordReset();
          passwordForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
          throw new Error(response.message || 'Update failed');
        }
      } catch (error) {
        console.error('[profile_users.js]  Password error:', error);
        toast.error(error.message || 'Failed to update password');
      } finally {
        this.setLoading(changeBtn, changeText, changeSpinner, false);
      }
    }

    handlePasswordReset() {
      const { passwordForm } = this.elements;
      
      // Clear password strength bar
      const passwordStrengthBar = qs('#passwordStrengthBar');
      if (passwordStrengthBar) {
        passwordStrengthBar.style.width = '0%';
        passwordStrengthBar.style.backgroundColor = '';
      }
      
      // Reset help text
      const passwordHelpText = qs('#passwordHelpText');
      if (passwordHelpText) {
        passwordHelpText.textContent = 'Password must be at least 8 characters';
        passwordHelpText.style.color = '';
      }
      
      // Clear password match error
      const passwordMatchError = qs('#passwordMatchError');
      if (passwordMatchError) {
        passwordMatchError.classList.add('d-none');
      }
      
      // Remove validation classes
      if (passwordForm) {
        passwordForm.querySelectorAll('.form-control').forEach(input => {
          input.classList.remove('is-valid', 'is-invalid');
        });
      }
      
      console.log('[profile_users.js] Password form reset');
    }

    // ============================================
    // EMAIL CHANGE
    // ============================================
    async handleEmailChangeSubmit(e) {
      e.preventDefault();
      e.stopPropagation();
      
      console.log('[profile_users.js] 🔵 Email change form submitted');
      
      const { changeEmailForm, newEmailInput, sendEmailChangeBtn, 
              sendEmailChangeText, sendEmailChangeSpinner, changeEmailModal } = this.elements;
      
      const newEmail = newEmailInput.value.trim();
      
      // Clear errors
      this.clearEmailError();
      
      // Validate email
      if (!newEmail) {
        this.showEmailError('Please enter a new email address');
        return;
      }
      
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(newEmail)) {
        this.showEmailError('Please enter a valid email address');
        return;
      }
      
      // Show loading
      this.setLoading(sendEmailChangeBtn, sendEmailChangeText, sendEmailChangeSpinner, true);
      
      try {
        const formData = new FormData(changeEmailForm);
        const response = await ajax.post('/profile/request-email-change/', formData);
        
        if (response.success) {
          // Close modal
          const modalInstance = bootstrap.Modal.getInstance(changeEmailModal);
          if (modalInstance) modalInstance.hide();
          
          toast.success(response.message || 'Confirmation email sent! Check your inbox.');
          changeEmailForm.reset();
        } else {
          throw new Error(response.message || 'Failed to send email');
        }
      } catch (error) {
        console.error('[profile_users.js]  Email error:', error);
        this.showEmailError(error.message || 'An error occurred');
      } finally {
        this.setLoading(sendEmailChangeBtn, sendEmailChangeText, sendEmailChangeSpinner, false);
      }
    }

    showEmailError(message) {
      const { newEmailInput, emailError } = this.elements;
      if (newEmailInput) newEmailInput.classList.add('is-invalid');
      if (emailError) emailError.textContent = message;
    }

    clearEmailError() {
      const { newEmailInput, emailError } = this.elements;
      if (newEmailInput) newEmailInput.classList.remove('is-invalid');
      if (emailError) emailError.textContent = '';
    }

    handleEmailModalClose() {
      const { changeEmailForm } = this.elements;
      if (changeEmailForm) changeEmailForm.reset();
      this.clearEmailError();
    }

    // ============================================
    // UTILITIES
    // ============================================
    
    /**
     * Set loading state for email change button
     * Note: Profile and Password forms use FormLoadingHandler from base.js
     */
    setLoading(button, textEl, spinnerEl, isLoading) {
      if (!button) return;
      
      button.disabled = isLoading;
      
      if (textEl && spinnerEl) {
        if (isLoading) {
          textEl.classList.add('d-none');
          spinnerEl.classList.remove('d-none');
        } else {
          textEl.classList.remove('d-none');
          spinnerEl.classList.add('d-none');
        }
      }
    }
  }

  // ============================================
  // INITIALIZE
  // ============================================
  let instance = null;
  
  const init = () => {
    // Prevent multiple instances
    if (instance) {
      console.warn('[profile_users.js]  Already initialized');
      return;
    }
    
    instance = new ProfileManager();
  };

  // Register with base.js
  if (window.ResSyncBase && window.ResSyncBase.registerInit) {
    window.ResSyncBase.registerInit(init);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();