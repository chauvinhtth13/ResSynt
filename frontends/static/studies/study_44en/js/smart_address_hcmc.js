/**
 * Smart Address Selection for Study 44EN - HCMC
 * ==============================================
 * 
 * Data source: thien0291/vietnam_dataset (SG.json)
 * Structure: district[] → ward[], district[] → street[] (streets at DISTRICT level)
 * 
 * Features:
 * - Cascading District → Ward dropdowns
 * - Street autocomplete from DISTRICT level (not ward)
 * - Smart search with Vietnamese accent normalization
 * - Prioritize "starts-with" matches over "contains"
 * - Real-time address preview
 * - Keyboard navigation support
 * 
 * @version 3.4
 * @author Claude
 * @date 2026-01-14
 */

(function() {
    'use strict';
    
    // ========================================================================
    // CONFIGURATION
    // ========================================================================
    
    const CONFIG = {
        // Data source (thien0291/vietnam_dataset)
        DATA_URL: '/static/SG.json',
        
        // Fallback to local file if CDN fails
        FALLBACK_URL: '/static/SG.json',
        
        // Element IDs
        DISTRICT_SELECT_ID: 'district-select',
        WARD_SELECT_ID: 'ward-select',
        STREET_INPUT_ID: 'street-autocomplete',
        STREET_SUGGESTIONS_ID: 'street-suggestions',
        FULL_ADDRESS_INPUT_ID: 'full-address-input',
        WARD_HIDDEN_INPUT_ID: 'ward-hidden-input',
        ADDRESS_PREVIEW_ID: 'address-preview',
        ADDRESS_PREVIEW_TEXT_ID: 'address-preview-text',
        
        // Autocomplete settings
        MIN_SEARCH_LENGTH: 1,
        MAX_SUGGESTIONS: 20,
        
        // Debug mode
        DEBUG: true
    };
    
    // ========================================================================
    // STATE MANAGEMENT
    // ========================================================================
    
    const state = {
        hcmcData: null,
        currentDistrict: null,
        currentDistrictIndex: null,
        currentWard: null,
        currentWardIndex: null,
        availableStreets: [],
        selectedStreetIndex: -1
    };
    
    // ========================================================================
    // DOM ELEMENTS CACHE
    // ========================================================================
    
    const elements = {
        districtSelect: null,
        wardSelect: null,
        streetInput: null,
        streetSuggestions: null,
        fullAddressInput: null,
        wardHiddenInput: null,
        addressPreview: null,
        addressPreviewText: null
    };
    
    // ========================================================================
    // LOGGING UTILITY
    // ========================================================================
    
    function log(message, ...args) {
        if (CONFIG.DEBUG) {
            console.log(`[SmartAddress] ${message}`, ...args);
        }
    }
    
    function logError(message, ...args) {
        console.error(`[SmartAddress] ✗ ${message}`, ...args);
    }
    
    function logSuccess(message, ...args) {
        if (CONFIG.DEBUG) {
            console.log(`[SmartAddress] ✓ ${message}`, ...args);
        }
    }
    
    // ========================================================================
    // INITIALIZATION
    // ========================================================================
    
    function init() {
        log('Initializing v3.4 (District-level streets with smart search)...');
        
        // Cache DOM elements
        cacheElements();
        
        // Verify required elements exist
        if (!verifyElements()) {
            logError('Required DOM elements not found!');
            return;
        }
        
        // Load HCMC data
        loadHCMCData();
    }
    
    function cacheElements() {
        elements.districtSelect = document.getElementById(CONFIG.DISTRICT_SELECT_ID);
        elements.wardSelect = document.getElementById(CONFIG.WARD_SELECT_ID);
        elements.streetInput = document.getElementById(CONFIG.STREET_INPUT_ID);
        elements.streetSuggestions = document.getElementById(CONFIG.STREET_SUGGESTIONS_ID);
        elements.fullAddressInput = document.getElementById(CONFIG.FULL_ADDRESS_INPUT_ID);
        elements.wardHiddenInput = document.getElementById(CONFIG.WARD_HIDDEN_INPUT_ID);
        elements.addressPreview = document.getElementById(CONFIG.ADDRESS_PREVIEW_ID);
        elements.addressPreviewText = document.getElementById(CONFIG.ADDRESS_PREVIEW_TEXT_ID);
    }
    
    function verifyElements() {
        const required = ['districtSelect', 'wardSelect'];
        return required.every(key => elements[key] !== null);
    }
    
    // ========================================================================
    // DATA LOADING
    // ========================================================================
    
    function loadHCMCData() {
        log('Loading data from:', CONFIG.DATA_URL);
        
        // Show loading state
        setDistrictLoading(true);
        
        // Try CDN first, fallback to local
        fetchWithFallback(CONFIG.DATA_URL, CONFIG.FALLBACK_URL)
            .then(data => {
                logSuccess('Data loaded successfully');
                log('Structure:', {
                    name: data.name,
                    code: data.code,
                    districts: data.district ? data.district.length : 0
                });
                
                // Validate data structure
                if (!validateDataStructure(data)) {
                    throw new Error('Invalid data structure');
                }
                
                state.hcmcData = data;
                populateDistricts();
            })
            .catch(error => {
                logError('Failed to load data:', error);
                showError('Không thể tải dữ liệu địa chỉ. Vui lòng kiểm tra kết nối mạng hoặc liên hệ admin.');
            });
    }
    
    function fetchWithFallback(primaryUrl, fallbackUrl) {
        return fetch(primaryUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                log('CDN failed, trying fallback:', fallbackUrl);
                return fetch(fallbackUrl).then(response => {
                    if (!response.ok) {
                        throw new Error('Both CDN and local file failed');
                    }
                    return response.json();
                });
            });
    }
    
    function validateDataStructure(data) {
        if (!data || !data.district || !Array.isArray(data.district)) {
            logError('Missing or invalid "district" array');
            return false;
        }
        
        // Check first district has wards
        if (data.district.length > 0) {
            const firstDistrict = data.district[0];
            if (!firstDistrict.ward || !Array.isArray(firstDistrict.ward)) {
                logError('District missing "ward" array');
                return false;
            }
            
            // Check first ward has streets
            if (firstDistrict.ward.length > 0) {
                const firstWard = firstDistrict.ward[0];
                if (!firstWard.street || !Array.isArray(firstWard.street)) {
                    log('Warning: Ward missing "street" array (may be empty)');
                }
            }
        }
        
        return true;
    }
    
    // ========================================================================
    // POPULATE DISTRICTS
    // ========================================================================
    
    function populateDistricts() {
        const districts = state.hcmcData.district;
        
        // Clear and populate
        elements.districtSelect.innerHTML = '<option value="">-- Chọn Quận/Huyện --</option>';
        
        districts.forEach((district, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = formatDistrictName(district);
            option.dataset.districtName = district.name;
            option.dataset.districtPre = district.pre || '';
            elements.districtSelect.appendChild(option);
        });
        
        setDistrictLoading(false);
        
        logSuccess(`Populated ${districts.length} districts`);
        
        // Attach event listener
        elements.districtSelect.addEventListener('change', handleDistrictChange);
    }
    
    function formatDistrictName(district) {
        return district.pre ? `${district.pre} ${district.name}` : district.name;
    }
    
    function setDistrictLoading(isLoading) {
        if (isLoading) {
            elements.districtSelect.innerHTML = '<option value="">-- Đang tải... --</option>';
            elements.districtSelect.disabled = true;
        } else {
            elements.districtSelect.disabled = false;
        }
    }
    
    // ========================================================================
    // HANDLE DISTRICT CHANGE
    // ========================================================================
    
    function handleDistrictChange(event) {
        const selectedIndex = event.target.value;
        
        // Reset state
        resetState();
        
        if (!selectedIndex) {
            return;
        }
        
        // Update state
        state.currentDistrictIndex = parseInt(selectedIndex);
        state.currentDistrict = state.hcmcData.district[state.currentDistrictIndex];
        
        log('District selected:', formatDistrictName(state.currentDistrict));
        log('Available wards:', state.currentDistrict.ward ? state.currentDistrict.ward.length : 0);
        
        // Load streets from DISTRICT level (not ward - that's the data structure)
        loadStreetsFromDistrict();
        
        // Populate wards
        populateWards();
    }
    
    function resetState() {
        state.currentDistrict = null;
        state.currentDistrictIndex = null;
        state.currentWard = null;
        state.currentWardIndex = null;
        state.availableStreets = [];
        state.selectedStreetIndex = -1;
        
        resetWards();
        resetStreets();
        clearWardHiddenField();
        updateAddressPreview();
    }
    
    // ========================================================================
    // POPULATE WARDS
    // ========================================================================
    
    function populateWards() {
        if (!state.currentDistrict || !state.currentDistrict.ward) {
            log('No wards available for district');
            elements.wardSelect.innerHTML = '<option value="">-- Không có dữ liệu Phường/Xã --</option>';
            elements.wardSelect.disabled = true;
            return;
        }
        
        const wards = state.currentDistrict.ward;
        
        elements.wardSelect.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
        
        wards.forEach((ward, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = formatWardName(ward);
            option.dataset.wardName = ward.name;
            option.dataset.wardPre = ward.pre || '';
            elements.wardSelect.appendChild(option);
        });
        
        elements.wardSelect.disabled = false;
        
        logSuccess(`Populated ${wards.length} wards`);
        
        // Attach event listener (only once)
        if (!elements.wardSelect.dataset.hasListener) {
            elements.wardSelect.addEventListener('change', handleWardChange);
            elements.wardSelect.dataset.hasListener = 'true';
        }
    }
    
    function formatWardName(ward) {
        return ward.pre ? `${ward.pre} ${ward.name}` : ward.name;
    }
    
    function resetWards() {
        elements.wardSelect.innerHTML = '<option value="">-- Chọn Quận/Huyện trước --</option>';
        elements.wardSelect.disabled = true;
    }
    
    // ========================================================================
    // HANDLE WARD CHANGE
    // ========================================================================
    
    function handleWardChange(event) {
        const selectedIndex = event.target.value;
        
        // Reset ward state only (keep streets - they're from district)
        state.currentWard = null;
        state.currentWardIndex = null;
        state.selectedStreetIndex = -1;
        
        // Don't reset streets - they're loaded from district, not ward!
        clearWardHiddenField();
        
        if (!selectedIndex || !state.currentDistrict) {
            updateAddressPreview();
            return;
        }
        
        // Update state
        state.currentWardIndex = parseInt(selectedIndex);
        state.currentWard = state.currentDistrict.ward[state.currentWardIndex];
        
        const wardFullName = formatWardName(state.currentWard);
        
        log('Ward selected:', wardFullName);
        
        // Set hidden field for form submission
        elements.wardHiddenInput.value = wardFullName;
        
        // Streets already loaded from district (data structure has streets at district level)
        // Just update address preview
        updateAddressPreview();
    }
    
    function clearWardHiddenField() {
        if (elements.wardHiddenInput) {
            elements.wardHiddenInput.value = '';
        }
    }
    
    // ========================================================================
    // LOAD STREETS FROM DISTRICT (NOT WARD - that's the data structure)
    // ========================================================================
    
    function loadStreetsFromDistrict() {
        state.availableStreets = [];
        
        if (!state.currentDistrict) {
            log('No district selected');
            return;
        }
        
        // Streets are stored as string array at DISTRICT level (not ward!)
        if (state.currentDistrict.street && Array.isArray(state.currentDistrict.street)) {
            // Convert string array to object array for consistent handling
            state.availableStreets = state.currentDistrict.street.map(streetName => ({
                name: streetName,
                pre: '' // No prefix in dataset
            }));
            
            logSuccess(`Loaded ${state.availableStreets.length} streets for district: ${state.currentDistrict.name}`);
        } else {
            log(`No streets available for district: ${state.currentDistrict.name}`);
        }
        
        // Setup street input listeners (only once)
        setupStreetInputListeners();
    }
    
    function setupStreetInputListeners() {
        if (!elements.streetInput || elements.streetInput.dataset.hasListener) {
            return;
        }
        
        elements.streetInput.addEventListener('input', handleStreetInput);
        elements.streetInput.addEventListener('focus', handleStreetInput);
        elements.streetInput.addEventListener('keydown', handleStreetKeyboard);
        elements.streetInput.dataset.hasListener = 'true';
        
        // Close suggestions on outside click
        document.addEventListener('click', (e) => {
            if (e.target !== elements.streetInput && 
                !elements.streetSuggestions.contains(e.target)) {
                hideStreetSuggestions();
            }
        });
        
        log('Street input listeners attached');
    }
    
    // ========================================================================
    // HANDLE STREET INPUT (AUTOCOMPLETE)
    // ========================================================================
    
    function handleStreetInput(event) {
        const query = event.target.value.trim();
        
        // Reset selection index
        state.selectedStreetIndex = -1;
        
        // Must select district first (streets are at district level)
        if (!state.currentDistrict) {
            showStreetMessage('Vui lòng chọn Quận/Huyện trước');
            return;
        }
        
        // Check if streets available
        if (state.availableStreets.length === 0) {
            if (query.length > 0) {
                showStreetMessage('Không có dữ liệu tên đường cho quận/huyện này');
            } else {
                hideStreetSuggestions();
            }
            return;
        }
        
        // Minimum length check
        if (query.length < CONFIG.MIN_SEARCH_LENGTH) {
            hideStreetSuggestions();
            return;
        }
        
        // Filter streets
        const filtered = filterStreets(query);
        
        if (filtered.length === 0) {
            showStreetMessage(`Không tìm thấy đường phù hợp với "${query}"`);
            return;
        }
        
        // Show suggestions
        showStreetSuggestions(filtered.slice(0, CONFIG.MAX_SUGGESTIONS), query);
    }
    
    // ========================================================================
    // KEYBOARD NAVIGATION
    // ========================================================================
    
    function handleStreetKeyboard(event) {
        const suggestions = elements.streetSuggestions.querySelectorAll('.list-group-item');
        
        if (suggestions.length === 0) {
            return;
        }
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                state.selectedStreetIndex = Math.min(
                    state.selectedStreetIndex + 1, 
                    suggestions.length - 1
                );
                highlightSuggestion(suggestions);
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                state.selectedStreetIndex = Math.max(
                    state.selectedStreetIndex - 1, 
                    -1
                );
                highlightSuggestion(suggestions);
                break;
                
            case 'Enter':
                event.preventDefault();
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
    
    // ========================================================================
    // FILTER STREETS WITH SMART SEARCH
    // ========================================================================
    
    function filterStreets(query) {
        const lowerQuery = query.toLowerCase();
        const normalizedQuery = normalizeVietnamese(query);
        
        const startsWithMatches = [];
        const containsMatches = [];
        
        state.availableStreets.forEach(street => {
            const streetName = street.name.toLowerCase();
            const normalizedStreet = normalizeVietnamese(street.name);
            
            // Check if matches
            const matchesExact = streetName.includes(lowerQuery);
            const matchesNormalized = normalizedStreet.includes(normalizedQuery);
            
            if (!matchesExact && !matchesNormalized) {
                return; // No match
            }
            
            // Prioritize: starts with query
            const startsWithExact = streetName.startsWith(lowerQuery);
            const startsWithNormalized = normalizedStreet.startsWith(normalizedQuery);
            
            if (startsWithExact || startsWithNormalized) {
                startsWithMatches.push(street);
            } else {
                containsMatches.push(street);
            }
        });
        
        // Return startsWith first, then contains
        return [...startsWithMatches, ...containsMatches];
    }
    
    // ========================================================================
    // NORMALIZE VIETNAMESE TEXT (REMOVE ACCENTS)
    // ========================================================================
    
    function normalizeVietnamese(text) {
        if (!text) return '';
        
        return text
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
            .replace(/đ/g, 'd')
            .replace(/Đ/g, 'd');
    }
    
    // ========================================================================
    // SHOW STREET SUGGESTIONS
    // ========================================================================
    
    function showStreetSuggestions(streets, query) {
        if (!elements.streetSuggestions) return;
        
        elements.streetSuggestions.innerHTML = '';
        
        streets.forEach((street, index) => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.dataset.streetIndex = index;
            
            const streetFullName = street.name;
            item.innerHTML = highlightMatch(streetFullName, query);
            
            item.addEventListener('click', (e) => {
                e.preventDefault();
                selectStreet(street);
            });
            
            elements.streetSuggestions.appendChild(item);
        });
        
        elements.streetSuggestions.style.display = 'block';
        log(`Showing ${streets.length} street suggestions`);
    }
    
    function highlightMatch(text, query) {
        if (!query) return escapeHtml(text);
        
        const escapedText = escapeHtml(text);
        const escapedQuery = escapeRegex(query);
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        
        return escapedText.replace(regex, '<strong class="text-primary">$1</strong>');
    }
    
    // ========================================================================
    // SELECT STREET
    // ========================================================================
    
    function selectStreet(street) {
        const streetFullName = street.name;
        
        elements.streetInput.value = streetFullName;
        hideStreetSuggestions();
        
        log('Street selected:', streetFullName);
        
        updateAddressPreview();
    }
    
    // ========================================================================
    // UI HELPERS
    // ========================================================================
    
    function showStreetMessage(message) {
        if (!elements.streetSuggestions) return;
        
        elements.streetSuggestions.innerHTML = 
            `<div class="list-group-item text-muted small">${escapeHtml(message)}</div>`;
        elements.streetSuggestions.style.display = 'block';
    }
    
    function hideStreetSuggestions() {
        if (elements.streetSuggestions) {
            elements.streetSuggestions.style.display = 'none';
        }
        state.selectedStreetIndex = -1;
    }
    
    function resetStreets() {
        if (elements.streetInput) {
            elements.streetInput.value = '';
        }
        hideStreetSuggestions();
    }
    
    function showError(message) {
        elements.districtSelect.innerHTML = '<option value="">-- Lỗi tải dữ liệu --</option>';
        elements.districtSelect.disabled = true;
        
        if (typeof alert !== 'undefined') {
            alert(message);
        }
    }
    
    // ========================================================================
    // ADDRESS PREVIEW
    // ========================================================================
    
    function updateAddressPreview() {
        if (!elements.addressPreview || !elements.addressPreviewText) {
            return;
        }
        
        const parts = [];
        
        // House number/details
        if (elements.fullAddressInput) {
            const houseDetails = elements.fullAddressInput.value.trim();
            if (houseDetails) parts.push(houseDetails);
        }
        
        // Street
        if (elements.streetInput) {
            const street = elements.streetInput.value.trim();
            if (street) parts.push(street);
        }
        
        // Ward
        if (state.currentWard) {
            parts.push(formatWardName(state.currentWard));
        }
        
        // District
        if (state.currentDistrict) {
            parts.push(formatDistrictName(state.currentDistrict));
        }
        
        // City
        parts.push('TP. Hồ Chí Minh');
        
        // Update preview
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
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    function escapeRegex(text) {
        return (text || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // ========================================================================
    // SETUP ADDRESS PREVIEW LISTENERS
    // ========================================================================
    
    function setupPreviewListeners() {
        if (elements.fullAddressInput) {
            elements.fullAddressInput.addEventListener('input', updateAddressPreview);
        }
        if (elements.streetInput) {
            elements.streetInput.addEventListener('change', updateAddressPreview);
        }
    }
    
    // ========================================================================
    // AUTO-INIT
    // ========================================================================
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
            setupPreviewListeners();
        });
    } else {
        init();
        setupPreviewListeners();
    }
    
    log('Script loaded and ready');
    
})();