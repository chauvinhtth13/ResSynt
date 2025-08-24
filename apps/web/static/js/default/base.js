'use strict';
/**
 * Base utilities for ResSync client-side JS.
 * Includes query shortcuts, cookie getter, dropdown handling, focus trap, and init system.
 * Optimized for performance, accessibility, and minimal redundancy.
 * - Uses passive event listeners where possible.
 * - Ensures proper ARIA attributes and focus management.
 * - Minimizes global namespace pollution.
 */

// Query shortcuts
const qs = (s, el = document) => el.querySelector(s);
const qsa = (s, el = document) => el.querySelectorAll(s);

// Get cookie by name (secure: decodes URI component)
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  return parts.length === 2 ? decodeURIComponent(parts.pop().split(';').shift()) : null;
};

// Standardized dropdown handling (optimized: merged click/touch, reduced redundancy)
const initDropdowns = (selector = '[data-dropdown]') => {
  const dropdowns = qsa(selector);
  if (!dropdowns.length) return () => {}; // Early exit if no dropdowns

  const closeAll = (except = null) => {
    dropdowns.forEach(dropdown => {
      const menu = qs('[data-dropdown-menu], .dropdown-menu', dropdown);
      const trigger = qs('[data-dropdown-trigger], .dropdown-trigger', dropdown);
      if (!menu || menu === except) return;
      menu.setAttribute('hidden', '');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  };

  const toggleDropdown = (trigger, dropdown, menu) => {
    const isOpen = !menu.hasAttribute('hidden');
    closeAll(menu);
    if (isOpen) {
      menu.setAttribute('hidden', '');
      trigger.setAttribute('aria-expanded', 'false');
    } else {
      menu.removeAttribute('hidden');
      trigger.setAttribute('aria-expanded', 'true');
      const firstFocusable = qs('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])', menu);
      firstFocusable?.focus({ preventScroll: true });
    }
  };

  const handleInteraction = (e, isTouch = false) => {
    if (isTouch) e.preventDefault();
    const trigger = e.target.closest('[data-dropdown-trigger], .dropdown-trigger');
    if (trigger) {
      const dropdown = trigger.closest('[data-dropdown]');
      const menu = qs('[data-dropdown-menu], .dropdown-menu', dropdown);
      if (menu) {
        toggleDropdown(trigger, dropdown, menu);
        return;
      }
    }
    if (!e.target.closest('[data-dropdown]')) closeAll();
  };

  const handleKeydown = (e) => {
    if (e.key !== 'Escape') return;
    const openMenu = qs('[data-dropdown-menu]:not([hidden]), .dropdown-menu:not([hidden])');
    if (openMenu) {
      closeAll();
      const trigger = openMenu.closest('[data-dropdown]')?.querySelector('[data-dropdown-trigger], .dropdown-trigger');
      trigger?.focus();
    }
  };

  document.addEventListener('click', (e) => handleInteraction(e), { passive: true });
  document.addEventListener('touchstart', (e) => handleInteraction(e, true), { passive: false });
  document.addEventListener('keydown', handleKeydown, { passive: true });

  return () => {
    document.removeEventListener('click', handleInteraction);
    document.removeEventListener('touchstart', handleInteraction);
    document.removeEventListener('keydown', handleKeydown);
  };
};

// Focus trap utility (optimized: stricter filtering, minimal DOM queries)
const trapFocusWithin = (container) => {
  if (!container) return () => {};
  const focusables = Array.from(
    qsa('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])', container)
  ).filter(el => el.offsetParent !== null && !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true');
  if (!focusables.length) return () => {};
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
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
};

// Init system: Run registered functions on DOMContentLoaded
const inits = [];
const registerInit = (fn) => inits.push(fn);
document.addEventListener('DOMContentLoaded', () => {
  inits.forEach(fn => {
    try {
      fn();
    } catch (error) {
      console.error('Init function error:', error);
    }
  });
  inits.length = 0; // Clear inits to prevent re-running
});

// Expose utilities to global namespace
window.ResSyncBase = {
  qs,
  qsa,
  getCookie,
  initDropdowns,
  trapFocusWithin,
  registerInit
};