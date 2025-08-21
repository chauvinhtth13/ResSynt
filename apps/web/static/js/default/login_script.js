/* web/static/js/default/login_script.js */
class ResSyncLoginForm {
  constructor() {
    this.form = document.getElementById('loginForm');
    this.usernameInput = document.getElementById('username');
    this.passwordInput = document.getElementById('password');
    this.passwordToggle = document.getElementById('passwordToggle');
    // Get references to the eye icons for toggling
    this.eyeOnIcon = document.getElementById('eyeOn');
    this.eyeOffIcon = document.getElementById('eyeOff');
    this.submitButton = this.form.querySelector('.submit-btn');
    this.bind();
  }

  bind() {
    // Check if the password toggle button exists
    if (this.passwordToggle) {
      this.passwordToggle.addEventListener('click', () => {
        // Determine the new type for the password input field
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';

        // Set the new type for the password input
        this.passwordInput.type = type;

        // Toggle the aria-pressed attribute for accessibility, indicating if the password is shown
        this.passwordToggle.setAttribute('aria-pressed', type === 'text');

        // Toggle the visibility of the eye icons based on the password input type
        if (type === 'text') {
          // If password is now visible, show eye-off icon and hide eye-on icon
          this.eyeOnIcon.classList.add('hidden');
          this.eyeOffIcon.classList.remove('hidden');
          // Update aria-label for screen readers to indicate the action
          this.passwordToggle.setAttribute('aria-label', 'Hide password');
        } else {
          // If password is now hidden, show eye-on icon and hide eye-off icon
          this.eyeOnIcon.classList.remove('hidden');
          this.eyeOffIcon.classList.add('hidden');
          // Update aria-label for screen readers to indicate the action
          this.passwordToggle.setAttribute('aria-label', 'Show password');
        }
      });
    }

    // Add submit event listener to the form
    // DO NOT preventDefault — let the form POST directly to Django
    this.form.addEventListener('submit', () => {
      // Disable the submit button and add a loading class when the form is submitted
      this.submitButton.disabled = true;
      this.submitButton.classList.add('loading');
    });
  }
}

// Initialize the ResSyncLoginForm class when the DOM content is fully loaded
document.addEventListener('DOMContentLoaded', () => new ResSyncLoginForm());
