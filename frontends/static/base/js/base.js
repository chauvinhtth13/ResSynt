// frontends/static/js/default/base.js
// Complete optimized base.js with Vietnamese as default language (using Django i18n)
'use strict';

(() => {
  // ========================================
  // Performance Monitoring
  // ========================================
  const perfMark = (name) => {
    if (window.performance && performance.mark) {
      performance.mark(name);
    }
  };

  perfMark('ResSyncBase:start');

  // ========================================
  // Core Utilities
  // ========================================
  
  // Element cache for performance
  const elementCache = new WeakMap();
  
  // Optimized query selector with caching
  const qs = (selector, element = document) => {
    if (!elementCache.has(element)) {
      elementCache.set(element, new Map());
    }
    
    const cache = elementCache.get(element);
    const key = selector;
    
    if (!cache.has(key)) {
      cache.set(key, element.querySelector(selector));
    }
    
    return cache.get(key);
  };
  
  // Query selector all
  const qsa = (selector, element = document) => {
    return Array.from(element.querySelectorAll(selector));
  };

  // ========================================
  // Cookie Management
  // ========================================
  const cookieCache = new Map();
  let cookieCacheTime = 0;
  
  const getCookie = (name) => {
    if (!name) return null;
    
    const now = Date.now();
    if (now - cookieCacheTime > 1000) { // Refresh cache every second
      cookieCache.clear();
      cookieCacheTime = now;
    }
    
    if (cookieCache.has(name)) {
      return cookieCache.get(name);
    }
    
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    const result = parts.length === 2 ? 
      decodeURIComponent(parts.pop().split(';').shift()) : null;
    
    cookieCache.set(name, result);
    return result;
  };

  const setCookie = (name, value, days = 365) => {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${encodeURIComponent(value)}; ${expires}; path=/`;
    
    // Update cache
    cookieCache.set(name, value);
  };

  const deleteCookie = (name) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    cookieCache.delete(name);
  };

  // ========================================
  // Language Management
  // ========================================
  
  // Get current language with Vietnamese as default
  const getCurrentLanguage = () => {
    return getCookie('django_language') || 'vi';
  };

  // Set language
  const setLanguage = (lang) => {
    setCookie('django_language', lang);
  };

  // ========================================
  // Utility Functions
  // ========================================
  
  // Debounce function
  const debounce = (func, wait = 300, immediate = false) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        timeout = null;
        if (!immediate) func.apply(this, args);
      };
      
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      
      if (callNow) func.apply(this, args);
    };
  };

  // Throttle function
  const throttle = (func, limit = 250) => {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  };

  // Format number for Vietnamese (dot for thousands)
  const formatNumber = (num) => {
    const lang = getCurrentLanguage();
    if (lang === 'vi') {
      return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    return num.toLocaleString('en-US');
  };

  // Format date (DD/MM/YYYY) - consistent format across all languages
  const formatDate = (date) => {
    const d = new Date(date);
    if (isNaN(d.getTime())) return ''; // Invalid date
    
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  };

  // Format datetime (DD/MM/YYYY HH:MM) - consistent format across all languages
  const formatDateTime = (date) => {
    const d = new Date(date);
    if (isNaN(d.getTime())) return ''; // Invalid date
    
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  };

  // Format time
  const formatTime = (date) => {
    const d = new Date(date);
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  // ========================================
  // Dropdown Handler
  // ========================================
  const initDropdowns = (selector = '[data-dropdown]') => {
    const dropdowns = qsa(selector);
    if (!dropdowns.length) return () => {};

    const dropdownStates = new WeakMap();
    
    const closeAll = (except = null) => {
      dropdowns.forEach(dropdown => {
        const menu = qs('[data-dropdown-menu], .dropdown-menu', dropdown);
        if (!menu || menu === except) return;
        
        menu.hidden = true;
        menu.setAttribute('aria-hidden', 'true');
        
        const trigger = qs('[data-dropdown-trigger], .dropdown-trigger', dropdown);
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
        
        dropdownStates.set(dropdown, false);
      });
    };
    
    const toggleDropdown = (trigger, dropdown, menu) => {
      const isOpen = dropdownStates.get(dropdown) || false;
      closeAll(isOpen ? null : menu);
      
      menu.hidden = isOpen;
      menu.setAttribute('aria-hidden', String(isOpen));
      trigger.setAttribute('aria-expanded', String(!isOpen));
      dropdownStates.set(dropdown, !isOpen);
      
      if (!isOpen) {
        // Use requestIdleCallback for non-critical focus operation
        const focusFirstElement = () => {
          const firstFocusable = qs(
            'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
            menu
          );
          if (firstFocusable) firstFocusable.focus({ preventScroll: true });
        };
        
        if ('requestIdleCallback' in window) {
          requestIdleCallback(focusFirstElement);
        } else {
          requestAnimationFrame(focusFirstElement);
        }
      }
    };
    
    const handleInteraction = (e) => {
      const trigger = e.target.closest('[data-dropdown-trigger], .dropdown-trigger');
      
      if (!trigger) {
        // Close all dropdowns if clicking outside
        if (!e.target.closest('[data-dropdown-menu], .dropdown-menu')) {
          closeAll();
        }
        return;
      }
      
      const dropdown = trigger.closest('[data-dropdown]');
      if (!dropdown) return;
      
      const menu = qs('[data-dropdown-menu], .dropdown-menu', dropdown);
      if (!menu) return;
      
      if (trigger.tagName === 'A') e.preventDefault();
      e.stopPropagation();
      
      toggleDropdown(trigger, dropdown, menu);
    };
    
    const handleKeydown = (e) => {
      if (e.key === 'Escape') {
        const openDropdown = Array.from(dropdownStates.entries())
          .find(([_, isOpen]) => isOpen);
        
        if (openDropdown) {
          closeAll();
          const trigger = qs('[data-dropdown-trigger], .dropdown-trigger', openDropdown[0]);
          if (trigger) trigger.focus();
        }
      }
    };
    
    // Use passive listeners where possible
    document.addEventListener('click', handleInteraction, { passive: false });
    document.addEventListener('keydown', handleKeydown, { passive: true });
    
    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleKeydown);
    };
  };

  // ========================================
  // Focus Trap
  // ========================================
  const trapFocusWithin = (container) => {
    if (!container) return () => {};
    
    let focusables = [];
    let observer = null;
    
    const updateFocusables = debounce(() => {
      focusables = qsa(
        'a[href], button:not([disabled]), textarea:not([disabled]), ' +
        'input:not([disabled]):not([type="hidden"]), select:not([disabled]), ' +
        '[tabindex]:not([tabindex="-1"])',
        container
      ).filter(el => {
        if (observer) return true;
        return el.offsetParent !== null && 
               getComputedStyle(el).visibility !== 'hidden';
      });
    }, 100);
    
    // Setup IntersectionObserver for better performance
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          const index = focusables.indexOf(entry.target);
          if (entry.isIntersecting && index === -1) {
            updateFocusables();
          } else if (!entry.isIntersecting && index !== -1) {
            updateFocusables();
          }
        });
      });
      
      // Observe all potential focusable elements
      qsa('a, button, textarea, input, select, [tabindex]', container)
        .forEach(el => observer.observe(el));
    }
    
    updateFocusables();
    
    const onKey = (e) => {
      if (e.key !== 'Tab' || !focusables.length) return;
      
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    
    // Use MutationObserver with debouncing
    const mutationObserver = new MutationObserver(
      debounce(updateFocusables, 100)
    );
    
    mutationObserver.observe(container, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['disabled', 'tabindex']
    });
    
    container.addEventListener('keydown', onKey);
    
    return () => {
      if (observer) observer.disconnect();
      mutationObserver.disconnect();
      container.removeEventListener('keydown', onKey);
    };
  };

  // ========================================
  // Language Switcher with Vietnamese Default
  // ========================================
  const initLanguageSwitcher = (config = {}) => {
    const {
      currentLangId = 'current-language',
      langMenuId = 'lang-menu',
      errorContainer = 'main',
      setLangUrl = '/i18n/setlang/',
      defaultLanguage = 'vi'  // Vietnamese as default
    } = config;

    const currentLangSpan = document.getElementById(currentLangId);
    const langMenu = document.getElementById(langMenuId);
    if (!langMenu || !currentLangSpan) return () => {};

    const formAction = langMenu.querySelector('form')?.getAttribute('action') || null;
    const finalSetLangUrl = formAction || setLangUrl;

    // Set Vietnamese as default if no language cookie exists
    let currentLang = getCookie('django_language');
    if (!currentLang) {
      currentLang = defaultLanguage;
      setCookie('django_language', currentLang);
    }
    
    // Update display
    currentLangSpan.textContent = currentLang.toUpperCase();

    const showError = (message) => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700';
      errorDiv.textContent = message;
      errorDiv.setAttribute('role', 'alert');
      const container = qs(errorContainer);
      if (container) {
        container.prepend(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
      }
    };

    const handleLangChange = async (e) => {
      const button = e.target.closest('button[name="language"]');
      if (!button) return;
      
      e.preventDefault();
      
      const lang = button.value;
      if (!lang) return;

      const prevLang = currentLangSpan.textContent;
      currentLangSpan.textContent = lang.toUpperCase();

      // Disable all language buttons
      langMenu.querySelectorAll('button').forEach(btn => {
        btn.disabled = true;
        btn.classList.add('opacity-50');
      });

      try {
        const csrfToken = getCookie('csrftoken');
        if (!csrfToken) throw new Error('CSRF token missing');

        const response = await fetch(finalSetLangUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
          },
          body: new URLSearchParams({
            language: lang,
            next: window.location.pathname + window.location.search,
          }),
          credentials: 'same-origin'
        });

        if (response.ok) {
          // Update cookie
          setCookie('django_language', lang);
          // Reload page to apply new language
          location.reload();
        } else {
          throw new Error(`Failed: ${response.status}`);
        }
      } catch (error) {
        console.error('Language change error:', error);
        showError('Failed to change language. Please try again.');
        currentLangSpan.textContent = prevLang;
      } finally {
        // Re-enable buttons
        langMenu.querySelectorAll('button').forEach(btn => {
          btn.disabled = false;
          btn.classList.remove('opacity-50');
        });
      }
    };

    // Handle form submission
    const form = langMenu.querySelector('form');
    if (form) {
      form.addEventListener('submit', handleLangChange);
    }

    return () => {
      if (form) form.removeEventListener('submit', handleLangChange);
    };
  };

  // ========================================
  // Toast Notifications
  // ========================================
  const toast = {
    container: null,
    
    init() {
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
        this.container.setAttribute('aria-live', 'polite');
        document.body.appendChild(this.container);
      }
    },
    
    show(message, type = 'info', duration = 3000) {
      this.init();
      
      const toastEl = document.createElement('div');
      toastEl.className = `
        max-w-sm p-4 rounded-lg shadow-lg transform transition-all duration-300 
        ${type === 'success' ? 'bg-green-500 text-white' : ''}
        ${type === 'error' ? 'bg-red-500 text-white' : ''}
        ${type === 'warning' ? 'bg-yellow-500 text-white' : ''}
        ${type === 'info' ? 'bg-blue-500 text-white' : ''}
      `;
      toastEl.textContent = message;
      
      // Add to container with animation
      toastEl.style.opacity = '0';
      toastEl.style.transform = 'translateX(100%)';
      this.container.appendChild(toastEl);
      
      // Animate in
      requestAnimationFrame(() => {
        toastEl.style.opacity = '1';
        toastEl.style.transform = 'translateX(0)';
      });
      
      // Auto remove
      setTimeout(() => {
        toastEl.style.opacity = '0';
        toastEl.style.transform = 'translateX(100%)';
        setTimeout(() => toastEl.remove(), 300);
      }, duration);
    },
    
    success(message, duration) {
      this.show(message, 'success', duration);
    },
    
    error(message, duration) {
      this.show(message, 'error', duration);
    },
    
    warning(message, duration) {
      this.show(message, 'warning', duration);
    },
    
    info(message, duration) {
      this.show(message, 'info', duration);
    }
  };

  // ========================================
  // AJAX Helper
  // ========================================
  const ajax = {
    async request(url, options = {}) {
      const defaultOptions = {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
      };
      
      // Add CSRF token for non-GET requests
      if (options.method && options.method !== 'GET') {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
          defaultOptions.headers['X-CSRFToken'] = csrfToken;
        }
      }
      
      // Merge options
      const finalOptions = { ...defaultOptions, ...options };
      if (options.headers) {
        finalOptions.headers = { ...defaultOptions.headers, ...options.headers };
      }
      
      try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }
        
        return await response.text();
      } catch (error) {
        console.error('AJAX error:', error);
        throw error;
      }
    },
    
    get(url, options = {}) {
      return this.request(url, { ...options, method: 'GET' });
    },
    
    post(url, data, options = {}) {
      const isFormData = data instanceof FormData;
      const finalOptions = {
        ...options,
        method: 'POST',
        body: isFormData ? data : JSON.stringify(data),
      };
      
      if (!isFormData) {
        finalOptions.headers = {
          ...options.headers,
          'Content-Type': 'application/json',
        };
      }
      
      return this.request(url, finalOptions);
    },
    
    put(url, data, options = {}) {
      return this.post(url, data, { ...options, method: 'PUT' });
    },
    
    delete(url, options = {}) {
      return this.request(url, { ...options, method: 'DELETE' });
    }
  };

  // ========================================
  // Lazy Loading
  // ========================================
  const lazyLoadImages = () => {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
              imageObserver.unobserve(img);
              
              // Add loaded class for animation
              img.classList.add('loaded');
            }
          }
        });
      }, {
        rootMargin: '50px 0px',
        threshold: 0.01
      });
      
      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
      
      return imageObserver;
    }
    
    // Fallback for browsers without IntersectionObserver
    document.querySelectorAll('img[data-src]').forEach(img => {
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
      img.classList.add('loaded');
    });
    
    return null;
  };

  // ========================================
  // Form Utilities
  // ========================================
  const validateForm = (form) => {
    let isValid = true;
    const errors = [];
    
    // Check required fields
    form.querySelectorAll('[required]').forEach(field => {
      if (!field.value.trim()) {
        isValid = false;
        errors.push({
          field: field.name || field.id,
          message: 'This field is required'
        });
        field.classList.add('error');
      } else {
        field.classList.remove('error');
      }
    });
    
    // Check email fields
    form.querySelectorAll('[type="email"]').forEach(field => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (field.value && !emailRegex.test(field.value)) {
        isValid = false;
        errors.push({
          field: field.name || field.id,
          message: 'Invalid email address'
        });
        field.classList.add('error');
      }
    });
    
    return { isValid, errors };
  };

  const serializeForm = (form) => {
    const data = {};
    const formData = new FormData(form);
    
    for (const [key, value] of formData.entries()) {
      if (data[key]) {
        if (!Array.isArray(data[key])) {
          data[key] = [data[key]];
        }
        data[key].push(value);
      } else {
        data[key] = value;
      }
    }
    
    return data;
  };

  // ========================================
  // Modal Management
  // ========================================
  const modal = {
    show(content, options = {}) {
      const {
        title = '',
        size = 'medium',
        closeButton = true,
        backdrop = true,
        onClose = null
      } = options;
      
      // Create modal elements
      const modalEl = document.createElement('div');
      modalEl.className = 'fixed inset-0 z-50 overflow-y-auto';
      modalEl.setAttribute('role', 'dialog');
      modalEl.setAttribute('aria-modal', 'true');
      
      if (backdrop) {
        const backdropEl = document.createElement('div');
        backdropEl.className = 'fixed inset-0 bg-black bg-opacity-50 transition-opacity';
        backdropEl.addEventListener('click', () => this.close(modalEl, onClose));
        modalEl.appendChild(backdropEl);
      }
      
      const modalContent = document.createElement('div');
      modalContent.className = `
        relative mx-auto my-8 max-w-${size === 'small' ? 'md' : size === 'large' ? '4xl' : '2xl'}
        bg-white rounded-lg shadow-xl
      `;
      
      if (title) {
        const header = document.createElement('div');
        header.className = 'px-6 py-4 border-b';
        header.innerHTML = `<h3 class="text-lg font-semibold">${title}</h3>`;
        modalContent.appendChild(header);
      }
      
      const body = document.createElement('div');
      body.className = 'px-6 py-4';
      if (typeof content === 'string') {
        body.innerHTML = content;
      } else {
        body.appendChild(content);
      }
      modalContent.appendChild(body);
      
      if (closeButton) {
        const closeBtn = document.createElement('button');
        closeBtn.className = 'absolute top-4 right-4 text-gray-400 hover:text-gray-600';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', () => this.close(modalEl, onClose));
        modalContent.appendChild(closeBtn);
      }
      
      modalEl.appendChild(modalContent);
      document.body.appendChild(modalEl);
      
      // Trap focus
      const cleanup = trapFocusWithin(modalContent);
      modalEl._cleanup = cleanup;
      
      return modalEl;
    },
    
    close(modalEl, callback) {
      if (modalEl._cleanup) modalEl._cleanup();
      modalEl.remove();
      if (callback) callback();
    }
  };

  // ========================================
  // Storage Utilities
  // ========================================
  const storage = {
    get(key, defaultValue = null) {
      try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : defaultValue;
      } catch {
        return defaultValue;
      }
    },
    
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
    
    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch {
        return false;
      }
    },
    
    clear() {
      try {
        localStorage.clear();
        return true;
      } catch {
        return false;
      }
    }
  };

  // ========================================
  // URL Utilities
  // ========================================
  const url = {
    getParams() {
      const params = {};
      const searchParams = new URLSearchParams(window.location.search);
      for (const [key, value] of searchParams) {
        params[key] = value;
      }
      return params;
    },
    
    getParam(key, defaultValue = null) {
      const searchParams = new URLSearchParams(window.location.search);
      return searchParams.get(key) || defaultValue;
    },
    
    setParam(key, value) {
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.set(key, value);
      const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
      window.history.replaceState(null, '', newUrl);
    },
    
    removeParam(key) {
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.delete(key);
      const newUrl = searchParams.toString() 
        ? `${window.location.pathname}?${searchParams.toString()}`
        : window.location.pathname;
      window.history.replaceState(null, '', newUrl);
    }
  };

  // ========================================
  // Initialization System
  // ========================================
  const inits = new Set();
  const priorityInits = new Set();
  
  const runInits = () => {
    perfMark('ResSyncBase:runInits:start');
    
    // Set Vietnamese as default language if not set
    if (!getCookie('django_language')) {
      setCookie('django_language', 'vi');
    }
    
    // Run priority inits first
    priorityInits.forEach(fn => {
      try { fn(); } catch (err) { console.error('[ResSyncBase] Priority init error:', err); }
    });
    priorityInits.clear();
    
    // Run regular inits
    inits.forEach(fn => {
      try { fn(); } catch (err) { console.error('[ResSyncBase] Init error:', err); }
    });
    inits.clear();
    
    perfMark('ResSyncBase:runInits:end');
    
    // Log performance metrics in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      if (window.performance && performance.measure) {
        performance.measure('ResSyncBase:init', 'ResSyncBase:start', 'ResSyncBase:runInits:end');
        const measure = performance.getEntriesByName('ResSyncBase:init')[0];
        if (measure) {
          console.log(`[ResSyncBase] Initialization took ${measure.duration.toFixed(2)}ms`);
        }
      }
    }
  };
  
  const registerInit = (fn, priority = false) => {
    if (typeof fn !== 'function') return;
    
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
      // Use requestIdleCallback for non-priority inits
      if (!priority && 'requestIdleCallback' in window) {
        requestIdleCallback(() => {
          try { fn(); } catch (err) { console.error('[ResSyncBase] Init error:', err); }
        });
      } else {
        queueMicrotask(() => {
          try { fn(); } catch (err) { console.error('[ResSyncBase] Init error:', err); }
        });
      }
    } else {
      (priority ? priorityInits : inits).add(fn);
    }
  };
  
  // Use DOMContentLoaded with once option
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runInits, { once: true });
  } else {
    runInits();
  }
  
  // Initialize lazy loading
  registerInit(lazyLoadImages);
  
  // Initialize toast container
  registerInit(() => toast.init());
  
  perfMark('ResSyncBase:end');
  
  // ========================================
  // Public API
  // ========================================
  window.ResSyncBase = {
    // Core utilities
    qs,
    qsa,
    
    // Cookie management
    getCookie,
    setCookie,
    deleteCookie,
    
    // Language
    getCurrentLanguage,
    setLanguage,
    
    // Formatting
    formatNumber,
    formatDate,
    formatDateTime,
    formatTime,
    
    // UI Components
    initDropdowns,
    trapFocusWithin,
    initLanguageSwitcher,
    toast,
    modal,
    
    // Utilities
    debounce,
    throttle,
    
    // Forms
    validateForm,
    serializeForm,
    
    // AJAX
    ajax,
    
    // Storage
    storage,
    
    // URL
    url,
    
    // Lazy loading
    lazyLoadImages,
    
    // Initialization
    registerInit,
    
    // Performance
    perfMark
  };
  
  // Also expose commonly used functions globally for convenience
  window.qs = qs;
  window.qsa = qsa;
})();