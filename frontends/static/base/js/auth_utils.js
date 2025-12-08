// frontends/static/js/default/auth-utils.js
// Shared utilities for authentication pages (login, password reset, etc.)

(() => {
  'use strict';

  // ========================================
  // Password Toggle Utility
  // ========================================
  class PasswordToggle {
    /**
     * Initialize password toggle functionality for a field
     * @param {Object} config - Configuration object
     * @param {string} config.inputId - ID of password input field
     * @param {string} config.toggleId - ID of toggle button
     * @param {string} config.iconId - ID of icon element
     */
    constructor(config) {
      this.input = document.getElementById(config.inputId);
      this.toggle = document.getElementById(config.toggleId);
      this.icon = document.getElementById(config.iconId);
      
      if (!this.input || !this.toggle || !this.icon) {
        console.warn('[PasswordToggle] Missing elements:', {
          input: !!this.input,
          toggle: !!this.toggle,
          icon: !!this.icon,
          config
        });
        return;
      }
      
      this.bind();
    }

    bind() {
      this.toggle.addEventListener('click', () => this.toggleVisibility());
    }

    toggleVisibility() {
      const currentType = this.input.getAttribute('type');
      const newType = currentType === 'password' ? 'text' : 'password';
      this.input.setAttribute('type', newType);

      // Toggle icon classes
      if (newType === 'password') {
        this.icon.classList.remove('bi-eye');
        this.icon.classList.add('bi-eye-slash');
      } else {
        this.icon.classList.remove('bi-eye-slash');
        this.icon.classList.add('bi-eye');
      }
    }
  }

  // ========================================
  // Password Strength Calculator (Sync with Django validators)
  // ========================================
  
  /**
   * Common passwords list (subset of Django's CommonPasswordValidator)
   * Full list: https://github.com/django/django/blob/main/django/contrib/auth/common-passwords.txt.gz
   */
  const COMMON_PASSWORDS = new Set([
    'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey', 
    '1234567', 'letmein', 'trustno1', 'dragon', 'baseball', 'iloveyou',
    'master', 'sunshine', 'ashley', 'bailey', 'shadow', 'superman',
    '123456789', '12345', 'password1', '123123', 'admin', 'welcome'
  ]);

  /**
   * Calculate password strength matching Django's AUTH_PASSWORD_VALIDATORS
   * Returns: { score: 0-5, issues: [], passed: boolean }
   */
  const calculatePasswordStrength = (password, username = '') => {
    const issues = [];
    let score = 0;
    
    //  Handle empty password
    if (!password || password.length === 0) {
      return {
        score: 0,
        issues: [],
        passed: false,
        isEmpty: true  // Flag to indicate empty password
      };
    }
    
    // 1. Minimum Length (Django: MinimumLengthValidator with min_length=8)
    if (password.length < 8) {
      issues.push('Password must be at least 8 characters long');
    } else {
      score++;
      if (password.length >= 12) score++; // Bonus for longer passwords
    }
    
    // 2. Not all numeric (Django: NumericPasswordValidator)
    if (/^\d+$/.test(password)) {
      issues.push('Password cannot be entirely numeric');
    } else {
      score++;
    }
    
    // 3. Not common password (Django: CommonPasswordValidator)
    if (COMMON_PASSWORDS.has(password.toLowerCase())) {
      issues.push('This password is too common');
    } else {
      score++;
    }
    
    // 4. Not similar to username (Django: UserAttributeSimilarityValidator)
    if (username && password.toLowerCase().includes(username.toLowerCase())) {
      issues.push('Password is too similar to your username');
    } else if (username) {
      score++;
    }
    
    // 5. Character variety (Best practice - not in Django by default)
    const hasLower = /[a-z]/.test(password);
    const hasUpper = /[A-Z]/.test(password);
    const hasDigit = /\d/.test(password);
    const hasSpecial = /[^a-zA-Z0-9]/.test(password);
    const varietyCount = [hasLower, hasUpper, hasDigit, hasSpecial].filter(Boolean).length;
    
    if (varietyCount >= 3) {
      score++;
    } else {
      issues.push('Use a mix of uppercase, lowercase, numbers, and special characters');
    }
    
    return {
      score: Math.min(score, 5),
      issues: issues,
      passed: issues.length === 0 && score >= 3,
      isEmpty: false
    };
  };

  /**
   * Update password strength UI with detailed feedback
   * Supports two UI modes: progress bar (profile) and inline text (auth pages)
   */
  const updatePasswordStrengthUI = (result, indicatorId = 'passwordStrength') => {
    const strengthIndicator = document.getElementById(indicatorId);
    if (!strengthIndicator) return;
    
    const { score, issues, passed, isEmpty } = result;
    
    // Get progress bar reference
    const progressBar = document.getElementById('passwordStrengthBar');
    
    //  Clear UI COMPLETELY if password is empty
    if (isEmpty) {
      // Clear text indicator
      strengthIndicator.innerHTML = '';
      strengthIndicator.textContent = '';
      strengthIndicator.style.color = '';
      
      // Clear progress bar if exists
      if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = '';
        progressBar.style.transition = 'width 0.3s ease, background-color 0.3s ease';
      }
      
      return;
    }
    
    const strengthLevels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const strengthColors = ['danger', 'danger', 'warning', 'info', 'success', 'success'];
    const color = strengthColors[Math.min(score, 5)];
    
    if (progressBar) {
      // Profile page style - with progress bar
      const widthPercent = (score / 5) * 100;
      const colorMap = {
        'danger': '#dc3545',
        'warning': '#ffc107', 
        'info': '#0dcaf0',
        'success': '#198754'
      };
      
      //  Always set transition for smooth animation
      progressBar.style.transition = 'width 0.3s ease, background-color 0.3s ease';
      progressBar.style.width = `${widthPercent}%`;
      progressBar.style.backgroundColor = colorMap[color] || '';
      
      // Update help text with strength level and issues
      let helpText = `${strengthLevels[score]}`;
      if (issues.length > 0) {
        helpText = issues[0]; // Show first issue
      }
      strengthIndicator.textContent = helpText;
      strengthIndicator.style.color = colorMap[color] || '';
      
    } else {
      // Auth pages style - detailed with list
      let html = `
        <div class="mt-2">
          <div class="d-flex align-items-center gap-2 mb-1">
            <small class="text-${color} fw-bold">
              ${strengthLevels[score]}
            </small>
            <div class="flex-grow-1">
              <div class="progress" style="height: 4px;">
                <div class="progress-bar bg-${color}" 
                     role="progressbar" 
                     style="width: ${(score / 5) * 100}%"
                     aria-valuenow="${score}" 
                     aria-valuemin="0" 
                     aria-valuemax="5">
                </div>
              </div>
            </div>
          </div>
      `;
      
      // Show issues if any
      if (issues.length > 0) {
        html += '<ul class="mb-0 ps-3" style="font-size: 0.85rem;">';
        issues.forEach(issue => {
          html += `<li class="text-${color}">${issue}</li>`;
        });
        html += '</ul>';
      }
      
      html += '</div>';
      strengthIndicator.innerHTML = html;
    }
  };

  // ========================================
  // Password Match Validator
  // ========================================
  class PasswordMatchValidator {
    /**
     * Initialize password match validation
     * @param {string} password1Id - ID of first password field
     * @param {string} password2Id - ID of second password field (confirmation)
     */
    constructor(password1Id, password2Id) {
      this.password1 = document.getElementById(password1Id);
      this.password2 = document.getElementById(password2Id);
      
      if (!this.password1 || !this.password2) {
        console.warn('[PasswordMatchValidator] Missing password fields');
        return;
      }
      
      this.bind();
    }

    bind() {
      this.password2.addEventListener('input', () => this.validateMatch());
    }

    validateMatch() {
      if (this.password1.value && this.password2.value) {
        if (this.password1.value === this.password2.value) {
          this.password2.classList.remove('is-invalid');
          this.password2.classList.add('is-valid');
        } else {
          this.password2.classList.remove('is-valid');
          this.password2.classList.add('is-invalid');
        }
      }
    }
  }

  // ========================================
  // Password Strength Monitor
  // ========================================
  class PasswordStrengthMonitor {
    /**
     * Monitor password strength and update UI (synced with Django validators)
     * @param {string} inputId - ID of password input field
     * @param {string} indicatorId - ID of strength indicator element
     * @param {string|Function} usernameGetter - Username string or function to get username
     */
    constructor(inputId, indicatorId = 'passwordStrength', usernameGetter = '') {
      this.input = document.getElementById(inputId);
      this.indicatorId = indicatorId;
      this.usernameGetter = usernameGetter;
      
      if (!this.input) {
        console.warn('[PasswordStrengthMonitor] Password input not found');
        return;
      }
      
      this.bind();
    }

    getUsername() {
      if (typeof this.usernameGetter === 'function') {
        return this.usernameGetter();
      }
      if (typeof this.usernameGetter === 'string') {
        return this.usernameGetter;
      }
      return '';
    }

    bind() {
      //  Handle ALL input events including deletion
      this.input.addEventListener('input', () => {
        const password = this.input.value;
        const username = this.getUsername();
        
        //  CRITICAL: Check if password is empty
        if (!password || password.trim().length === 0) {
          // Force clear UI for empty password
          updatePasswordStrengthUI({
            score: 0,
            issues: [],
            passed: false,
            isEmpty: true
          }, this.indicatorId);
        } else {
          // Calculate and update normally
          const result = calculatePasswordStrength(password, username);
          updatePasswordStrengthUI(result, this.indicatorId);
        }
      });
      
      //  Also handle keyup for immediate feedback
      this.input.addEventListener('keyup', () => {
        const password = this.input.value;
        
        // Double-check empty state on keyup
        if (!password || password.trim().length === 0) {
          updatePasswordStrengthUI({
            score: 0,
            issues: [],
            passed: false,
            isEmpty: true
          }, this.indicatorId);
        }
      });
    }
  }

  // ========================================
  // Initialize Multiple Password Toggles
  // ========================================
  const initPasswordToggles = (configs) => {
    return configs.map(config => new PasswordToggle(config));
  };

  // ========================================
  // Public API
  // ========================================
  window.ResSyncAuthUtils = {
    PasswordToggle,
    PasswordMatchValidator,
    PasswordStrengthMonitor,
    initPasswordToggles,
    calculatePasswordStrength,
    updatePasswordStrengthUI
  };

})();