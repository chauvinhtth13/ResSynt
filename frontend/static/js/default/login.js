// static/js/default/login.js
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

      this.elements = { username, password, toggle, eyeOn, eyeOff, submit };
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
      const { toggle, username } = elements;

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

    handleSubmit(e) {
      const { username, password, submit } = this.elements;
      if (this.isSubmitting || !password.value || !username?.value) {
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