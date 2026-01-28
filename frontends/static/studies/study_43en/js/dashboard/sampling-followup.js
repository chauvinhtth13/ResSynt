/**
 * Sampling Follow-up Statistics (Patient & Contact)
 * ==================================================
 * 
 * Table: Patient and Contact sampling by visit schedule
 * 
 * Features:
 * - Simple 3-column layout: Schedule, Patient, Contact
 * - Site filter integration with global site selector
 * - Day 1, 10, 28, 90 timepoints
 * 
 * Version: 2.0 - Simplified and integrated with site-selector
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/sampling-followup/',
        CURRENT_SITE: 'all',
    };

    // ========================================================================
    // DOM ELEMENTS
    // ========================================================================

    const DOM = {
        tableContainer: () => document.getElementById('samplingTableContainer'),
        tableBody: () => document.getElementById('samplingTableBody'),
        loading: () => document.getElementById('samplingLoading'),
    };

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        initSiteSelector();
        loadSamplingData();
    });

    // ========================================================================
    // SITE SELECTOR INTEGRATION
    // ========================================================================

    /**
     * Initialize site selector listener (uses global site-selector.js)
     */
    function initSiteSelector() {
        // Listen for site change events from global site selector
        document.addEventListener('siteChanged', function (e) {
            CONFIG.CURRENT_SITE = e.detail.site || 'all';
            loadSamplingData();
        });

        // Get initial site from hidden input
        const siteInput = document.getElementById('selectedSiteInput');
        if (siteInput) {
            CONFIG.CURRENT_SITE = siteInput.value || 'all';
        }
    }

    // ========================================================================
    // DATA LOADING
    // ========================================================================

    /**
     * Load sampling follow-up statistics data
     */
    function loadSamplingData() {
        const loading = DOM.loading();
        const container = DOM.tableContainer();

        // Show loading
        if (loading) loading.style.display = 'flex';

        // Build API URL
        const params = new URLSearchParams({
            site: CONFIG.CURRENT_SITE,
        });

        const url = `${CONFIG.API_ENDPOINT}?${params.toString()}`;

        // Fetch data
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                if (!result.success) {
                    throw new Error(result.error || 'Unknown error');
                }

                // Hide loading
                if (loading) loading.style.display = 'none';

                // Render table
                renderSamplingTable(result.data);
            })
            .catch(error => {
                console.error('Sampling data error:', error);
                if (loading) loading.style.display = 'none';
                renderError(error.message);
            });
    }

    // ========================================================================
    // TABLE RENDERING
    // ========================================================================

    /**
     * Render sampling follow-up table with simple 3-column layout
     */
    function renderSamplingTable(data) {
        const tbody = DOM.tableBody();
        if (!tbody) return;

        // Clear existing rows
        tbody.innerHTML = '';

        // Define schedule rows
        const schedules = [
            { key: 'visit1', label: 'Day 1' },
            { key: 'visit2', label: 'Day 10' },
            { key: 'visit3', label: 'Day 28' },
            { key: 'visit4', label: 'Day 90' },
        ];

        // Render each row
        schedules.forEach(schedule => {
            const tr = document.createElement('tr');

            // Schedule label
            const labelCell = document.createElement('td');
            labelCell.className = 'fw-bold';
            labelCell.textContent = schedule.label;
            tr.appendChild(labelCell);

            // Patient count
            const patientCell = document.createElement('td');
            patientCell.className = 'text-center';
            const patientVal = data?.patient?.[schedule.key]?.total;
            patientCell.textContent = patientVal !== undefined && patientVal !== null ? patientVal : '-';
            tr.appendChild(patientCell);

            // Contact count
            const contactCell = document.createElement('td');
            contactCell.className = 'text-center';
            const contactVal = data?.contact?.[schedule.key]?.total;
            contactCell.textContent = contactVal !== undefined && contactVal !== null ? contactVal : '-';
            tr.appendChild(contactCell);

            tbody.appendChild(tr);
        });
    }

    /**
     * Render error message
     */
    function renderError(message) {
        const tbody = DOM.tableBody();
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    ${escapeHtml(message)}
                </td>
            </tr>
        `;
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