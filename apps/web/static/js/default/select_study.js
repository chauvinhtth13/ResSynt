/**
 * Client-side JavaScript for ResSync study selection page.
 * Handles dropdowns, language switching, and debounced table search.
 * Ensures Vietnamese ('vi') is the default language.
 */

const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  return parts.length === 2 ? decodeURIComponent(parts.pop().split(';').shift()) : null;
};

// Dropdowns (accessible, touch-friendly)
const initDropdowns = () => {
  const dropdowns = document.querySelectorAll('[data-dropdown]');

  const closeAll = (except) => {
    dropdowns.forEach(dropdown => {
      const menu = dropdown.querySelector('[data-dropdown-menu]');
      const trigger = dropdown.querySelector('[data-dropdown-trigger]');
      if (!menu || menu === except) return;
      menu.setAttribute('hidden', '');
      trigger?.setAttribute('aria-expanded', 'false');
    });
  };

  const toggleDropdown = (trigger, dropdown, menu) => {
    const isOpen = !menu.hasAttribute('hidden');
    closeAll();
    if (!isOpen) {
      menu.removeAttribute('hidden');
      trigger.setAttribute('aria-expanded', 'true');
      const firstFocusable = menu.querySelector('a,button,[tabindex]:not([tabindex="-1"])');
      firstFocusable?.focus({ preventScroll: true });
    }
  };

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-dropdown-trigger]');
    if (trigger) {
      const dropdown = trigger.closest('[data-dropdown]');
      const menu = dropdown?.querySelector('[data-dropdown-menu]');
      if (menu) toggleDropdown(trigger, dropdown, menu);
      return;
    }
    if (!e.target.closest('[data-dropdown]')) closeAll();
  });

  document.addEventListener('touchstart', (e) => {
    const trigger = e.target.closest('[data-dropdown-trigger]');
    if (trigger) {
      e.preventDefault();
      const dropdown = trigger.closest('[data-dropdown]');
      const menu = dropdown?.querySelector('[data-dropdown-menu]');
      if (menu) toggleDropdown(trigger, dropdown, menu);
      return;
    }
    if (!e.target.closest('[data-dropdown]')) closeAll();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const openMenu = document.querySelector('[data-dropdown-menu]:not([hidden])');
    if (openMenu) {
      closeAll();
      const trigger = openMenu.closest('[data-dropdown]')?.querySelector('[data-dropdown-trigger]');
      trigger?.focus();
    }
  });
};

// Language switcher with user feedback
const initLanguageSwitcher = () => {
  const currentLanguageSpan = document.getElementById('current-language');
  const langMenu = document.getElementById('lang-menu');
  if (!langMenu || !currentLanguageSpan) return;

  // Initialize with server-rendered LANGUAGE_CODE or 'VI'
  const initialLang = currentLanguageSpan.textContent || 'VI';
  currentLanguageSpan.textContent = initialLang;

  langMenu.querySelectorAll('[data-lang]').forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const lang = link.getAttribute('data-lang');
      const langText = link.querySelector('span.font-semibold')?.textContent || lang.toUpperCase();

      link.style.pointerEvents = 'none';
      link.style.opacity = '0.5';
      currentLanguageSpan.textContent = langText;

      try {
        const response = await fetch('/i18n/setlang/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken') || '',
          },
          body: new URLSearchParams({
            language: lang,
            next: window.location.pathname,
          }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        window.location.reload();
      } catch (error) {
        console.error('Language switch failed:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700';
        errorDiv.textContent = 'Failed to change language. Please try again.';
        document.querySelector('main').prepend(errorDiv);
        currentLanguageSpan.textContent = getCookie('django_language')?.toUpperCase() || 'VI';
      } finally {
        link.style.pointerEvents = '';
        link.style.opacity = '';
      }
    });
  });
};

// Debounced table search
const initStudySearch = () => {
  const input = document.getElementById('study-id-search');
  const tbody = document.getElementById('studies-body');
  if (!input || !tbody) return;

  const rows = Array.from(tbody.querySelectorAll('[data-row]'));
  const emptyRow = tbody.querySelector('[data-empty-row]');

  const applyFilter = (query) => {
    const q = (query || '').trim().toLowerCase();
    let visible = 0;
    rows.forEach(row => {
      const code = row.querySelector('[data-col="code"]')?.textContent.toLowerCase() || '';
      const name = row.querySelector('[data-col="name"]')?.textContent.toLowerCase() || '';
      row.style.display = (q && !code.includes(q) && !name.includes(q)) ? 'none' : '';
      if (!row.style.display) visible++;
    });
    if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
  };

  let debounceTimeout;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => applyFilter(input.value), 300);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceTimeout);
      applyFilter(input.value);
    } else if (e.key === 'Escape') {
      input.value = '';
      applyFilter('');
    }
  });

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      input.focus();
      input.select();
    }
  });

  applyFilter(input.value);
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initDropdowns();
  initLanguageSwitcher();
  initStudySearch();
});