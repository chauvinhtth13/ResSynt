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
      // Thêm: Lấy error elements
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

      // Thêm: Event listeners để clear error realtime khi input thay đổi
      username?.addEventListener('input', () => {
        console.debug('[login.js] Username input changed:', username.value); // Debug
        if (username.value.trim() !== '') {
          username.classList.remove('border-red-500', 'focus:ring-red-500');
          usernameError?.classList.add('hidden');
        }
      });

      password?.addEventListener('input', () => {
        console.debug('[login.js] Password input changed:', password.value); // Debug (note: password value sẽ không log full cho security, nhưng trim() ok)
        if (password.value.trim() !== '') {
          password.classList.remove('border-red-500', 'focus:ring-red-500');
          passwordError?.classList.add('hidden');
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

    // Thêm: Method để reset tất cả error states
    resetErrors() {
      const { username, password, usernameError, passwordError } = this.elements;
      username?.classList.remove('border-red-500', 'focus:ring-red-500');
      password?.classList.remove('border-red-500', 'focus:ring-red-500');
      usernameError?.classList.add('hidden');
      passwordError?.classList.add('hidden');
      console.debug('[login.js] Errors reset'); // Debug
    }

    handleSubmit(e) {
      const { username, password, submit, usernameError, passwordError } = this.elements;
      this.resetErrors(); // Reset trước khi validate mới

      let isValid = true;

      if (username?.value.trim() === '') {
        username.classList.add('border-red-500', 'focus:ring-red-500');
        usernameError?.classList.remove('hidden');
        isValid = false;
        console.debug('[login.js] Username invalid'); // Debug
      }

      if (password?.value.trim() === '') {
        password.classList.add('border-red-500', 'focus:ring-red-500');
        passwordError?.classList.remove('hidden');
        isValid = false;
        console.debug('[login.js] Password invalid'); // Debug
      }

      if (this.isSubmitting || !isValid) {
        e.preventDefault();
        console.debug('[login.js] Submit prevented:', { isSubmitting: this.isSubmitting, isValid }); // Debug
        return;
      }
      this.isSubmitting = true;

      submit.disabled = true;
      submit.classList.add('loading');
      submit.setAttribute('aria-busy', 'true');
      submit.querySelector('.spinner')?.classList.remove('hidden');
      console.debug('[login.js] Submitting form'); // Debug
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





<script>
        // Language Switch
        document.querySelectorAll('.lang-switch .btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.lang-switch .btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                const lang = this.dataset.lang;
                // Django language switch
                fetch(`{% url 'set_language' %}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': '{{ csrf_token }}'
                    },
                    body: `language=${lang}`
                }).then(() => {
                    window.location.reload();
                });
            });
        });
        
        // Handle Login Form Submit
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            const btnText = document.getElementById('btnText');
            const btnLoading = document.getElementById('btnLoading');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            // Show loading state
            btnText.classList.add('d-none');
            btnLoading.classList.remove('d-none');
            submitBtn.disabled = true;
        });
        
        // Add input focus effects
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.classList.add('focused');
            });
            
            input.addEventListener('blur', function() {
                if (!this.value) {
                    this.parentElement.classList.remove('focused');
                }
            });
        });
        
        // Auto-hide alerts after 5 seconds
        document.querySelectorAll('.alert').forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    </script>