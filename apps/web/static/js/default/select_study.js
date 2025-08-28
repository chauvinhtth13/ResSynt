// static/js/default/select_study.js
(() => {
  const { initDropdowns, initLanguageSwitcher, registerInit } = window.ResSyncBase;

  // Study search
  const initStudySearch = () => {
    const input = document.getElementById('study-id-search');
    const tbody = document.getElementById('studies-body');
    if (!input || !tbody) return;

    const rows = tbody.querySelectorAll('[data-row]');
    const emptyRow = tbody.querySelector('[data-empty-row]');

    const rowCache = Array.from(rows).map(row => ({
      element: row,
      code: (row.querySelector('[data-col="code"]')?.textContent || '').toLowerCase().trim(),
      name: (row.querySelector('[data-col="name"]')?.textContent || '').toLowerCase().trim()
    }));

    const applyFilter = (query) => {
      const q = (query || '').trim().toLowerCase();
      let visibleCount = 0;

      rowCache.forEach(({ element, code, name }) => {
        const match = !q || code.includes(q) || name.includes(q);
        element.hidden = !match;
        if (match) visibleCount++;
      });

      if (emptyRow) emptyRow.hidden = visibleCount > 0;

      const liveRegion = document.getElementById('search-results-status');
      if (liveRegion) {
        liveRegion.textContent = q ? `${visibleCount} results found` : `Showing all ${rowCache.length} studies`;
      }
    };

    let debounceTimer = null;
    input.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => applyFilter(e.target.value), 300);
    }, { passive: true });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        clearTimeout(debounceTimer);
        applyFilter(input.value);
      } else if (e.key === 'Escape') {
        input.value = '';
        applyFilter('');
        input.blur();
      }
    });

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        const tag = (document.activeElement?.tagName || '').toLowerCase();
        if (['input', 'textarea', 'select'].includes(tag) && document.activeElement !== input) return;
        e.preventDefault();
        input.focus();
        input.select();
      }
    });

    if (input.value) applyFilter(input.value);
  };

  registerInit(() => {
    initDropdowns();
    initLanguageSwitcher();
    initStudySearch();
  });
})();