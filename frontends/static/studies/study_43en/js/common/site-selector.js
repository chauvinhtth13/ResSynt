/**
 * Site Selection Dropdown Controller
 * ===================================
 * 
 * Seamless single-select dropdown for site filtering.
 * - Click to select and auto-apply immediately
 * - Dispatches 'siteChanged' event for chart integration
 * - No radio buttons or apply button needed
 * 
 * Version: 5.0 - Event Dispatch for Chart Integration
 */

(function() {
    'use strict';
    
    // ========================================================================
    // DOM UTILITIES
    // ========================================================================
    
    const $ = id => document.getElementById(id);
    const $$ = sel => document.querySelectorAll(sel);
    
    // ========================================================================
    // ELEMENTS
    // ========================================================================
    
    const elements = {
        get container() { return $('siteSelectContainer'); },
        get dropdown() { return $('siteSelectBtn'); },
        get label() { return $('selectedSiteLabel'); },
        get hiddenInput() { return $('selectedSiteInput'); },
        get optionsList() { return $('siteOptionsList'); }
    };
    
    // ========================================================================
    // HELPER FUNCTIONS
    // ========================================================================
    
    function getSiteOptions() {
        return Array.from($$('.site-option-btn'));
    }
    
    function getCurrentValue() {
        const hiddenInput = elements.hiddenInput;
        return hiddenInput ? hiddenInput.value : 'all';
    }
    
    // ========================================================================
    // CORE FUNCTIONS
    // ========================================================================
    
    /**
     * Dispatch site changed event for other components
     */
    function dispatchSiteChanged(newSite) {
        const event = new CustomEvent('siteChanged', {
            detail: { site: newSite },
            bubbles: true
        });
        document.dispatchEvent(event);
    }
    
    /**
     * Navigate to filtered URL immediately
     */
    function navigateToSite(siteValue) {
        const url = new URL(window.location.href);
        
        // Update URL params
        if (siteValue === 'all') {
            url.searchParams.delete('site');
            url.searchParams.set('sites', 'all');
        } else {
            url.searchParams.delete('sites');
            url.searchParams.set('site', siteValue);
        }
        
        // Navigate immediately
        window.location.href = url.toString();
    }
    
    /**
     * Handle site option click - auto navigate
     */
    function handleSiteClick(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const btn = e.currentTarget;
        const value = btn.dataset.value;
        const currentValue = getCurrentValue();
        
        // Skip if same value selected
        if (value === currentValue) {
            // Just close dropdown
            const bsDropdown = bootstrap.Dropdown.getInstance(elements.dropdown);
            if (bsDropdown) bsDropdown.hide();
            return;
        }
        
        // Add loading state to clicked item
        btn.classList.add('loading');
        btn.style.pointerEvents = 'none';
        
        // Dispatch event before navigation
        dispatchSiteChanged(value);
        
        // Navigate immediately
        navigateToSite(value);
    }
    
    /**
     * Update visual selection state
     */
    function updateActiveState() {
        const currentValue = getCurrentValue();
        const options = getSiteOptions();
        
        options.forEach(opt => {
            const isActive = opt.dataset.value === currentValue;
            opt.classList.toggle('active', isActive);
        });
    }
    
    /**
     * Get current selection value for API calls
     */
    function getSelectedSite() {
        return getCurrentValue();
    }
    
    // ========================================================================
    // EVENT HANDLERS
    // ========================================================================
    
    function bindEvents() {
        const options = getSiteOptions();
        
        // Skip if no elements
        if (!options.length) return;
        
        // Click on any site option - auto navigate
        options.forEach(opt => {
            opt.addEventListener('click', handleSiteClick);
        });
    }
    
    // ========================================================================
    // INITIALIZATION
    // ========================================================================
    
    function init() {
        bindEvents();
        updateActiveState();
    }
    
    // DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose for external access
    window.SiteSelect = {
        getSelectedSite,
        navigateToSite,
        dispatchSiteChanged
    };

})();
