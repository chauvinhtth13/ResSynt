/**
 * Smart Address System - DUAL MODE (NEW + OLD)
 * ==============================================
 * 
 * COMBINES:
 * 1. OLD STRUCTURE (smart_address_hcmc.js v3.4) - District → Ward → Street
 * 2. NEW STRUCTURE (smart_address_unified.js v4.0) - Direct Wards
 * 
 * Data sources:
 * - OLD: /static/SG.json (24 districts, thien0291/vietnam_dataset)
 * - NEW: /static/vn_wards_new.json (168 direct wards)
 * 
 * @version 5.0 - Production Ready
 * @author Claude
 * @date 2026-01-15
 */

(function() {
    'use strict';
    
    // ========================================================================
    // CONFIGURATION
    // ========================================================================
    
    const CONFIG = {
        // Data sources
        OLD_STRUCTURE_URL: '/static/SG.json',              // With districts
        NEW_STRUCTURE_URL: '/static/vn_wards_new.json',    // Direct wards
        
        // Mode detection
        MODE: 'auto', // 'old', 'new', or 'auto'
        
        // Element IDs - BOTH modes supported
        // OLD mode elements:
        DISTRICT_SELECT_ID: 'district-select',
        WARD_SELECT_ID: 'ward-select',
        STREET_INPUT_ID: 'street-autocomplete',
        STREET_SUGGESTIONS_ID: 'street-suggestions',
        WARD_HIDDEN_INPUT_ID: 'ward-hidden-input',
        DISTRICT_HIDDEN_INPUT_ID: 'district-hidden-input',
        
        // NEW mode elements:
        WARD_SELECT_NEW_ID: 'ward-select-new',
        WARD_HIDDEN_INPUT_NEW_ID: 'ward-hidden-input-new',
        
        // Common elements:
        FULL_ADDRESS_INPUT_ID: 'full-address-input',
        ADDRESS_PREVIEW_ID: 'address-preview',
        ADDRESS_PREVIEW_TEXT_ID: 'address-preview-text',
        
        // Search settings
        MIN_SEARCH_LENGTH: 1,
        MAX_SUGGESTIONS: 20,
        
        DEBUG: true
    };
    
    // ========================================================================
    // STATE
    // ========================================================================
    
    const state = {
        mode: null,                  // 'old' or 'new'
        data: null,                  // Loaded JSON data
        currentDistrict: null,       // For OLD mode
        currentDistrictIndex: null,  // For OLD mode
        currentWard: null,
        currentWardIndex: null,
        availableStreets: [],
        selectedStreetIndex: -1,
        initialized: false
    };
    
    // ========================================================================
    // DOM ELEMENTS
    // ========================================================================
    
    const elements = {
        // OLD mode
        districtSelect: null,
        wardSelect: null,
        streetInput: null,
        streetSuggestions: null,
        wardHiddenInput: null,
        districtHiddenInput: null,
        
        // Common
        fullAddressInput: null,
        addressPreview: null,
        addressPreviewText: null
    };
    
    // ========================================================================
    // LOGGING
    // ========================================================================
    
    function log(msg, ...args) {
        if (CONFIG.DEBUG) console.log(`[SmartAddress] ${msg}`, ...args);
    }
    
    function logError(msg, ...args) {
        console.error(`[SmartAddress] ✗ ${msg}`, ...args);
    }
    
    function logSuccess(msg, ...args) {
        if (CONFIG.DEBUG) console.log(`[SmartAddress] ✓ ${msg}`, ...args);
    }
    
    // ========================================================================
    // INITIALIZATION
    // ========================================================================
    
    function init() {
        log('Initializing v5.0 - Dual Mode (NEW + OLD)...');
        // Guard against duplicate initialization (page scripts may call init() twice)
        if (state.initialized || window.SmartAddress?._initialized) {
            log('Already initialized - skipping duplicate init');
            return;
        }
        
        // Small delay to let enrollment.js toggle visibility first
        setTimeout(() => {
            cacheElements();
            detectMode();
            
            if (!state.mode) {
                logError('Could not detect mode');
                return;
            }
            
            log('Mode detected:', state.mode.toUpperCase());
            loadData();
        }, 100);
    }
    
    function cacheElements() {
        // Try OLD mode elements
        elements.districtSelect = document.getElementById(CONFIG.DISTRICT_SELECT_ID);
        elements.wardSelect = document.getElementById(CONFIG.WARD_SELECT_ID);
        elements.streetInput = document.getElementById(CONFIG.STREET_INPUT_ID);
        elements.streetSuggestions = document.getElementById(CONFIG.STREET_SUGGESTIONS_ID);
        elements.wardHiddenInput = document.getElementById(CONFIG.WARD_HIDDEN_INPUT_ID);
        elements.districtHiddenInput = document.getElementById(CONFIG.DISTRICT_HIDDEN_INPUT_ID);
        
        // Try NEW mode elements
        const wardSelectNew = document.getElementById(CONFIG.WARD_SELECT_NEW_ID);
        const wardHiddenNew = document.getElementById(CONFIG.WARD_HIDDEN_INPUT_NEW_ID);
        
        // Use NEW if OLD not visible
        if (wardSelectNew && isElementVisible(wardSelectNew)) {
            elements.wardSelect = wardSelectNew;
            elements.wardHiddenInput = wardHiddenNew;
        }
        
        // Common elements
        elements.fullAddressInput = document.getElementById(CONFIG.FULL_ADDRESS_INPUT_ID);
        elements.addressPreview = document.getElementById(CONFIG.ADDRESS_PREVIEW_ID);
        elements.addressPreviewText = document.getElementById(CONFIG.ADDRESS_PREVIEW_TEXT_ID);

        // Diagnostic: report what we found
        log('Cached elements:', {
            districtSelect: !!elements.districtSelect,
            wardSelect: !!elements.wardSelect,
            streetInput: !!elements.streetInput,
            wardHiddenInput: !!elements.wardHiddenInput,
            districtHiddenInput: !!elements.districtHiddenInput,
            fullAddressInput: !!elements.fullAddressInput,
        });
    }
    
    function detectMode() {
        log('Detecting mode from VISIBLE containers...');
        
        // Check for visible containers with data-address-mode
        const containers = document.querySelectorAll('[data-address-mode]');
        log('Found containers with data-address-mode:', containers.length);
        
        for (const container of containers) {
            if (isElementVisible(container)) {
                state.mode = container.dataset.addressMode;
                logSuccess(`Mode from visible container: ${state.mode}`);
                return;
            }
        }
        
        // Fallback: Check element existence and visibility
        if (elements.districtSelect && isElementVisible(elements.districtSelect)) {
            state.mode = 'old';
            logSuccess('Mode auto-detected: OLD (visible district-select)');
            return;
        }
        
        if (elements.wardSelect && isElementVisible(elements.wardSelect)) {
            state.mode = 'new';
            logSuccess('Mode auto-detected: NEW (visible ward-select)');
            return;
        }
        
        logError('No visible address elements found');
    }
    
    function isElementVisible(element) {
        if (!element) return false;
        
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' &&
               element.offsetParent !== null;
    }
    
    // ========================================================================
    // DATA LOADING
    // ========================================================================
    
    function loadData() {
        const url = state.mode === 'old' ? CONFIG.OLD_STRUCTURE_URL : CONFIG.NEW_STRUCTURE_URL;
        
        log('Loading data from:', url);
        
        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                state.data = data;
                logSuccess('Data loaded', { mode: state.mode, dataLoaded: Array.isArray(data) ? data.length : Object.keys(data).length });
                
                if (state.mode === 'old') {
                    initOldStructure();
                } else {
                    initNewStructure();
                }

                // Attempt to restore any previously-saved values from hidden inputs
                try {
                    restoreFromHiddenInputs();
                } catch (e) {
                    logError('restoreFromHiddenInputs failed', e);
                }

                state.initialized = true;
                // Mark global to prevent duplicate calls
                if (!window.SmartAddress) window.SmartAddress = {};
                window.SmartAddress._initialized = true;
            })
            .catch(err => {
                logError('Load failed:', err);
                showError('Không thể tải dữ liệu địa chỉ');
            });
    }
    
    // ========================================================================
    // OLD STRUCTURE - From smart_address_hcmc.js v3.4 (PROVEN WORKING)
    // ========================================================================
    
    function initOldStructure() {
        log('Initializing OLD structure (with districts)...');
        
        if (!state.data.district || !Array.isArray(state.data.district)) {
            logError('Invalid OLD structure - no districts');
            return;
        }
        
        populateDistricts();
    }
    
    function populateDistricts() {
        if (!elements.districtSelect) {
            logError('populateDistricts: districtSelect element not found');
            return;
        }
        const districts = state.data.district;
        
        elements.districtSelect.innerHTML = '<option value="">-- Chọn Quận/Huyện --</option>';
        
        districts.forEach((district, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = formatDistrictName(district);
            option.dataset.districtName = district.name;
            elements.districtSelect.appendChild(option);
        });
        
        elements.districtSelect.disabled = false;
        logSuccess(`Populated ${districts.length} districts`);
        
        // Event listener
        if (!elements.districtSelect.dataset.hasListener) {
            elements.districtSelect.addEventListener('change', handleDistrictChange);
            elements.districtSelect.dataset.hasListener = 'true';
        }
    }
    
    function formatDistrictName(district) {
        return district.pre ? `${district.pre} ${district.name}` : district.name;
    }
    
    function handleDistrictChange(e) {
        const index = parseInt(e.target.value);
        
        // Reset
        resetWardAndStreet();
        
        if (isNaN(index)) return;
        
        state.currentDistrictIndex = index;
        state.currentDistrict = state.data.district[index];
        
        log('District selected:', formatDistrictName(state.currentDistrict));
        
        // Update hidden field
        if (elements.districtHiddenInput) {
            elements.districtHiddenInput.value = formatDistrictName(state.currentDistrict);
        }
        
        // Populate wards
        populateWardsFromDistrict();
        
        // Load streets from DISTRICT level (that's the data structure)
        loadStreetsFromDistrict();
    }
    
    function populateWardsFromDistrict() {
        if (!elements.wardSelect) {
            logError('populateWardsFromDistrict: wardSelect element not found');
            return;
        }

        if (!state.currentDistrict || !state.currentDistrict.ward) {
            elements.wardSelect.innerHTML = '<option value="">-- Không có dữ liệu --</option>';
            elements.wardSelect.disabled = true;
            return;
        }
        
        const wards = state.currentDistrict.ward;
        
        elements.wardSelect.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
        
        wards.forEach((ward, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = formatWardName(ward);
            elements.wardSelect.appendChild(option);
        });
        
        elements.wardSelect.disabled = false;
        logSuccess(`Populated ${wards.length} wards`);
        
        // Event listener
        if (!elements.wardSelect.dataset.hasListener) {
            elements.wardSelect.addEventListener('change', handleWardChangeOld);
            elements.wardSelect.dataset.hasListener = 'true';
        }
    }
    
    function formatWardName(ward) {
        return ward.pre ? `${ward.pre} ${ward.name}` : ward.name;
    }
    
    function handleWardChangeOld(e) {
        const index = parseInt(e.target.value);
        
        if (isNaN(index) || !state.currentDistrict) {
            state.currentWard = null;
            if (elements.wardHiddenInput) elements.wardHiddenInput.value = '';
            updateAddressPreview();
            return;
        }
        
        state.currentWardIndex = index;
        state.currentWard = state.currentDistrict.ward[index];
        
        log('Ward selected:', formatWardName(state.currentWard));
        
        // Update hidden field
        if (elements.wardHiddenInput) {
            elements.wardHiddenInput.value = formatWardName(state.currentWard);
        }
        
        updateAddressPreview();
    }
    
    function loadStreetsFromDistrict() {
        state.availableStreets = [];
        
        if (!state.currentDistrict) return;
        
        // Streets are at DISTRICT level in SG.json
        if (state.currentDistrict.street && Array.isArray(state.currentDistrict.street)) {
            // Convert string array to objects
            state.availableStreets = state.currentDistrict.street.map(name => ({ name }));
            
            logSuccess(`Loaded ${state.availableStreets.length} streets for district`);
        }
        
        setupStreetAutocomplete();
    }
    
    // ========================================================================
    // NEW STRUCTURE - Direct Wards (No Districts)
    // ========================================================================
    
    function initNewStructure() {
        log('Initializing NEW structure (direct wards)...');
        
        // Find HCMC data
        let hcmcData = state.data;
        
        // If array, find HCMC
        if (Array.isArray(state.data)) {
            hcmcData = state.data.find(p => p.Code === '79');
            if (!hcmcData) {
                logError('HCMC not found');
                return;
            }
        }
        
        if (!hcmcData.Wards || !Array.isArray(hcmcData.Wards)) {
            logError('No Wards array');
            return;
        }
        
        state.data = hcmcData;
        populateWardsDirectly();
    }
    
    function populateWardsDirectly() {
        const wards = state.data.Wards;
        
        // Sort alphabetically
        const sorted = [...wards].sort((a, b) => {
            const nameA = a.FullName || a.Name;
            const nameB = b.FullName || b.Name;
            return nameA.localeCompare(nameB, 'vi');
        });
        
        elements.wardSelect.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
        
        sorted.forEach((ward, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = ward.FullName || ward.Name;
            elements.wardSelect.appendChild(option);
        });
        
        elements.wardSelect.disabled = false;
        logSuccess(`Populated ${wards.length} wards (NEW)`);
        
        // Event listener
        if (!elements.wardSelect.dataset.hasListener) {
            elements.wardSelect.addEventListener('change', handleWardChangeNew);
            elements.wardSelect.dataset.hasListener = 'true';
        }
    }
    
    function handleWardChangeNew(e) {
        const index = parseInt(e.target.value);
        
        if (isNaN(index)) {
            state.currentWard = null;
            if (elements.wardHiddenInput) elements.wardHiddenInput.value = '';
            updateAddressPreview();
            return;
        }
        
        // Get sorted wards
        const wards = state.data.Wards;
        const sorted = [...wards].sort((a, b) => {
            const nameA = a.FullName || a.Name;
            const nameB = b.FullName || b.Name;
            return nameA.localeCompare(nameB, 'vi');
        });
        
        state.currentWard = sorted[index];
        log('Ward selected:', state.currentWard.FullName || state.currentWard.Name);
        
        // Update hidden field
        if (elements.wardHiddenInput) {
            elements.wardHiddenInput.value = state.currentWard.FullName || state.currentWard.Name;
        }
        
        updateAddressPreview();
    }
    
    // ========================================================================
    // STREET AUTOCOMPLETE - Common for both modes
    // ========================================================================
    
    function setupStreetAutocomplete() {
        if (!elements.streetInput || elements.streetInput.dataset.hasListener) return;
        
        elements.streetInput.addEventListener('input', handleStreetInput);
        elements.streetInput.addEventListener('keydown', handleStreetKeyboard);
        elements.streetInput.dataset.hasListener = 'true';
        
        // Close on outside click
        document.addEventListener('click', (e) => {
            if (e.target !== elements.streetInput && 
                !elements.streetSuggestions?.contains(e.target)) {
                hideStreetSuggestions();
            }
        });
    }
    
    function handleStreetInput(e) {
        const query = e.target.value.trim();
        
        state.selectedStreetIndex = -1;
        
        if (state.mode === 'old' && !state.currentDistrict) {
            if (query.length > 0) {
                showStreetMessage('Vui lòng chọn Quận/Huyện trước');
            }
            return;
        }
        
        if (query.length < CONFIG.MIN_SEARCH_LENGTH) {
            hideStreetSuggestions();
            return;
        }
        
        if (state.availableStreets.length === 0) {
            if (query.length > 0) {
                showStreetMessage('Không có dữ liệu tên đường');
            }
            return;
        }
        
        const filtered = filterStreets(query);
        
        if (filtered.length === 0) {
            showStreetMessage(`Không tìm thấy "${query}"`);
            return;
        }
        
        showStreetSuggestions(filtered.slice(0, CONFIG.MAX_SUGGESTIONS), query);
    }
    
    function filterStreets(query) {
        const normalized = normalizeVietnamese(query);
        
        const startsWithMatches = [];
        const containsMatches = [];
        
        state.availableStreets.forEach(street => {
            const streetNormalized = normalizeVietnamese(street.name);
            
            if (!streetNormalized.includes(normalized)) return;
            
            if (streetNormalized.startsWith(normalized)) {
                startsWithMatches.push(street);
            } else {
                containsMatches.push(street);
            }
        });
        
        return [...startsWithMatches, ...containsMatches];
    }
    
    function normalizeVietnamese(text) {
        if (!text) return '';
        return text.toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/đ/g, 'd');
    }
    
    function showStreetSuggestions(streets, query) {
        if (!elements.streetSuggestions) return;
        
        elements.streetSuggestions.innerHTML = '';
        
        streets.forEach(street => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = highlightMatch(street.name, query);
            
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Set value
                elements.streetInput.value = street.name;
                hideStreetSuggestions();
                
                //  FIX: Use jQuery trigger if available (more reliable)
                if (typeof jQuery !== 'undefined') {
                    $(elements.streetInput).trigger('change').trigger('input');
                } else {
                    // Fallback to vanilla JS
                    const changeEvent = new Event('change', { bubbles: true });
                    const inputEvent = new Event('input', { bubbles: true });
                    elements.streetInput.dispatchEvent(changeEvent);
                    elements.streetInput.dispatchEvent(inputEvent);
                }
                
                // Also manually call updateAddressPreview if it exists
                if (typeof updateAddressPreview === 'function') {
                    updateAddressPreview();
                }
                
                log('Street selected:', street.name);
            });
            
            elements.streetSuggestions.appendChild(item);
        });
        
        elements.streetSuggestions.style.display = 'block';
    }

    
    function highlightMatch(text, query) {
        if (!query) return escapeHtml(text);
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return escapeHtml(text).replace(regex, '<strong class="text-primary">$1</strong>');
    }
    
    function handleStreetKeyboard(e) {
        const suggestions = elements.streetSuggestions?.querySelectorAll('.list-group-item');
        if (!suggestions || suggestions.length === 0) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                state.selectedStreetIndex = Math.min(state.selectedStreetIndex + 1, suggestions.length - 1);
                highlightSuggestion(suggestions);
                break;
            case 'ArrowUp':
                e.preventDefault();
                state.selectedStreetIndex = Math.max(state.selectedStreetIndex - 1, -1);
                highlightSuggestion(suggestions);
                break;
            case 'Enter':
                e.preventDefault();
                if (state.selectedStreetIndex >= 0) {
                    suggestions[state.selectedStreetIndex].click();
                }
                break;
            case 'Escape':
                hideStreetSuggestions();
                break;
        }
    }
    
    function highlightSuggestion(suggestions) {
        suggestions.forEach((item, index) => {
            if (index === state.selectedStreetIndex) {
                item.classList.add('active');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    function showStreetMessage(msg) {
        if (!elements.streetSuggestions) return;
        elements.streetSuggestions.innerHTML = 
            `<div class="list-group-item text-muted small">${escapeHtml(msg)}</div>`;
        elements.streetSuggestions.style.display = 'block';
    }
    
    function hideStreetSuggestions() {
        if (elements.streetSuggestions) {
            elements.streetSuggestions.style.display = 'none';
        }
        state.selectedStreetIndex = -1;
    }
    
    // ========================================================================
    // ADDRESS PREVIEW
    // ========================================================================
    
    function updateAddressPreview() {
        if (!elements.addressPreview || !elements.addressPreviewText) return;
        
        const parts = [];
        
        // House details
        if (elements.fullAddressInput) {
            const val = elements.fullAddressInput.value?.trim();
            if (val) parts.push(val);
        }
        
        // Street
        if (elements.streetInput) {
            const val = elements.streetInput.value?.trim();
            if (val) parts.push(val);
        }
        
        // Ward
        if (state.currentWard) {
            if (state.mode === 'old') {
                parts.push(formatWardName(state.currentWard));
            } else {
                parts.push(state.currentWard.FullName || state.currentWard.Name);
            }
        }
        
        // District (OLD only)
        if (state.mode === 'old' && state.currentDistrict) {
            parts.push(formatDistrictName(state.currentDistrict));
        }
        
        // City
        parts.push('TP. Hồ Chí Minh');
        
        // Update display
        if (parts.length > 1) {
            elements.addressPreviewText.textContent = parts.join(', ');
            elements.addressPreview.style.display = 'block';
        } else {
            elements.addressPreview.style.display = 'none';
        }
    }
    
    // ========================================================================
    // UTILITIES
    // ========================================================================

    /**
     * Attempt to restore selected district/ward from hidden inputs saved by the server/template.
     * This is defensive: it will not throw if elements are missing and will avoid repeated restores.
     */
    function restoreFromHiddenInputs() {
        try {
            log('Attempting restore from hidden inputs', {
                wardHidden: elements.wardHiddenInput?.value,
                districtHidden: elements.districtHiddenInput?.value,
                fullAddress: elements.fullAddressInput?.value
            });

            // NEW mode: match ward by visible option text
            if (state.mode === 'new') {
                const targetWard = elements.wardHiddenInput?.value?.trim();
                if (targetWard && elements.wardSelect) {
                    const opts = Array.from(elements.wardSelect.options);
                    let idx = opts.findIndex(o => (o.textContent || '').trim() === targetWard);
                    if (idx === -1) idx = opts.findIndex(o => (o.textContent || '').includes(targetWard));
                    if (idx > 0) {
                        elements.wardSelect.value = opts[idx].value;
                        if (!elements.wardSelect.dataset.restored) {
                            elements.wardSelect.dataset.restored = 'true';
                            setTimeout(() => elements.wardSelect.dispatchEvent(new Event('change', { bubbles: true })), 50);
                        }
                        log('Restored NEW ward to option index', idx);
                    } else {
                        log('No matching NEW ward option found for', targetWard);
                    }
                }
                return;
            }

            // OLD mode: restore district then ward
            if (state.mode === 'old') {
                const targetDistrict = elements.districtHiddenInput?.value?.trim();
                const targetWard = elements.wardHiddenInput?.value?.trim();

                if (targetDistrict && elements.districtSelect) {
                    const opts = Array.from(elements.districtSelect.options);
                    let didx = opts.findIndex(o => ((o.dataset.districtName || o.textContent) || '').trim() === targetDistrict);
                    if (didx === -1) didx = opts.findIndex(o => (o.textContent || '').includes(targetDistrict));
                    if (didx > 0) {
                        elements.districtSelect.value = opts[didx].value;
                        if (!elements.districtSelect.dataset.restored) {
                            elements.districtSelect.dataset.restored = 'true';
                            // trigger change to populate wards
                            setTimeout(() => elements.districtSelect.dispatchEvent(new Event('change', { bubbles: true })), 50);
                        }
                        log('Restored OLD district to option index', didx);

                        // After wards populated, try restore ward
                        setTimeout(() => {
                            if (targetWard && elements.wardSelect) {
                                const wopts = Array.from(elements.wardSelect.options);
                                let widx = wopts.findIndex(o => (o.textContent || '').trim() === targetWard);
                                if (widx === -1) widx = wopts.findIndex(o => (o.textContent || '').includes(targetWard));
                                if (widx > 0) {
                                    elements.wardSelect.value = wopts[widx].value;
                                    if (!elements.wardSelect.dataset.restored) {
                                        elements.wardSelect.dataset.restored = 'true';
                                        elements.wardSelect.dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                    log('Restored OLD ward to option index', widx);
                                } else {
                                    log('No matching OLD ward option found for', targetWard);
                                }
                            }
                        }, 150);
                    } else {
                        log('No matching district option found for', targetDistrict);
                    }
                }
            }
        } catch (e) {
            logError('restoreFromHiddenInputs exception', e);
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    function escapeRegex(text) {
        return (text || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    function resetWardAndStreet() {
        state.currentWard = null;
        state.currentWardIndex = null;
        state.availableStreets = [];
        state.selectedStreetIndex = -1;
        
        if (elements.wardSelect) {
            elements.wardSelect.innerHTML = '<option value="">-- Chọn Quận/Huyện trước --</option>';
            elements.wardSelect.disabled = true;
        }
        
        if (elements.streetInput) {
            elements.streetInput.value = '';
        }
        
        if (elements.wardHiddenInput) {
            elements.wardHiddenInput.value = '';
        }
        
        hideStreetSuggestions();
        updateAddressPreview();
    }
    
    function showError(msg) {
        alert(msg);
    }
    
    // ========================================================================
    // RE-INITIALIZATION (for mode switching)
    // ========================================================================
    
    function reinitialize() {
        log('Re-initializing...');
        
        // Reset state
        state.mode = null;
        state.data = null;
        state.currentDistrict = null;
        state.currentDistrictIndex = null;
        state.currentWard = null;
        state.currentWardIndex = null;
        state.availableStreets = [];
        state.initialized = false;
        
        // Re-run init
        init();
    }
    
    // ========================================================================
    // AUTO-INIT
    // ========================================================================
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Setup preview listeners
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (elements.fullAddressInput) {
                elements.fullAddressInput.addEventListener('input', updateAddressPreview);
            }
        });
    } else {
        if (elements.fullAddressInput) {
            elements.fullAddressInput.addEventListener('input', updateAddressPreview);
        }
    }
    
    // Expose API
    window.SmartAddress = {
        init: init,
        reinitialize: reinitialize,
        setMode: function(mode) {
            state.mode = mode;
            loadData();
        }
    };
    
    log('Script loaded v5.0');
    
})();