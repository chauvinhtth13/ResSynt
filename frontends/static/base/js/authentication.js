// frontends\static\base\js\authentication.js
(() => {
  class PasswordToggleHandler {
    constructor() {
      this.initializeToggles();
    }

    initializeToggles() {
      // Tìm TẤT CẢ các container chứa password input
      const passwordContainers = document.querySelectorAll('.password-input-container');
      
      passwordContainers.forEach((container, index) => {
        const passwordInput = container.querySelector('input[type="password"], input[type="text"]');
        const toggleButton = container.querySelector('.password-toggle-icon');
        const toggleIcon = toggleButton?.querySelector('i');
        
        if (!passwordInput || !toggleButton || !toggleIcon) {
          console.warn(`[PasswordToggle] Missing elements in container ${index}:`, {
            passwordInput: !!passwordInput,
            toggleButton: !!toggleButton,
            toggleIcon: !!toggleIcon
          });
          return;
        }

        // Gán unique ID nếu chưa có
        if (!passwordInput.id) {
          passwordInput.id = `password-field-${index}`;
        }
        
        // Setup ARIA attributes
        toggleButton.setAttribute('aria-controls', passwordInput.id);
        toggleButton.setAttribute('aria-label', 'Toggle password visibility');
        
        // Bind sự kiện click cho từng button
        this.bindToggleEvent(toggleButton, passwordInput, toggleIcon);
      });
    }

    bindToggleEvent(button, input, icon) {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation(); // Ngăn event bubbling
        
        const currentType = input.getAttribute('type');
        const newType = currentType === 'password' ? 'text' : 'password';
        
        // Toggle input type
        input.setAttribute('type', newType);
        
        // Toggle icon với animation
        this.toggleIcon(icon, newType === 'password');
        
        // Update ARIA
        button.setAttribute('aria-pressed', newType === 'text');
        
        // Focus lại input để user tiếp tục nhập
        input.focus();
        
        // Giữ cursor position
        const cursorPosition = input.selectionStart;
        setTimeout(() => {
          input.setSelectionRange(cursorPosition, cursorPosition);
        }, 0);
      });
    }

    toggleIcon(icon, showEyeSlash) {
      // Thêm animation khi chuyển icon
      icon.style.transition = 'transform 0.2s ease';
      icon.style.transform = 'scale(0.8)';
      
      setTimeout(() => {
        if (showEyeSlash) {
          icon.classList.remove('bi-eye');
          icon.classList.add('bi-eye-slash');
        } else {
          icon.classList.remove('bi-eye-slash');
          icon.classList.add('bi-eye');
        }
        icon.style.transform = 'scale(1)';
      }, 100);
    }
  }

  // Khởi tạo khi DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      new PasswordToggleHandler();
    });
  } else {
    // DOM đã load xong
    new PasswordToggleHandler();
  }
})();