const qs = (s, el = document) => el.querySelector(s);

// Simplified focus trap for mobile sidebar
function trapFocusWithin(container) {
  const focusables = Array.from(
    container.querySelectorAll('a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])')
  ).filter(el => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && el.tabIndex !== -1);
  if (!focusables.length) return () => {};
  const first = focusables[0], last = focusables[focusables.length - 1];
  const onKey = (e) => {
    if (e.key !== 'Tab') return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };
  container.addEventListener('keydown', onKey);
  return () => container.removeEventListener('keydown', onKey);
}

document.addEventListener('DOMContentLoaded', () => {
  const toggleSidebarBtn = qs('#toggleSidebarBtn');
  const userMenuBtn = qs('#userMenuBtn');
  const userMenu = qs('#userMenu');
  const mqlDesktop = window.matchMedia('(min-width: 768px)');

  // Restore desktop collapsed state
  if (mqlDesktop.matches && localStorage.getItem('sidebarCollapsed') === '1') {
    document.body.classList.add('sidebar-collapsed');
  }

  // Desktop toggle (collapse)
  const toggleSidebar = () => {
    if (!toggleSidebarBtn) return;
    const isCollapsed = document.body.classList.toggle('sidebar-collapsed');
    toggleSidebarBtn.setAttribute('aria-label', isCollapsed ? toggleSidebarBtn.dataset.showLabel : toggleSidebarBtn.dataset.hideLabel);
    toggleSidebarBtn.setAttribute('aria-pressed', String(isCollapsed));
    const svg = toggleSidebarBtn.querySelector('svg');
    if (svg) {
      svg.classList.toggle('-rotate-180', !isCollapsed);
      svg.classList.toggle('rotate-0', isCollapsed);
    }
    localStorage.setItem('sidebarCollapsed', isCollapsed ? '1' : '0');
  };
  toggleSidebarBtn?.addEventListener('click', toggleSidebar);

  // User menu
  const hideUserMenu = () => {
    if (userMenu) userMenu.classList.add('hidden');
    if (userMenuBtn) userMenuBtn.setAttribute('aria-expanded', 'false');
  };
  const showUserMenu = () => {
    if (userMenu) userMenu.classList.remove('hidden');
    if (userMenuBtn) userMenuBtn.setAttribute('aria-expanded', 'true');
  };

  // Delegated click handler for dropdowns
  document.addEventListener('click', (e) => {
    if (userMenuBtn?.contains(e.target)) {
      e.stopPropagation();
      userMenu?.classList.contains('hidden') ? showUserMenu() : hideUserMenu();
    } else if (userMenu && !userMenu.contains(e.target)) {
      hideUserMenu();
    }
  });

});