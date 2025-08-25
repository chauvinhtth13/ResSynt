// static/js/default/login.js
(() => {
  class ResSyncLoginForm {
    constructor() {
      this.form = document.getElementById('loginForm');
      if (!this.form) return;

      const username = document.getElementById('username');
      const password = document.getElementById('password');
      const toggle = document.getElementById('passwordToggle');
      const eyeOn = document.getElementById('eyeOn');
      const eyeOff = document.getElementById('eyeOff');
      const submit = this.form.querySelector('.submit-btn');

      this.elements = { username, password, toggle, eyeOn, eyeOff, submit };
      this.isSubmitting = false;

      if (!password || !submit) return;

      // Initial icon state
      if (password.type === 'password') {
        eyeOn?.classList.add('hidden');
        eyeOff?.classList.remove('hidden');
      }

      // Ensure toggle is a non-submit control
      if (toggle?.tagName === 'BUTTON' && toggle.getAttribute('type') !== 'button') {
        toggle.setAttribute('type', 'button');
      }
      // Link toggle to the input for a11y
      if (toggle && !toggle.hasAttribute('aria-controls') && password.id) {
        toggle.setAttribute('aria-controls', password.id);
      }

      this.bind();
      this.restoreIfFromBFCache();
    }

    bind() {
      const { form, elements } = this;
      const { toggle, username } = elements;

      toggle?.addEventListener('click', () => this.togglePassword());
      toggle?.addEventListener('keydown', (e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          this.togglePassword();
        }
      });

      form.addEventListener('submit', (e) => this.handleSubmit(e));

      username?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !username.value) e.preventDefault();
      });
    }

    togglePassword() {
      const { password, toggle, eyeOn, eyeOff } = this.elements;
      if (!password || !toggle) return;

      const isPassword = password.type === 'password';
      password.type = isPassword ? 'text' : 'password';
      toggle.setAttribute('aria-pressed', String(isPassword));
      toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      eyeOn?.classList.toggle('hidden', !isPassword);
      eyeOff?.classList.toggle('hidden', isPassword);
    }

    handleSubmit(e) {
      const { username, password, submit } = this.elements;
      if (!submit || !password) return;

      if (!password.value || !username?.value) {
        e.preventDefault();
        return;
      }

      if (this.isSubmitting) {
        e.preventDefault();
        return;
      }
      this.isSubmitting = true;

      submit.disabled = true;
      submit.classList.add('loading');
      submit.setAttribute('aria-busy', 'true');
      submit.querySelector('.spinner')?.classList.remove('hidden');
    }

    restoreIfFromBFCache() {
      const { submit } = this.elements;
      if (!submit) return;

      window.addEventListener('pageshow', (evt) => {
        if (evt.persisted) {
          this.isSubmitting = false;
          submit.disabled = false;
          submit.classList.remove('loading');
          submit.setAttribute('aria-busy', 'false');
          submit.querySelector('.spinner')?.classList.add('hidden');
        }
      });
    }
  }

  // Initialize after HTML is parsed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ResSyncLoginForm());
  } else {
    new ResSyncLoginForm();
  }
})();
