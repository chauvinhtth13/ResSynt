// static/js/default/dashboard.js
'use strict';

const { qs, qsa, initDropdowns, trapFocusWithin, registerInit } = window.ResSyncBase;

// Toggle sidebar (optimized: Handles missing elements, uses dataset safely)
const initSidebarToggle = () => {
  const toggleSidebarBtn = qs('#toggleSidebarBtn');
  if (!toggleSidebarBtn) return;

  const mqlDesktop = window.matchMedia('(min-width: 768px)');

  // Restore desktop collapsed state
  if (mqlDesktop.matches) {
    const collapsed = localStorage.getItem('sidebarCollapsed') === '1';
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    updateToggleState(toggleSidebarBtn, collapsed);
  }

  toggleSidebarBtn.addEventListener('click', () => {
    const isCollapsed = document.body.classList.toggle('sidebar-collapsed');
    updateToggleState(toggleSidebarBtn, isCollapsed);
    localStorage.setItem('sidebarCollapsed', isCollapsed ? '1' : '0');
  });
};

const updateToggleState = (btn, isCollapsed) => {
  btn.setAttribute('aria-label', isCollapsed ? btn.dataset.showLabel || 'Show sidebar' : btn.dataset.hideLabel || 'Hide sidebar');
  btn.setAttribute('aria-pressed', String(isCollapsed));
  const svg = btn.querySelector('svg');
  if (svg) {
    svg.classList.toggle('-rotate-180', !isCollapsed);
    svg.classList.toggle('rotate-0', isCollapsed);
  }
};

// Handle choose study form and back trap (optimized: Checks history support)
const initBackTrap = () => {
  if (!history || !history.pushState) return; // Graceful degradation

  const chooseStudyForm = qs('[data-choose-study-form]');
  if (chooseStudyForm) {
    chooseStudyForm.addEventListener('submit', () => {
      history.pushState(null, '', location.href);
      history.pushState(null, '', location.href);
    });
  }

  window.addEventListener('popstate', () => {
    history.go(1);
  });
};

// Force reload on back/forward navigation or persisted page show
const initReloadOnBack = () => {
  // Check for back_forward navigation type
  if (performance.getEntriesByType('navigation')[0].type === 'back_forward') {
    window.location.reload();
  }

  // Add event listener for pageshow if persisted (bfcache)
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      window.location.reload();
    }
  });
};

registerInit(() => {
  initSidebarToggle();
  const cleanupDropdowns = initDropdowns();
  initBackTrap();
  initReloadOnBack();

  // Apply trapFocus if sidebar exists (assuming #sidebar for mobile)
  const sidebar = qs('#sidebar'); // Adjust selector as needed
  if (sidebar && !window.matchMedia('(min-width: 768px)').matches) {
    const untrap = trapFocusWithin(sidebar);
    // Optional: Add event to remove trap when sidebar closes
  }
});