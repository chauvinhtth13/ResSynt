// static/js/default/dashboard.js
const qs = (s, el = document) => el.querySelector(s);
const qsa = (s, el = document) => el.querySelectorAll(s);

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
  container.addEventListener('keydown', onKey, { passive: true });
  return () => container.removeEventListener('keydown', onKey);
}

document.addEventListener('DOMContentLoaded', () => {
  const toggleSidebarBtn = qs('#toggleSidebarBtn');
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
  toggleSidebarBtn?.addEventListener('click', toggleSidebar, { passive: true });

  // General dropdown handling
  const dropdowns = qsa('[data-dropdown]');
  dropdowns.forEach(drop => {
    const trigger = drop.querySelector('.dropdown-trigger');
    const menu = drop.querySelector('.dropdown-menu');
    if (trigger && menu) {
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = menu.classList.contains('hidden');
        menu.classList.toggle('hidden', !isHidden);
        trigger.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
      }, { passive: true });
      document.addEventListener('click', (e) => {
        if (!drop.contains(e.target)) {
          menu.classList.add('hidden');
          trigger.setAttribute('aria-expanded', 'false');
        }
      }, { passive: true });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          menu.classList.add('hidden');
          trigger.setAttribute('aria-expanded', 'false');
        }
      }, { passive: true });
    }
  });

  // Handle "Choose another study" to block back
  const chooseStudyForm = qs('[data-choose-study-form]');
  if (chooseStudyForm) {
    chooseStudyForm.addEventListener('submit', (e) => {
      history.pushState(null, '', location.href);  // Push dummy state to trap back
      history.pushState(null, '', location.href);  // Multiple to block multiple backs
      // Form submits POST, no need for replace
    }, { passive: true });
  }

  // Trap back button
  window.addEventListener('popstate', () => {
    history.go(1);  // Force forward on back
  }, { passive: true });
});