/* web/static/js/default/login_script.js */
class ResSyncLoginForm {
  constructor() {
    this.form = document.getElementById('loginForm');
    this.usernameInput = document.getElementById('username');
    this.passwordInput = document.getElementById('password');
    this.passwordToggle = document.getElementById('passwordToggle');
    this.submitButton = this.form.querySelector('.submit-btn');
    this.bind();
  }
  bind() {
    if (this.passwordToggle) {
      this.passwordToggle.addEventListener('click', () => {
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
      });
    }
    // DO NOT preventDefault — let the form POST directly to Django
    this.form.addEventListener('submit', () => {
      this.submitButton.disabled = true;
      this.submitButton.classList.add('loading');
    });
  }
}
document.addEventListener('DOMContentLoaded', () => new ResSyncLoginForm());