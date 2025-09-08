// static/js/default/dashboard.js
(() => {
  const { qs, initDropdowns, trapFocusWithin, initLanguageSwitcher, registerInit } = window.ResSyncBase;

  // Sidebar toggle
  const initSidebarToggle = () => {
    const toggleBtn = qs('#toggleSidebarBtn');
    if (!toggleBtn) return;

    const mqlDesktop = matchMedia('(min-width: 768px)');
    const STORAGE_KEY = 'sidebarCollapsed';

    const updateToggleState = (isCollapsed) => {
      toggleBtn.setAttribute('aria-label', isCollapsed ? toggleBtn.dataset.showLabel || 'Show sidebar' : toggleBtn.dataset.hideLabel || 'Hide sidebar');
      toggleBtn.setAttribute('aria-pressed', String(isCollapsed));
      const svg = toggleBtn.querySelector('svg');
      if (svg) svg.style.transform = isCollapsed ? 'rotate(0deg)' : 'rotate(-180deg)';
    };

    const toggleSidebar = (forceState = null) => {
      const isCollapsed = forceState ?? !document.body.classList.contains('sidebar-collapsed');
      document.body.classList.toggle('sidebar-collapsed', isCollapsed);
      updateToggleState(isCollapsed);
      localStorage.setItem(STORAGE_KEY, isCollapsed ? '1' : '0');
      return isCollapsed;
    };

    const initState = () => {
      if (mqlDesktop.matches) {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored !== null) toggleSidebar(stored === '1');
      }
    };

    initState();
    toggleBtn.addEventListener('click', () => toggleSidebar());
    mqlDesktop.addEventListener('change', initState);
  };

  // Back trap
  const initBackTrap = () => {
      // Disable browser back button
      history.pushState(null, null, location.href);
      
      window.addEventListener('popstate', (e) => {
          history.pushState(null, null, location.href);
          // Show warning instead of allowing back
          if (confirm('Do you want to go back to study selection? This will release the current database.')) {
              window.location.href = '/select-study/';
          }
      });
  };

  // Force reload on back/forward
  const initReloadOnBack = () => {
    const navEntry = performance.getEntriesByType('navigation')[0];
    if (navEntry?.type === 'back_forward') {
      location.reload();
      return;
    }

    addEventListener('pageshow', (event) => {
      if (event.persisted) location.reload();
    });
  };

  // Mobile sidebar focus trap
  const initMobileSidebarTrap = () => {
    const sidebar = qs('#sidebar');
    if (!sidebar) return;

    const mqlMobile = matchMedia('(max-width: 767px)');
    let untrap = null;

    const handleMediaChange = (e) => {
      if (e.matches && !untrap) {
        untrap = trapFocusWithin(sidebar);
      } else if (!e.matches && untrap) {
        untrap();
        untrap = null;
      }
    };

    handleMediaChange(mqlMobile);
    mqlMobile.addEventListener('change', handleMediaChange);
  };

  registerInit(() => {
    initSidebarToggle();
    initDropdowns();
    initLanguageSwitcher();
    initBackTrap();
    initReloadOnBack();
    initMobileSidebarTrap();
  });
})();