/**
 * K. pneumoniae Isolation Statistics
 * ===================================
 * 
 * Table 7: No. of K. pneumoniae isolated from samples
 * 
 * Features:
 * - By study site (HTD, NHTD, Cho Ray)
 * - Patient and Contact data
 * - Throat swab vs Stool/Rectal swab
 * - Clinical Kp count
 * - Site filter support
 * 
 * Version: 1.1 - Added site filtering
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/kpneumoniae-isolation/',
        CURRENT_SITE: 'all',
        ALLOWED_SITES: [],
    };

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        console.log('[K. pneumoniae] Initializing...');
        initKpneumoniaeSiteButtons();
        loadKpneumoniaeData();
    });

    // ========================================================================
    // SITE FILTER BUTTONS
    // ========================================================================

    /**
     * Initialize K. pneumoniae site filter buttons
     */
    function initKpneumoniaeSiteButtons() {
        const filterButtons = document.querySelectorAll('.kpneumoniae-site-btn');

        filterButtons.forEach(button => {
            button.addEventListener('click', function () {
                const site = this.getAttribute('data-site');

                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Update current site
                CONFIG.CURRENT_SITE = site;

                // Reload data
                console.log('[K. pneumoniae] Switching to site:', site);
                loadKpneumoniaeData();
            });
        });
    }

    /**
     * Update site filter buttons based on user's allowed sites
     */
    function updateKpneumoniaeSiteButtons(allowedSites) {
        const filterButtons = document.querySelectorAll('.kpneumoniae-site-btn');

        filterButtons.forEach(button => {
            const site = button.getAttribute('data-site');

            if (site === 'all') {
                if (!allowedSites.includes('all')) {
                    button.style.display = 'none';
                }
            } else {
                if (!allowedSites.includes(site)) {
                    button.style.display = 'none';
                }
            }
        });

        // If current active button is now hidden, select first visible one
        const activeButton = document.querySelector('.kpneumoniae-site-btn.active');
        if (activeButton && activeButton.style.display === 'none') {
            const firstVisible = document.querySelector('.kpneumoniae-site-btn:not([style*="display: none"])');
            if (firstVisible) {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                firstVisible.classList.add('active');
                CONFIG.CURRENT_SITE = firstVisible.getAttribute('data-site');
                // Reload with correct site
                loadKpneumoniaeData();
            }
        }

        console.log('[K. pneumoniae] Updated buttons for allowed sites:', allowedSites);
    }

    // ========================================================================
    // DATA LOADING
    // ========================================================================

    /**
     * Load K. pneumoniae isolation statistics
     */
    function loadKpneumoniaeData() {
        const tableContainer = document.getElementById('kpneumoniaeTableContainer');
        const loadingIndicator = document.getElementById('kpneumoniaeLoading');

        // Show loading
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (tableContainer) {
            tableContainer.style.display = 'none';
        }

        // Build API URL with site parameter
        const params = new URLSearchParams({
            site: CONFIG.CURRENT_SITE,
        });

        const url = `${CONFIG.API_ENDPOINT}?${params.toString()}`;

        console.log('[K. pneumoniae] Loading data for site:', CONFIG.CURRENT_SITE);

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

                console.log('[K. pneumoniae] Data received:', result.data);

                // Update allowed sites
                if (result.allowed_sites) {
                    CONFIG.ALLOWED_SITES = result.allowed_sites;
                    updateKpneumoniaeSiteButtons(result.allowed_sites);
                }

                // Hide loading
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                if (tableContainer) {
                    tableContainer.style.display = 'block';
                }

                // Render table
                renderKpneumoniaeTable(result.data);
            })
            .catch(error => {
                console.error('[K. pneumoniae] Load error:', error);

                if (loadingIndicator) {
                    loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load K. pneumoniae data: ${escapeHtml(error.message)}
                    </div>
                `;
                }
            });
    }

    // ========================================================================
    // TABLE RENDERING
    // ========================================================================

    /**
     * Render K. pneumoniae isolation table
     */
    function renderKpneumoniaeTable(data) {
        const tbody = document.getElementById('kpneumoniaeTableBody');
        if (!tbody) {
            console.error('[K. pneumoniae] Table body not found');
            return;
        }

        // Clear existing rows
        tbody.innerHTML = '';

        // Get site codes from data (only the ones returned by API)
        const siteOrder = ['003', '011', '020'];
        const sitesToRender = siteOrder.filter(site => data[site] !== undefined);

        if (sitesToRender.length === 0) {
            tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No data available</td></tr>';
            return;
        }

        // Render each site
        sitesToRender.forEach(siteCode => {
            const siteData = data[siteCode];
            if (!siteData) return;

            // Patient row
            const patientRow = createDataRow(
                siteData.site_name,
                'Patient',
                siteData.patient.count,
                siteData.patient.clinical_kp,
                siteData.patient.throat,
                siteData.patient.stool_rectal,
                true  // First row for site (show site name)
            );
            tbody.appendChild(patientRow);

            // Contact row
            const contactRow = createDataRow(
                '',  // No site name (merged cell)
                'Contact',
                siteData.contact.count,
                '-',  // No clinical Kp for contacts
                siteData.contact.throat,
                siteData.contact.stool_rectal,
                false
            );
            tbody.appendChild(contactRow);

            // Complicated cases row (only for HTD based on PDF)
            if (siteCode === '003') {
                const complicatedRow = createDataRow(
                    '',  // No site name
                    'Complicated cases',
                    siteData.complicated.count,
                    siteData.complicated.count,  // Same as count
                    null,  // No throat data
                    null,  // No stool/rectal data
                    false
                );
                tbody.appendChild(complicatedRow);
            }
        });

        console.log('[K. pneumoniae] Table rendered');
    }

    /**
     * Create a data row
     */
    function createDataRow(siteName, subject, participantCount, clinicalKp, throatData, stoolRectalData, showSiteName) {
        const tr = document.createElement('tr');

        // Site name (only for first row of each site)
        if (showSiteName) {
            const siteCell = document.createElement('td');
            siteCell.className = 'fw-bold';
            siteCell.textContent = siteName;
            // Set rowspan based on site (HTD has 3 rows, others have 2)
            siteCell.rowSpan = siteName === 'HTD' ? 3 : 2;
            tr.appendChild(siteCell);
        }

        // Subject
        const subjectCell = document.createElement('td');
        subjectCell.textContent = subject;
        if (subject === 'Complicated cases') {
            subjectCell.className = 'fst-italic text-muted';
        }
        tr.appendChild(subjectCell);

        // Participant count
        const countCell = document.createElement('td');
        countCell.className = 'text-center';
        countCell.textContent = participantCount || '-';
        tr.appendChild(countCell);

        // Clinical Kp
        const clinicalCell = document.createElement('td');
        clinicalCell.className = 'text-center fw-semibold';
        clinicalCell.textContent = clinicalKp || '-';
        tr.appendChild(clinicalCell);

        // Throat swab data (Day 1, 10, 28, 90)
        if (throatData) {
            ['day1', 'day2', 'day3', 'day4'].forEach(day => {
                const cell = document.createElement('td');
                cell.className = 'text-center bg-info bg-opacity-5';
                cell.textContent = throatData[day] ? throatData[day].display : '-';
                tr.appendChild(cell);
            });
        } else {
            // Complicated cases - no throat data
            for (let i = 0; i < 4; i++) {
                const cell = document.createElement('td');
                cell.className = 'text-center bg-info bg-opacity-5 text-muted';
                cell.textContent = '-';
                tr.appendChild(cell);
            }
        }

        // Stool/Rectal swab data (Day 1, 10, 28, 90)
        if (stoolRectalData) {
            ['day1', 'day2', 'day3', 'day4'].forEach(day => {
                const cell = document.createElement('td');
                cell.className = 'text-center bg-warning bg-opacity-5';
                cell.textContent = stoolRectalData[day] ? stoolRectalData[day].display : '-';
                tr.appendChild(cell);
            });
        } else {
            // Complicated cases - no stool/rectal data
            for (let i = 0; i < 4; i++) {
                const cell = document.createElement('td');
                cell.className = 'text-center bg-warning bg-opacity-5 text-muted';
                cell.textContent = '-';
                tr.appendChild(cell);
            }
        }

        return tr;
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