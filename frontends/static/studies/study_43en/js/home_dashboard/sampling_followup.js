/**
 * Sampling Follow-up Statistics (Patient & Contact)
 * ==================================================
 * 
 * Similar to Table 5: Patient sampling and follow-up from study report
 * 
 * Features:
 * - Patient and Contact sampling by visit
 * - Total sampling (stool + rectal + throat)
 * - Blood sampling (separate)
 * - Site filter
 * 
 * Version: 1.0
 */

(function() {
    'use strict';
    
    // ========================================================================
    // CONFIGURATION
    // ========================================================================
    
    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/sampling-followup/',
        CURRENT_SITE: 'all',
    };
    
    // ========================================================================
    // DOM READY
    // ========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[Sampling Followup] Initializing...');
        
        // Initialize
        initSamplingSiteButtons();
        loadSamplingData();
    });
    
    // ========================================================================
    // SITE FILTER BUTTONS
    // ========================================================================
    
    /**
     * Initialize sampling site filter buttons
     */
    function initSamplingSiteButtons() {
        const filterButtons = document.querySelectorAll('.sampling-site-btn');
        
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                const site = this.getAttribute('data-site');
                
                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Update current site
                CONFIG.CURRENT_SITE = site;
                
                // Reload data
                console.log('[Sampling Followup] Switching to site:', site);
                loadSamplingData();
            });
        });
    }
    
    // ========================================================================
    // DATA LOADING
    // ========================================================================
    
    /**
     * Load sampling follow-up statistics data
     */
    function loadSamplingData() {
        const tableContainer = document.getElementById('samplingTableContainer');
        const loadingIndicator = document.getElementById('samplingLoading');
        
        // Show loading
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (tableContainer) {
            tableContainer.style.display = 'none';
        }
        
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
            
            console.log('[Sampling Followup] Data received:', result.data);
            
            // Hide loading
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            if (tableContainer) {
                tableContainer.style.display = 'block';
            }
            
            // Render table
            renderSamplingTable(result.data);
        })
        .catch(error => {
            console.error('[Sampling Followup] Load error:', error);
            
            if (loadingIndicator) {
                loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load sampling data: ${escapeHtml(error.message)}
                    </div>
                `;
            }
        });
    }
    
    // ========================================================================
    // TABLE RENDERING
    // ========================================================================
    
    /**
     * Render sampling follow-up table
     */
    function renderSamplingTable(data) {
        const tbody = document.getElementById('samplingTableBody');
        if (!tbody) {
            console.error('[Sampling Followup] Table body not found');
            return;
        }
        
        // Clear existing rows
        tbody.innerHTML = '';
        
        // Helper function to format value (handle null)
        const formatValue = (val) => {
            if (val === null || val === undefined) {
                return '<span class="text-muted">-</span>';
            }
            return `<strong>${val}</strong>`;
        };
        
        // Define rows based on Table 5 structure
        const rows = [
            {
                label: 'Enrolled',
                patient_total: data.patient.enrolled,
                patient_blood: formatValue(null),  // Not applicable at enrollment
                contact_total: data.contact.enrolled,
                contact_blood: formatValue(null),  // Not applicable at enrollment
            },
            {
                label: 'Sampling_Visit 1 (Day 1)',
                patient_total: data.patient.visit1.total,
                patient_blood: data.patient.visit1.blood,
                contact_total: data.contact.visit1.total,
                contact_blood: data.contact.visit1.blood,
            },
            {
                label: 'Sampling_Visit 2 (Day 10)',
                patient_total: data.patient.visit2.total,
                patient_blood: data.patient.visit2.blood,
                contact_total: formatValue(null),  // Not applicable for contacts
                contact_blood: formatValue(null),
            },
            {
                label: 'Sampling_Visit 3 (Day 28)',
                patient_total: data.patient.visit3.total,
                patient_blood: data.patient.visit3.blood,
                contact_total: data.contact.visit3.total,
                contact_blood: formatValue(null),  // Based on PDF
            },
            {
                label: 'Sampling_Visit 4 (Day 90)',
                patient_total: data.patient.visit4.total,
                patient_blood: data.patient.visit4.blood,
                contact_total: data.contact.visit4.total,
                contact_blood: formatValue(null),
            },
            {
                label: 'Discharged',
                patient_total: data.patient.discharged,
                patient_blood: formatValue(null),
                contact_total: formatValue(null),
                contact_blood: formatValue(null),
            },
        ];
        
        // Render each row
        rows.forEach(row => {
            const tr = document.createElement('tr');
            
            // Schedule column
            const scheduleCell = document.createElement('td');
            scheduleCell.className = 'fw-semibold';
            scheduleCell.textContent = row.label;
            tr.appendChild(scheduleCell);
            
            // Patient Total Sampling
            const patientTotalCell = document.createElement('td');
            patientTotalCell.className = 'text-center bg-primary bg-opacity-10';
            patientTotalCell.innerHTML = formatValue(row.patient_total);
            tr.appendChild(patientTotalCell);
            
            // Patient Blood Sampling
            const patientBloodCell = document.createElement('td');
            patientBloodCell.className = 'text-center bg-primary bg-opacity-10';
            patientBloodCell.innerHTML = formatValue(row.patient_blood);
            tr.appendChild(patientBloodCell);
            
            // Contact Total Sampling
            const contactTotalCell = document.createElement('td');
            contactTotalCell.className = 'text-center bg-success bg-opacity-10';
            contactTotalCell.innerHTML = formatValue(row.contact_total);
            tr.appendChild(contactTotalCell);
            
            // Contact Blood Sampling
            const contactBloodCell = document.createElement('td');
            contactBloodCell.className = 'text-center bg-success bg-opacity-10';
            contactBloodCell.innerHTML = formatValue(row.contact_blood);
            tr.appendChild(contactBloodCell);
            
            tbody.appendChild(tr);
        });
        
        console.log('[Sampling Followup] Table rendered');
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