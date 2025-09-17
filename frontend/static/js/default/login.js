// frontend\static\js\default\login.js
(() => {
  class ResSyncLoginForm {
    constructor() {
      this.form = document.getElementById('loginForm');
      if (!this.form) {
        console.warn('[login.js] Login form not found');
        return;
      }

      const username = document.getElementById('username');
      const password = document.getElementById('password');
      const toggle = document.getElementById('passwordToggle');
      const eyeOn = document.getElementById('eyeOn');
      const eyeOff = document.getElementById('eyeOff');
      const submit = this.form.querySelector('.submit-btn');
      // Lấy error elements
      const usernameError = document.getElementById('username-error');
      const passwordError = document.getElementById('password-error');

      this.elements = { username, password, toggle, eyeOn, eyeOff, submit, usernameError, passwordError };
      this.isSubmitting = false;

      if (!password || !submit || !username) {
        console.warn('[login.js] Missing form elements:', { username, password, submit });
        return;
      }

      if (password.type === 'password') {
        eyeOn?.classList.add('hidden');
        eyeOff?.classList.remove('hidden');
      } else {
        eyeOn?.classList.remove('hidden');
        eyeOff?.classList.add('hidden');
      }

      if (toggle?.tagName === 'BUTTON' && toggle.getAttribute('type') !== 'button') {
        toggle.setAttribute('type', 'button');
      }
      if (toggle && !toggle.hasAttribute('aria-controls') && password.id) {
        toggle.setAttribute('aria-controls', password.id);
        toggle.setAttribute('aria-label', window.trans?.('Show password') || 'Show password');
      }

      this.bind();
      this.restoreIfFromBFCache();
    }

    bind() {
      const { form, elements } = this;
      const { toggle, username, password, usernameError, passwordError } = elements;

      toggle?.addEventListener('click', () => this.togglePassword());
      toggle?.addEventListener('keydown', (e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          this.togglePassword();
        }
      }, { passive: true });

      form.addEventListener('submit', (e) => this.handleSubmit(e));

      username?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !username.value) e.preventDefault();
      }, { passive: true });

      // Event listeners để clear error realtime khi input thay đổi
      username?.addEventListener('input', () => {
        if (username.value.trim() !== '') {
          this.clearFieldError(username, usernameError);
        }
      });

      password?.addEventListener('input', () => {
        if (password.value.trim() !== '') {
          this.clearFieldError(password, passwordError);
        }
      });

      // Focus/Blur handling để chuyển border màu khi focus
      username?.addEventListener('focus', () => {
        if (username.getAttribute('aria-invalid') === 'true') {
          username.classList.remove('border-red-400');
          username.classList.add('border-blue-500');
        }
      });

      username?.addEventListener('blur', () => {
        if (username.getAttribute('aria-invalid') === 'true' && !username.value.trim()) {
          username.classList.remove('border-blue-500');
          username.classList.add('border-red-400');
        }
      });

      password?.addEventListener('focus', () => {
        if (password.getAttribute('aria-invalid') === 'true') {
          password.classList.remove('border-red-400');
          password.classList.add('border-blue-500');
        }
      });

      password?.addEventListener('blur', () => {
        if (password.getAttribute('aria-invalid') === 'true' && !password.value.trim()) {
          password.classList.remove('border-blue-500');
          password.classList.add('border-red-400');
        }
      });
    }

    togglePassword() {
      const { password, toggle, eyeOn, eyeOff } = this.elements;
      if (!password || !toggle) return;

      const isVisible = password.type === 'text';
      password.type = isVisible ? 'password' : 'text';
      toggle.setAttribute('aria-pressed', String(!isVisible));
      toggle.setAttribute('aria-label', window.trans?.(isVisible ? 'Show password' : 'Hide password') || (isVisible ? 'Show password' : 'Hide password'));
      
      eyeOn?.classList.toggle('hidden', isVisible);
      eyeOff?.classList.toggle('hidden', !isVisible);
    }

    // Method để clear error của một field
    clearFieldError(field, errorElement) {
      if (!field || !errorElement) return;
      
      // Remove all border colors and reset to default
      field.classList.remove('border-red-400', 'border-blue-500');
      field.classList.add('border-transparent');
      field.setAttribute('aria-invalid', 'false');
      
      // Hide error message - Tailwind way
      errorElement.classList.add('hidden');
      errorElement.classList.remove('flex');
    }

    // Method để set error cho một field
    setFieldError(field, errorElement) {
      if (!field || !errorElement) return;
      
      // Add red border (will be blue on focus due to focus event handlers)
      field.classList.remove('border-transparent', 'border-blue-500');
      field.classList.add('border-red-400');
      field.setAttribute('aria-invalid', 'true');
      
      // Show error message - Tailwind way
      errorElement.classList.remove('hidden');
      errorElement.classList.add('flex');
    }

    // Method để reset tất cả error states
    resetErrors() {
      const { username, password, usernameError, passwordError } = this.elements;
      this.clearFieldError(username, usernameError);
      this.clearFieldError(password, passwordError);
    }

    handleSubmit(e) {
      const { username, password, submit, usernameError, passwordError } = this.elements;
      
      // Reset errors trước khi validate mới
      this.resetErrors();

      let isValid = true;
      let firstInvalidField = null;

      // Validate username
      if (!username?.value.trim()) {
        this.setFieldError(username, usernameError);
        isValid = false;
        firstInvalidField = firstInvalidField || username;
      }

      // Validate password
      if (!password?.value.trim()) {
        this.setFieldError(password, passwordError);
        isValid = false;
        firstInvalidField = firstInvalidField || password;
      }

      // Prevent submit nếu đang submit hoặc không valid
      if (this.isSubmitting || !isValid) {
        e.preventDefault();
        
        // Focus vào field đầu tiên có lỗi
        if (firstInvalidField) {
          firstInvalidField.focus();
        }
        
        return;
      }

      // Set submitting state
      this.isSubmitting = true;
      submit.disabled = true;
      submit.classList.add('loading');
      submit.setAttribute('aria-busy', 'true');
      submit.querySelector('.spinner')?.classList.remove('hidden');
    }

    restoreIfFromBFCache() {
      const { submit } = this.elements;
      
      window.addEventListener('pageshow', (evt) => {
        if (evt.persisted) {
          this.isSubmitting = false;
          submit.disabled = false;
          submit.classList.remove('loading');
          submit.setAttribute('aria-busy', 'false');
          submit.querySelector('.spinner')?.classList.add('hidden');
          
          // Reset errors khi back từ cache
          this.resetErrors();
        }
      }, { passive: true });
    }
  }

  const initAll = () => {
    console.log('[login.js] Initializing, ResSyncBase:', window.ResSyncBase);
    new ResSyncLoginForm();
    
    if (window.ResSyncBase) {
      window.ResSyncBase.initDropdowns('[data-dropdown]');
      window.ResSyncBase.initLanguageSwitcher();
    } else {
      console.error('[login.js] ResSyncBase not found');
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll, { passive: true });
  } else {
    initAll();
  }
})();


