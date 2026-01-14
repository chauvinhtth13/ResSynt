/**
 * Contact Monthly Screening & Enrollment Statistics
 * ==================================================
 * 
 * Features:
 * - Bar chart (70%) + Data table (30%)
 * - Site filter buttons
 * - Year/Quarter/Month filter
 * - Responsive design
 * 
 * Version: 1.0
 */

(function() {
    'use strict';
    
    // ========================================================================
    // CONFIGURATION
    // ========================================================================
    
    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/contact-monthly-stats/',
        CHART_COLORS: {
            screening: '#9B59B6',    // Purple for contact screening
            enrollment: '#1ABC9C',   // Turquoise for contact enrollment
            grid: '#E8E8E8',
        },
        CURRENT_SITE: 'all',
        PERIOD_TYPE: 'month',  // 'year', 'quarter', 'month'
        SELECTED_YEAR: '2025',
        SELECTED_QUARTER: 'all',
        SELECTED_MONTH: 'all',
    };
    
    // ========================================================================
    // STATE
    // ========================================================================
    
    let contactChart = null;
    
    // ========================================================================
    // DOM READY
    // ========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        // Only load if on dashboard page with contact chart
        const chartCanvas = document.getElementById('contactChart');
        if (!chartCanvas) {
            console.log('[Contact Stats] Chart canvas not found - skipping load');
            return;
        }
        
        console.log('[Contact Stats] Initializing...');
        
        // Initialize
        initContactSiteButtons();
        initContactPeriodTypeSelector();
        initContactApplyButton();
        loadContactData();
    });
    
    // ========================================================================
    // SITE FILTER BUTTONS
    // ========================================================================
    
    /**
     * Initialize contact site filter buttons
     */
    function initContactSiteButtons() {
        const filterButtons = document.querySelectorAll('.contact-site-btn');
        
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                const site = this.getAttribute('data-site');
                
                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Update current site
                CONFIG.CURRENT_SITE = site;
                
                // Reload data
                console.log('[Contact Stats] Switching to site:', site);
                loadContactData();
            });
        });
    }
    
    // ========================================================================
    // PERIOD TYPE SELECTOR
    // ========================================================================
    
    /**
     * Initialize period type selector (Year/Quarter/Month)
     */
    function initContactPeriodTypeSelector() {
        const periodTypeSelect = document.getElementById('contactPeriodType');
        const yearSelector = document.getElementById('contactYearSelector');
        const quarterSelector = document.getElementById('contactQuarterSelector');
        const monthSelector = document.getElementById('contactMonthSelector');
        
        if (!periodTypeSelect) return;
        
        periodTypeSelect.addEventListener('change', function() {
            const periodType = this.value;
            CONFIG.PERIOD_TYPE = periodType;
            
            // Show/hide appropriate selectors
            if (periodType === 'year') {
                yearSelector.style.display = 'flex';
                quarterSelector.style.display = 'none';
                monthSelector.style.display = 'none';
            } else if (periodType === 'quarter') {
                yearSelector.style.display = 'flex';
                quarterSelector.style.display = 'flex';
                monthSelector.style.display = 'none';
            } else if (periodType === 'month') {
                yearSelector.style.display = 'flex';
                quarterSelector.style.display = 'none';
                monthSelector.style.display = 'flex';
            }
            
            console.log('[Contact Stats] Period type changed:', periodType);
        });
        
        // Trigger initial state
        periodTypeSelect.dispatchEvent(new Event('change'));
    }
    
    /**
     * Initialize apply button
     */
    function initContactApplyButton() {
        const applyBtn = document.getElementById('contactApplyFilter');
        const yearSelect = document.getElementById('contactSelectedYear');
        const quarterSelect = document.getElementById('contactSelectedQuarter');
        const monthSelect = document.getElementById('contactSelectedMonth');
        
        if (!applyBtn) return;
        
        applyBtn.addEventListener('click', function() {
            // Update config
            CONFIG.SELECTED_YEAR = yearSelect ? yearSelect.value : 'all';
            CONFIG.SELECTED_QUARTER = quarterSelect ? quarterSelect.value : 'all';
            CONFIG.SELECTED_MONTH = monthSelect ? monthSelect.value : 'all';
            
            console.log('[Contact Stats] Filters:', {
                periodType: CONFIG.PERIOD_TYPE,
                year: CONFIG.SELECTED_YEAR,
                quarter: CONFIG.SELECTED_QUARTER,
                month: CONFIG.SELECTED_MONTH,
            });
            
            // Reload data
            loadContactData();
        });
    }
    
    /**
     * Calculate date range from year/quarter/month selection
     */
    function calculateDateRange() {
        const periodType = CONFIG.PERIOD_TYPE;
        const year = CONFIG.SELECTED_YEAR;
        const quarter = CONFIG.SELECTED_QUARTER;
        const month = CONFIG.SELECTED_MONTH;
        
        let startDate, endDate;
        
        if (periodType === 'year') {
            if (year === 'all') {
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                startDate = `${year}-01-01`;
                endDate = `${year}-12-31`;
            }
        } else if (periodType === 'quarter') {
            if (year === 'all' || quarter === 'all') {
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                const quarterMonths = {
                    'Q1': { start: '01', end: '03' },
                    'Q2': { start: '04', end: '06' },
                    'Q3': { start: '07', end: '09' },
                    'Q4': { start: '10', end: '12' },
                };
                const months = quarterMonths[quarter];
                startDate = `${year}-${months.start}-01`;
                
                const endMonth = parseInt(months.end);
                const lastDay = new Date(parseInt(year), endMonth, 0).getDate();
                endDate = `${year}-${months.end}-${lastDay}`;
            }
        } else if (periodType === 'month') {
            if (year === 'all' || month === 'all') {
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                startDate = `${year}-${month}-01`;
                
                const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate();
                endDate = `${year}-${month}-${lastDay}`;
            }
        }
        
        return { startDate, endDate };
    }
    
    // ========================================================================
    // DATA LOADING
    // ========================================================================
    
    /**
     * Load contact monthly statistics data
     */
    function loadContactData() {
        const chartContainer = document.getElementById('contactMonthlyChart');
        const loadingIndicator = document.getElementById('contactChartLoading');
        
        // Show loading
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (chartContainer) {
            chartContainer.style.display = 'none';
        }
        
        // Calculate date range from filters
        const { startDate, endDate } = calculateDateRange();
        
        // Build API URL
        const params = new URLSearchParams({
            site: CONFIG.CURRENT_SITE,
            start_date: startDate,
            end_date: endDate,
        });
        
        const url = `${CONFIG.API_ENDPOINT}?${params.toString()}`;
        
        console.log('[Contact Stats] Loading data:', { 
            site: CONFIG.CURRENT_SITE, 
            startDate, 
            endDate,
            periodType: CONFIG.PERIOD_TYPE,
        });
        
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
            
            console.log('[Contact Stats] Data received:', result.data);
            
            // Hide loading
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            if (chartContainer) {
                chartContainer.style.display = 'block';
            }
            
            // Render chart and table
            renderContactChart(chartContainer, result.data);
            renderContactTable(result.data);
        })
        .catch(error => {
            console.error('[Contact Stats] Load error:', error);
            
            if (loadingIndicator) {
                loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load contact statistics: ${escapeHtml(error.message)}
                    </div>
                `;
            }
        });
    }
    
    // ========================================================================
    // CHART RENDERING
    // ========================================================================
    
    /**
     * Render contact monthly bar chart
     */
    function renderContactChart(container, data) {
        // Initialize ECharts instance
        if (contactChart) {
            contactChart.dispose();
        }
        contactChart = echarts.init(container);
        
        // Chart options
        const option = {
            title: {
                text: `Contact Monthly Statistics`,
                subtext: `Period: ${data.start_date} - ${data.end_date}`,
                left: 'center',
                textStyle: {
                    fontSize: 15,
                    fontWeight: 'bold',
                },
                subtextStyle: {
                    fontSize: 11,
                    color: '#666',
                },
            },
            
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow',
                },
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#ccc',
                borderWidth: 1,
                textStyle: {
                    color: '#333',
                },
                formatter: function(params) {
                    let html = `<div style="padding: 5px;">`;
                    html += `<strong>${params[0].axisValue}</strong><br/>`;
                    
                    params.forEach(item => {
                        html += `
                            <div style="margin-top: 5px;">
                                ${item.marker} ${item.seriesName}: 
                                <strong>${item.value}</strong> contacts
                            </div>
                        `;
                    });
                    
                    html += `</div>`;
                    return html;
                },
            },
            
            legend: {
                data: ['Screening', 'Enrollment'],
                top: 35,
                textStyle: {
                    fontSize: 12,
                },
            },
            
            grid: {
                left: '3%',
                right: '4%',
                bottom: '10%',
                top: 65,
                containLabel: true,
            },
            
            xAxis: {
                type: 'category',
                data: data.months,
                axisLabel: {
                    rotate: 45,
                    fontSize: 10,
                },
            },
            
            yAxis: {
                type: 'value',
                name: 'Contacts',
                nameTextStyle: {
                    fontSize: 12,
                    fontWeight: 'bold',
                },
                splitLine: {
                    lineStyle: {
                        color: CONFIG.CHART_COLORS.grid,
                    },
                },
                minInterval: 1,
            },
            
            series: [
                {
                    name: 'Screening',
                    type: 'bar',
                    data: data.screening,
                    itemStyle: {
                        color: CONFIG.CHART_COLORS.screening,
                    },
                    emphasis: {
                        focus: 'series',
                    },
                },
                {
                    name: 'Enrollment',
                    type: 'bar',
                    data: data.enrollment,
                    itemStyle: {
                        color: CONFIG.CHART_COLORS.enrollment,
                    },
                    emphasis: {
                        focus: 'series',
                    },
                },
            ],
        };
        
        // Set option and render
        contactChart.setOption(option);
        
        // Responsive resize
        window.addEventListener('resize', function() {
            if (contactChart) {
                contactChart.resize();
            }
        });
        
        console.log('[Contact Stats] Chart rendered');
    }
    
    // ========================================================================
    // TABLE RENDERING
    // ========================================================================
    
    /**
     * Render contact monthly statistics table
     */
    function renderContactTable(data) {
        const table = document.getElementById('contactStatsTable');
        if (!table) {
            console.error('[Contact Stats] Table not found');
            return;
        }
        
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Clear existing rows
        tbody.innerHTML = '';
        
        // Add data rows
        for (let i = 0; i < data.months.length; i++) {
            const row = document.createElement('tr');
            
            const monthCell = document.createElement('td');
            monthCell.textContent = data.months[i];
            
            const screeningCell = document.createElement('td');
            screeningCell.className = 'text-end fw-semibold';
            screeningCell.style.color = CONFIG.CHART_COLORS.screening;
            screeningCell.textContent = data.screening[i];
            
            const enrollmentCell = document.createElement('td');
            enrollmentCell.className = 'text-end fw-semibold';
            enrollmentCell.style.color = CONFIG.CHART_COLORS.enrollment;
            enrollmentCell.textContent = data.enrollment[i];
            
            row.appendChild(monthCell);
            row.appendChild(screeningCell);
            row.appendChild(enrollmentCell);
            
            tbody.appendChild(row);
        }
        
        // Add total row
        const totalRow = document.createElement('tr');
        totalRow.className = 'table-secondary fw-bold';
        
        const totalLabelCell = document.createElement('td');
        totalLabelCell.textContent = 'Total';
        
        const totalScreeningCell = document.createElement('td');
        totalScreeningCell.className = 'text-end';
        const totalScreening = data.screening.reduce((a, b) => a + b, 0);
        totalScreeningCell.textContent = totalScreening;
        
        const totalEnrollmentCell = document.createElement('td');
        totalEnrollmentCell.className = 'text-end';
        const totalEnrollment = data.enrollment.reduce((a, b) => a + b, 0);
        totalEnrollmentCell.textContent = totalEnrollment;
        
        totalRow.appendChild(totalLabelCell);
        totalRow.appendChild(totalScreeningCell);
        totalRow.appendChild(totalEnrollmentCell);
        
        tbody.appendChild(totalRow);
        
        console.log('[Contact Stats] Table rendered');
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