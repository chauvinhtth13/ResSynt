/**
 * K. pneumoniae Isolation Statistics
 * ===================================
 * 
 * Table: K. pneumoniae isolation summary by sample type and site
 * 
 * Features:
 * - 9-column layout: Sample Type | Total (P/C) | HTD (P/C) | CR (P/C) | NHTD (P/C)
 * - Site filter integration with global site selector
 * - Clinical Kp, Throat Swab, Stool/Rectal Swab rows
 * 
 * Version: 2.0 - Simplified and integrated with site-selector
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/kpneumoniae-isolation/',
        CURRENT_SITE: 'all',
    };

    // Site code mapping
    const SITE_CODES = {
        '003': 'htd',
        '011': 'choray',
        '020': 'nhtd',
    };

    // ========================================================================
    // DOM ELEMENTS
    // ========================================================================

    const DOM = {
        tableContainer: () => document.getElementById('kpneumoniaeTableContainer'),
        tableBody: () => document.getElementById('kpneumoniaeTableBody'),
        loading: () => document.getElementById('kpneumoniaeLoading'),
    };

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        initSiteSelector();
        loadKpneumoniaeData();
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
            loadKpneumoniaeData();
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
     * Load K. pneumoniae isolation statistics
     */
    function loadKpneumoniaeData() {
        const loading = DOM.loading();
        const container = DOM.tableContainer();

        // Show loading
        if (loading) loading.style.display = 'flex';

        // Build API URL with site parameter
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
                renderKpneumoniaeTable(result.data);
            })
            .catch(error => {
                console.error('K. pneumoniae data error:', error);
                if (loading) loading.style.display = 'none';
                renderError(error.message);
            });
    }

    // ========================================================================
    // TABLE RENDERING
    // ========================================================================

    /**
     * Render K. pneumoniae isolation table with 9-column layout
     */
    function renderKpneumoniaeTable(data) {
        const tbody = DOM.tableBody();
        if (!tbody) return;

        // Clear existing rows
        tbody.innerHTML = '';

        // Calculate totals from site data
        const sites = ['003', '011', '020']; // HTD, Cho Ray, NHTD
        
        // Sample types to render
        const sampleTypes = [
            { key: 'clinical_kp', label: 'Clinical Kp.', contactNA: true },
            { key: 'throat', label: 'Throat Swab', contactNA: false },
            { key: 'stool_rectal', label: 'Stool/Rectal Swab', contactNA: false },
        ];

        // Calculate and render each sample type row
        sampleTypes.forEach(sampleType => {
            const tr = document.createElement('tr');

            // Sample type label
            const labelCell = document.createElement('td');
            labelCell.className = 'fw-bold';
            labelCell.textContent = sampleType.label;
            tr.appendChild(labelCell);

            // Calculate totals
            let totalPatient = 0;
            let totalContact = 0;
            const siteValues = {};

            sites.forEach(siteCode => {
                const siteData = data?.[siteCode];
                if (siteData) {
                    let patientVal = 0;
                    let contactVal = 0;

                    if (sampleType.key === 'clinical_kp') {
                        patientVal = siteData.patient?.clinical_kp || 0;
                        contactVal = 0; // Clinical Kp not applicable to contacts
                    } else if (sampleType.key === 'throat') {
                        patientVal = getSampleTotal(siteData.patient?.throat);
                        contactVal = getSampleTotal(siteData.contact?.throat);
                    } else if (sampleType.key === 'stool_rectal') {
                        patientVal = getSampleTotal(siteData.patient?.stool_rectal);
                        contactVal = getSampleTotal(siteData.contact?.stool_rectal);
                    }

                    totalPatient += patientVal;
                    totalContact += contactVal;
                    siteValues[siteCode] = { patient: patientVal, contact: contactVal };
                }
            });

            // Total columns (Patient, Contact)
            const totalPCell = document.createElement('td');
            totalPCell.className = 'text-center fw-bold';
            totalPCell.textContent = totalPatient || '-';
            tr.appendChild(totalPCell);

            const totalCCell = document.createElement('td');
            totalCCell.className = 'text-center fw-bold';
            totalCCell.textContent = sampleType.contactNA ? '-' : (totalContact || '-');
            tr.appendChild(totalCCell);

            // Site columns (HTD, Cho Ray, NHTD)
            sites.forEach(siteCode => {
                const vals = siteValues[siteCode] || { patient: 0, contact: 0 };

                const pCell = document.createElement('td');
                pCell.className = 'text-center';
                pCell.textContent = vals.patient || '-';
                tr.appendChild(pCell);

                const cCell = document.createElement('td');
                cCell.className = 'text-center';
                cCell.textContent = sampleType.contactNA ? '-' : (vals.contact || '-');
                tr.appendChild(cCell);
            });

            tbody.appendChild(tr);
        });

        // Add Total row
        const totalRow = createTotalRow(data, sites);
        tbody.appendChild(totalRow);
    }

    /**
     * Create total row for K. pneumoniae table
     */
    function createTotalRow(data, sites) {
        const tr = document.createElement('tr');
        tr.className = 'table-light';

        // Label
        const labelCell = document.createElement('td');
        labelCell.className = 'fw-bold';
        labelCell.textContent = 'Total Kp. Positive';
        tr.appendChild(labelCell);

        // Calculate grand totals
        let grandTotalPatient = 0;
        let grandTotalContact = 0;
        const siteTotals = {};

        sites.forEach(siteCode => {
            const siteData = data?.[siteCode];
            let sitePatient = 0;
            let siteContact = 0;

            if (siteData) {
                // Sum all sample types for this site
                sitePatient += siteData.patient?.clinical_kp || 0;
                sitePatient += getSampleTotal(siteData.patient?.throat);
                sitePatient += getSampleTotal(siteData.patient?.stool_rectal);

                siteContact += getSampleTotal(siteData.contact?.throat);
                siteContact += getSampleTotal(siteData.contact?.stool_rectal);
            }

            grandTotalPatient += sitePatient;
            grandTotalContact += siteContact;
            siteTotals[siteCode] = { patient: sitePatient, contact: siteContact };
        });

        // Total columns
        const totalPCell = document.createElement('td');
        totalPCell.className = 'text-center fw-bold';
        totalPCell.textContent = grandTotalPatient || '-';
        tr.appendChild(totalPCell);

        const totalCCell = document.createElement('td');
        totalCCell.className = 'text-center fw-bold';
        totalCCell.textContent = grandTotalContact || '-';
        tr.appendChild(totalCCell);

        // Site columns
        sites.forEach(siteCode => {
            const vals = siteTotals[siteCode] || { patient: 0, contact: 0 };

            const pCell = document.createElement('td');
            pCell.className = 'text-center fw-bold';
            pCell.textContent = vals.patient || '-';
            tr.appendChild(pCell);

            const cCell = document.createElement('td');
            cCell.className = 'text-center fw-bold';
            cCell.textContent = vals.contact || '-';
            tr.appendChild(cCell);
        });

        return tr;
    }

    /**
     * Get total positive samples from sample data object
     * Sample data has day1, day2, day3, day4 with positive counts
     */
    function getSampleTotal(sampleData) {
        if (!sampleData) return 0;
        
        let total = 0;
        ['day1', 'day2', 'day3', 'day4'].forEach(day => {
            if (sampleData[day]?.positive) {
                total += sampleData[day].positive;
            }
        });
        return total;
    }

    /**
     * Render error message
     */
    function renderError(message) {
        const tbody = DOM.tableBody();
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-danger">
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