// static/js/default/base.js
'use strict';

(() => {
  // Query shortcuts
  const qs = (s, el = document) => el.querySelector(s);
  const qsa = (s, el = document) => Array.from(el.querySelectorAll(s));

  // Cookie getter
  const getCookie = (name) => {
    if (!name) return null;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? decodeURIComponent(parts.pop().split(';').shift()) : null;
  };

  // Dropdown handler
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
        requestAnimationFrame(() => {
          const firstFocusable = qs(
            'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
            menu
          );
          if (firstFocusable) firstFocusable.focus({ preventScroll: true });
        });
      }
    };

    const handleInteraction = (e) => {
      const trigger = e.target.closest('[data-dropdown-trigger], .dropdown-trigger');
      if (trigger) {
        const dropdown = trigger.closest('[data-dropdown]');
        if (dropdown) {
          const menu = qs('[data-dropdown-menu], .dropdown-menu', dropdown);
          if (menu) {
            // If trigger is a link, avoid navigation
            if (trigger.tagName === 'A') e.preventDefault();
            e.stopPropagation();
            toggleDropdown(trigger, dropdown, menu);
            return;
          }
        }
      }
      // Clicked outside any menu: close all
      if (!e.target.closest('[data-dropdown-menu], .dropdown-menu')) closeAll();
    };

    const handleKeydown = (e) => {
      if (e.key === 'Escape') {
        const openDropdown = Array.from(dropdownStates.entries()).find(([_, isOpen]) => isOpen);
        if (openDropdown) {
          closeAll();
          const trigger = qs('[data-dropdown-trigger], .dropdown-trigger', openDropdown[0]);
          if (trigger) trigger.focus();
        }
      }
    };

    // Note: use non-passive for click so we can preventDefault on anchors if needed
    document.addEventListener('click', handleInteraction, { passive: false });
    document.addEventListener('keydown', handleKeydown, { passive: true });

    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleKeydown);
    };
  };

  // Focus trap
  const trapFocusWithin = (container) => {
    if (!container) return () => {};

    let focusables = [];
    const updateFocusables = () => {
      focusables = qsa(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        container
      ).filter(el => el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden');
    };

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

    const observer = new MutationObserver(updateFocusables);
    observer.observe(container, { childList: true, subtree: true });
    container.addEventListener('keydown', onKey);

    return () => {
      observer.disconnect();
      container.removeEventListener('keydown', onKey);
    };
  };

  // Language switcher
  const initLanguageSwitcher = (config = {}) => {
    const {
      currentLangId = 'current-language',
      langMenuId = 'lang-menu',
      errorContainer = 'main',
      setLangUrl = '/i18n/setlang/'  // default fallback
    } = config;

    const currentLangSpan = document.getElementById(currentLangId);
    const langMenu = document.getElementById(langMenuId);
    if (!langMenu || !currentLangSpan) return () => {};

    // Auto-detect action from the form inside the menu if present
    const formAction = langMenu.querySelector('form')?.getAttribute('action') || null;
    const finalSetLangUrl = formAction || setLangUrl;

    const defaultLang = getCookie('django_language') || 'vi';
    currentLangSpan.textContent = defaultLang.toUpperCase();

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
      const link = e.target.closest('[data-lang]');
      if (!link) return;
      e.preventDefault();

      const lang = link.getAttribute('data-lang');
      if (!lang) return;

      const langText = link.querySelector('span.font-semibold')?.textContent.trim() || lang.toUpperCase();
      const prevText = currentLangSpan.textContent;
      currentLangSpan.textContent = langText;

      // Visual disable while request in flight
      link.style.pointerEvents = 'none';
      link.classList.add('opacity-50');

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
          location.reload();
        } else {
          throw new Error(`Failed: ${response.status}`);
        }
      } catch (error) {
        showError('Failed to change language. Please try again.');
        currentLangSpan.textContent = prevText || defaultLang.toUpperCase();
      } finally {
        link.style.pointerEvents = '';
        link.classList.remove('opacity-50');
      }
    };

    langMenu.addEventListener('click', handleLangChange);

    return () => langMenu.removeEventListener('click', handleLangChange);
  };

  // ===== Init system (fixed for defer + late registrants) =====
  const inits = new Set();

  const runInits = () => {
    inits.forEach(fn => {
      try { fn(); } catch (err) { console.error('[ResSyncBase] init error:', err); }
    });
    inits.clear();
  };

  const registerInit = (fn) => {
    if (typeof fn !== 'function') return;
    // If DOM already parsed, run this init on the next microtask
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
      queueMicrotask(() => {
        try { fn(); } catch (err) { console.error('[ResSyncBase] init error:', err); }
      });
    } else {
      inits.add(fn);
    }
  };

  // Always flush any queued inits at DOMContentLoaded
  document.addEventListener('DOMContentLoaded', runInits, { once: true });

  // Expose API
  window.ResSyncBase = {
    qs,
    qsa,
    getCookie,
    initDropdowns,
    trapFocusWithin,
    initLanguageSwitcher,
    registerInit
  };
})();