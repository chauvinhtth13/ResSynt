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
 * 
 * Version: 1.0
 */

(function() {
    'use strict';
    
    // ========================================================================
    // CONFIGURATION
    // ========================================================================
    
    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/kpneumoniae-isolation/',
    };
    
    // ========================================================================
    // DOM READY
    // ========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        // Only load if on dashboard page with target container
        const container = document.getElementById('kpneumoniaeTableContainer');
        if (!container) {
            console.log('[K. pneumoniae] Container not found - skipping load');
            return;
        }
        
        console.log('[K. pneumoniae] Initializing...');
        loadKpneumoniaeData();
    });
    
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
        
        // Fetch data
        fetch(CONFIG.API_ENDPOINT, {
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
        
        // Site order: HTD (003), Cho Ray (011), NHTD (020)
        const siteOrder = ['003', '011', '020'];
        
        // Render each site
        siteOrder.forEach(siteCode => {
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