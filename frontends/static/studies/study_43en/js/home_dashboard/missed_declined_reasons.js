/**
 * Missed/Declined Consent Reasons Statistics - FIXED VERSION
 * ===========================================================
 * 
 * FIX: Properly show/hide table after loading
 * 
 * Features:
 * - Table showing reasons for not participating
 * - Site filter
 * - Separate columns for Patient and Contact
 * 
 * Version: 1.1 (FIXED)
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/missed-declined-reasons/',
        CURRENT_SITE: 'all',
    };

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        console.log('[Missed/Declined] Initializing...');
        
        // Initialize
        initMissedDeclinedSiteFilter();
        loadMissedDeclinedData();
    });

    // ========================================================================
    // SITE FILTER
    // ========================================================================

    /**
     * Initialize site filter dropdown
     */
    function initMissedDeclinedSiteFilter() {
        const filterSelect = document.querySelector('.missed-declined-site-select');

        if (filterSelect) {
            filterSelect.addEventListener('change', function () {
                const site = this.value;
                console.log('[Missed/Declined] Site changed to:', site);

                // Update current site
                CONFIG.CURRENT_SITE = site;

                // Reload data
                loadMissedDeclinedData();
            });
            console.log('[Missed/Declined] Site filter initialized');
        } else {
            console.warn('[Missed/Declined] Site filter not found');
        }
    }

    // ========================================================================
    // DATA LOADING
    // ========================================================================

    /**
     * Load missed/declined reasons data
     */
    function loadMissedDeclinedData() {
        console.log('[Missed/Declined] Loading data for site:', CONFIG.CURRENT_SITE);
        
        const tableBody = document.getElementById('missedDeclinedTableBody');
        const loadingIndicator = document.getElementById('missedDeclinedLoading');
        const tableElement = tableBody ? tableBody.closest('table') : null;

        if (!tableBody) {
            console.error('[Missed/Declined] Table body not found!');
            return;
        }

        // Show loading, hide table
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (tableElement) {
            tableElement.style.display = 'none';
        }

        // Build API URL
        const params = new URLSearchParams({
            site: CONFIG.CURRENT_SITE,
        });

        const url = `${CONFIG.API_ENDPOINT}?${params.toString()}`;
        console.log('[Missed/Declined] Fetching from:', url);

        // Fetch data
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(response => {
                console.log('[Missed/Declined] Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                console.log('[Missed/Declined] Data received:', result);
                
                if (!result.success) {
                    throw new Error(result.error || 'Unknown error');
                }

                // Hide loading, show table
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                if (tableElement) {
                    tableElement.style.display = 'table';  // ✅ FIX: Show table!
                    console.log('[Missed/Declined] Table shown');
                }

                // Render table
                renderMissedDeclinedTable(result.data);
            })
            .catch(error => {
                console.error('[Missed/Declined] Error:', error);
                
                if (loadingIndicator) {
                    loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load missed/declined reasons: ${escapeHtml(error.message)}
                    </div>
                `;
                }
                
                // Hide table on error
                if (tableElement) {
                    tableElement.style.display = 'none';
                }
            });
    }

    // ========================================================================
    // TABLE RENDERING
    // ========================================================================

    /**
     * Render missed/declined reasons table
     */
    function renderMissedDeclinedTable(data) {
        console.log('[Missed/Declined] Rendering table with data:', data);

        const tbody = document.getElementById('missedDeclinedTableBody');
        if (!tbody) {
            console.error('[Missed/Declined] Table body not found for rendering');
            return;
        }

        // Clear existing rows
        tbody.innerHTML = '';

        // Lấy tất cả lý do động từ backend (dạng object: { reason_label: { patient: n, contact: m } })
        // data.reasons: { '2. Infection onset after 48 hours of hospitalization': { patient: 10, contact: 2 }, ... }
        const reasons = data.reasons || {};
        const reasonLabels = Object.keys(reasons);

        reasonLabels.forEach(label => {
            const row = document.createElement('tr');

            // Reason label
            const labelCell = document.createElement('td');
            labelCell.textContent = label;
            row.appendChild(labelCell);

            // Patient count
            const patientCell = document.createElement('td');
            patientCell.className = 'text-center';
            patientCell.textContent = reasons[label].patient || 0;
            row.appendChild(patientCell);

            // Contact count
            const contactCell = document.createElement('td');
            contactCell.className = 'text-center';
            contactCell.textContent = reasons[label].contact || 0;
            row.appendChild(contactCell);

            tbody.appendChild(row);
        });

        // Add total row
        const totalRow = document.createElement('tr');
        totalRow.className = 'table-secondary fw-bold';

        const totalLabelCell = document.createElement('td');
        totalLabelCell.textContent = 'Total';
        totalRow.appendChild(totalLabelCell);

        const totalPatientCell = document.createElement('td');
        totalPatientCell.className = 'text-center';
        totalPatientCell.textContent = data.patient ? (data.patient.total || 0) : 0;
        totalRow.appendChild(totalPatientCell);

        const totalContactCell = document.createElement('td');
        totalContactCell.className = 'text-center';
        totalContactCell.textContent = data.contact ? (data.contact.total || 0) : 0;
        totalRow.appendChild(totalContactCell);

        tbody.appendChild(totalRow);

        console.log('[Missed/Declined] Table rendered with', reasonLabels.length + 1, 'rows');
    }

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

})();