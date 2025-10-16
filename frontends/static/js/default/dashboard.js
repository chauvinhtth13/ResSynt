// frontends/static/js/default/sidebar.js
(() => {
  // ==========================================
  // SIDEBAR MANAGER - Xử lý toggle/responsive
  // ==========================================
  class SidebarManager {
    constructor(config = {}) {
      // Configuration
      this.config = {
        sidebarId: config.sidebarId || 'sidebar',
        toggleId: config.toggleId || 'sidebarToggle',
        overlayId: config.overlayId || 'sidebarOverlay',
        mainContentId: config.mainContentId || 'mainContent',
        breakpoint: config.breakpoint || 992,
        resizeDelay: config.resizeDelay || 250
      };

      // DOM Elements
      this.sidebar = document.getElementById(this.config.sidebarId);
      this.sidebarToggle = document.getElementById(this.config.toggleId);
      this.overlay = document.getElementById(this.config.overlayId);
      this.mainContent = document.getElementById(this.config.mainContentId);

      // Validate elements
      if (!this.sidebar || !this.sidebarToggle) {
        console.warn('[sidebar.js] Missing required elements:', {
          sidebar: this.sidebar,
          sidebarToggle: this.sidebarToggle,
          overlay: this.overlay,
          mainContent: this.mainContent
        });
        return;
      }

      // State
      this.resizeTimer = null;

      // Initialize
      this.bind();
    }

    bind() {
      // Toggle button click
      this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());

      // Overlay click
      if (this.overlay) {
        this.overlay.addEventListener('click', () => this.closeSidebar());
      }

      // ESC key
      document.addEventListener('keydown', (e) => this.handleEscapeKey(e));

      // Window resize
      window.addEventListener('resize', () => this.handleResize());
    }

    isDesktop() {
      return window.innerWidth >= this.config.breakpoint;
    }

    toggleSidebar() {
      if (this.isDesktop()) {
        // Desktop mode
        this.sidebar.classList.toggle('hide');
        if (this.mainContent) {
          this.mainContent.classList.toggle('sidebar-hidden');
        }
      } else {
        // Mobile mode
        this.sidebar.classList.toggle('show');
        if (this.overlay) {
          this.overlay.classList.toggle('d-none');
        }
      }
    }

    openSidebar() {
      if (!this.isDesktop()) {
        this.sidebar.classList.add('show');
        if (this.overlay) {
          this.overlay.classList.remove('d-none');
        }
      }
    }

    closeSidebar() {
      this.sidebar.classList.remove('show');
      if (this.overlay) {
        this.overlay.classList.add('d-none');
      }
    }

    handleEscapeKey(e) {
      if (e.key === 'Escape' && this.sidebar.classList.contains('show')) {
        this.closeSidebar();
      }
    }

    handleResize() {
      clearTimeout(this.resizeTimer);
      this.resizeTimer = setTimeout(() => {
        if (!this.isDesktop() && this.overlay) {
          this.overlay.classList.add('d-none');
        }
      }, this.config.resizeDelay);
    }

    isOpen() {
      if (this.isDesktop()) {
        return !this.sidebar.classList.contains('hide');
      } else {
        return this.sidebar.classList.contains('show');
      }
    }
  }

  // ==========================================
  // SIDEBAR ACTIVE MANAGER - Xử lý active state
  // ==========================================
  class SidebarActiveManager {
    constructor() {
      // Configuration
      this.config = {
        linkSelector: '.sidebar-link',
        activeClass: 'active',
        storageKey: 'sidebar-active-link',
        checkUrlMatch: true
      };

      // Initialize
      this.init();
    }

    init() {
      // Wait for DOM ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setup());
      } else {
        this.setup();
      }
    }

    setup() {
      // Get all sidebar links
      this.links = document.querySelectorAll(this.config.linkSelector);
      
      if (this.links.length === 0) {
        console.warn('[SidebarActiveManager] No sidebar links found');
        return;
      }

      // Bind click events
      this.bindClickEvents();
      
      // Set initial active state
      this.setInitialActiveState();
      
      // Handle browser back/forward
      window.addEventListener('popstate', () => this.setActiveByUrl());
    }

    bindClickEvents() {
      this.links.forEach(link => {
        link.addEventListener('click', (e) => {
          // Don't prevent default - let the link navigate
          // Just handle the active state
          this.setActive(link);
        });
      });
    }

    setActive(clickedLink) {
      // Remove active class from all links
      this.links.forEach(link => {
        link.classList.remove(this.config.activeClass);
        
        // Also check parent li element (for nested items)
        const parentLi = link.closest('li');
        if (parentLi) {
          parentLi.classList.remove(this.config.activeClass);
        }
      });

      // Add active class to clicked link
      clickedLink.classList.add(this.config.activeClass);
      
      // Also add to parent li if exists
      const parentLi = clickedLink.closest('li');
      if (parentLi) {
        parentLi.classList.add(this.config.activeClass);
      }

      // If the link is inside a collapsible card, ensure it's expanded
      const card = clickedLink.closest('.sidebar-card');
      if (card) {
        this.expandParentCard(card);
      }

      // Save to localStorage
      this.saveActiveState(clickedLink.getAttribute('href'));
    }

    expandParentCard(card) {
      // If using Bootstrap collapse, ensure the card is expanded
      const collapseElement = card.querySelector('.collapse');
      if (collapseElement && window.bootstrap) {
        const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseElement, {
          toggle: false
        });
        bsCollapse.show();
      }
    }

    setInitialActiveState() {
      // First priority: Check current URL
      if (this.config.checkUrlMatch) {
        const activeSet = this.setActiveByUrl();
        if (activeSet) return;
      }

      // Second priority: Check localStorage
      const savedHref = localStorage.getItem(this.config.storageKey);
      if (savedHref) {
        const savedLink = this.findLinkByHref(savedHref);
        if (savedLink) {
          this.setActive(savedLink);
          return;
        }
      }

      // Third priority: Set first link as active if no active state
      const hasActive = Array.from(this.links).some(link => 
        link.classList.contains(this.config.activeClass)
      );
      
      if (!hasActive && this.links.length > 0) {
        // Skip setting first link active if it's a # link
        const firstValidLink = Array.from(this.links).find(link => 
          link.getAttribute('href') !== '#'
        );
        if (firstValidLink) {
          this.setActive(firstValidLink);
        }
      }
    }

    setActiveByUrl() {
      const currentPath = window.location.pathname;
      const currentUrl = window.location.href;
      
      // Find exact match first
      let matchedLink = this.findLinkByHref(currentUrl) || 
                        this.findLinkByHref(currentPath);
      
      // If no exact match, try to find best partial match
      if (!matchedLink) {
        matchedLink = this.findBestMatchingLink(currentPath);
      }

      if (matchedLink) {
        this.setActive(matchedLink);
        return true;
      }
      
      return false;
    }

    findLinkByHref(href) {
      if (!href) return null;
      
      return Array.from(this.links).find(link => {
        const linkHref = link.getAttribute('href');
        if (!linkHref || linkHref === '#') return false;
        
        // Check exact match
        if (linkHref === href) return true;
        
        // Check if absolute URL matches
        try {
          const linkUrl = new URL(linkHref, window.location.origin);
          const targetUrl = new URL(href, window.location.origin);
          return linkUrl.href === targetUrl.href;
        } catch (e) {
          return false;
        }
      });
    }

    findBestMatchingLink(currentPath) {
      let bestMatch = null;
      let bestMatchLength = 0;
      
      this.links.forEach(link => {
        const linkHref = link.getAttribute('href');
        if (!linkHref || linkHref === '#') return;
        
        try {
          const linkUrl = new URL(linkHref, window.location.origin);
          const linkPath = linkUrl.pathname;
          
          // Check if current path includes link path
          if (currentPath.includes(linkPath) && linkPath !== '/') {
            if (linkPath.length > bestMatchLength) {
              bestMatch = link;
              bestMatchLength = linkPath.length;
            }
          }
        } catch (e) {
          // Invalid URL, skip
        }
      });
      
      return bestMatch;
    }

    saveActiveState(href) {
      if (href && href !== '#') {
        localStorage.setItem(this.config.storageKey, href);
      }
    }

    // Public method to manually set active link
    setActiveLink(href) {
      const link = this.findLinkByHref(href);
      if (link) {
        this.setActive(link);
      }
    }

    // Public method to clear active state
    clearActive() {
      this.links.forEach(link => {
        link.classList.remove(this.config.activeClass);
      });
      localStorage.removeItem(this.config.storageKey);
    }
  }

  // ==========================================
  // INITIALIZATION
  // ==========================================
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize Sidebar Manager (toggle/responsive)
    window.sidebarManager = new SidebarManager();

    // Initialize Sidebar Active Manager (active states)
    window.sidebarActiveManager = new SidebarActiveManager();

    // Add smooth scroll behavior for internal links
    document.querySelectorAll('.sidebar-link[href^="#"]').forEach(link => {
      link.addEventListener('click', (e) => {
        const targetId = link.getAttribute('href');
        if (targetId && targetId !== '#') {
          const targetElement = document.querySelector(targetId);
          if (targetElement) {
            e.preventDefault();
            targetElement.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
            // Still set active state
            window.sidebarActiveManager.setActive(link);
          }
        }
      });
    });

    // Bootstrap Tooltip initialization for sidebar items
    if (window.bootstrap) {
      // Initialize tooltips for sidebar links if they have title attribute
      const tooltipTriggerList = document.querySelectorAll('.sidebar-link[title]');
      const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
        new bootstrap.Tooltip(tooltipTriggerEl, {
          placement: 'right',
          delay: { show: 500, hide: 100 }
        })
      );
    }

    // Optional: Custom configuration example (commented out)
    // window.sidebarManager = new SidebarManager({
    //   sidebarId: 'customSidebar',
    //   toggleId: 'customToggle',
    //   overlayId: 'customOverlay',
    //   mainContentId: 'customMainContent',
    //   breakpoint: 1024,
    //   resizeDelay: 300
    // });
  });
})();