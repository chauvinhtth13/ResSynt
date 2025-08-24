// static/js/default/select_study.js
'use strict';
/**
 * Client-side JavaScript for ResSync study selection page.
 * Handles dropdowns (via base), language switching, and debounced table search.
 * Ensures Vietnamese ('vi') is the default language.
 * Optimized: Added error handling, improved performance with early exits.
 */

const { getCookie, initDropdowns, registerInit } = window.ResSyncBase;

// Language switcher with user feedback and error handling
const initLanguageSwitcher = () => {
  const currentLanguageSpan = document.getElementById('current-language');
  const langMenu = document.getElementById('lang-menu');
  if (!langMenu || !currentLanguageSpan) return;

  // Initialize with server-rendered LANGUAGE_CODE or 'VI'
  let initialLang = currentLanguageSpan.textContent.trim() || 'VI';
  currentLanguageSpan.textContent = initialLang.toUpperCase();

  const links = langMenu.querySelectorAll('[data-lang]');
  links.forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const lang = link.getAttribute('data-lang');
      if (!lang) return;
      const langText = link.querySelector('span.font-semibold')?.textContent.trim() || lang.toUpperCase();

      link.style.pointerEvents = 'none';
      link.style.opacity = '0.5';
      currentLanguageSpan.textContent = langText;

      try {
        const csrfToken = getCookie('csrftoken');
        if (!csrfToken) throw new Error('CSRF token missing');
        const response = await fetch('/i18n/setlang/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
          },
          body: new URLSearchParams({
            language: lang,
            next: window.location.pathname,
          }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        window.location.reload();
      } catch (error) {
        console.error('Language switch failed:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700';
        errorDiv.textContent = 'Failed to change language. Please try again.';
        const main = document.querySelector('main');
        if (main) main.prepend(errorDiv);
        currentLanguageSpan.textContent = (getCookie('django_language') || 'vi').toUpperCase();
      } finally {
        link.style.pointerEvents = '';
        link.style.opacity = '';
      }
    });
  });
};

// Debounced table search (optimized: Uses requestAnimationFrame for smoother updates)
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
      const code = row.querySelector('[data-col="code"]')?.textContent.toLowerCase().trim() || '';
      const name = row.querySelector('[data-col="name"]')?.textContent.toLowerCase().trim() || '';
      const hidden = q && !code.includes(q) && !name.includes(q);
      row.setAttribute('hidden', hidden ? '' : null);
      if (!hidden) visible++;
    });
    if (emptyRow) emptyRow.setAttribute('hidden', visible > 0 ? '' : null);
  };

  let debounceTimeout;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      requestAnimationFrame(() => applyFilter(input.value));
    }, 300);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceTimeout);
      applyFilter(input.value);
    } else if (e.key === 'Escape') {
      input.value = '';
      applyFilter('');
      input.blur();
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

registerInit(() => {
  const cleanupDropdowns = initDropdowns();
  initLanguageSwitcher();
  initStudySearch();
  // Optional: Add window.addEventListener('beforeunload', cleanupDropdowns); if needed
});