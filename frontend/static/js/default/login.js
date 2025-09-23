// frontend\static\js\default\login.js
(() => {
  class ResSyncLoginForm {
    constructor() {
      // Elements from your old code
      this.passwordInput = document.getElementById('passwordInput');
      this.togglePassword = document.getElementById('togglePassword');
      this.toggleIcon = document.getElementById('toggleIcon');
      
      if (!this.passwordInput || !this.togglePassword || !this.toggleIcon) {
        console.warn('[login.js] Missing password toggle elements:', {
          passwordInput: this.passwordInput,
          togglePassword: this.togglePassword,
          toggleIcon: this.toggleIcon
        });
        return;
      }
      
      this.bind();
    }

    bind() {
      this.togglePassword.addEventListener('click', () => this.togglePasswordVisibility());
    }

    togglePasswordVisibility() {
      const type = this.passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      this.passwordInput.setAttribute('type', type);

      // Toggle icon
      if (type === 'password') {
        this.toggleIcon.classList.remove('bi-eye');
        this.toggleIcon.classList.add('bi-eye-slash');
      } else {
        this.toggleIcon.classList.remove('bi-eye-slash');
        this.toggleIcon.classList.add('bi-eye');
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    new ResSyncLoginForm();
  });
})();
