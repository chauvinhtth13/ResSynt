// static/js/default/login.js
'use strict';
/* web/static/js/default/login_script.js */
const { registerInit } = window.ResSyncBase;

class ResSyncLoginForm {
  constructor() {
    this.form = document.getElementById('loginForm');
    if (!this.form) return; // Early exit if form missing
    this.usernameInput = document.getElementById('username');
    this.passwordInput = document.getElementById('password');
    this.passwordToggle = document.getElementById('passwordToggle');
    this.eyeOnIcon = document.getElementById('eyeOn');
    this.eyeOffIcon = document.getElementById('eyeOff');
    this.submitButton = this.form.querySelector('.submit-btn');
    this.bind();
  }

  bind() {
    if (this.passwordToggle && this.passwordInput && this.eyeOnIcon && this.eyeOffIcon) {
      this.passwordToggle.addEventListener('click', () => {
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
        this.passwordToggle.setAttribute('aria-pressed', type === 'text' ? 'true' : 'false');
        if (type === 'text') {
          this.eyeOnIcon.classList.add('hidden');
          this.eyeOffIcon.classList.remove('hidden');
          this.passwordToggle.setAttribute('aria-label', 'Hide password');
        } else {
          this.eyeOnIcon.classList.remove('hidden');
          this.eyeOffIcon.classList.add('hidden');
          this.passwordToggle.setAttribute('aria-label', 'Show password');
        }
      });
    }

    if (this.submitButton) {
      this.form.addEventListener('submit', () => {
        this.submitButton.disabled = true;
        this.submitButton.classList.add('loading');
        // Optional: Timeout to re-enable if submit fails, but since POST, rely on server
      });
    }
  }
}

registerInit(() => {
  new ResSyncLoginForm();
});