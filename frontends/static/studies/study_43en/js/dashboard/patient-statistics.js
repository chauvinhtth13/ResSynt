/**
 * Monthly Screening & Enrollment Statistics
 * ==========================================
 * 
 * Features:
 * - Bar chart (70%) + Data table (30%)
 * - Site filter buttons
 * - Date range filter
 * - Responsive design
 * 
 * Version: 1.0
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/monthly-stats/',
        CHART_COLORS: {
            screening: '#3498DB',    // Blue for screening
            enrollment: '#2ECC71',   // Green for enrollment
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

    let monthlyChart = null;

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {

        // Initialize
        initMonthlySiteButtons();
        initPeriodTypeSelector();
        initApplyButton();
        loadMonthlyData();
    });

    // ========================================================================
    // SITE FILTER BUTTONS
    // ========================================================================

    /**
     * Initialize monthly site filter dropdown
     */
    function initMonthlySiteButtons() {
        const filterSelect = document.querySelector('.monthly-site-select');

        if (filterSelect) {
            filterSelect.addEventListener('change', function () {
                const site = this.value;

                // Update current site
                CONFIG.CURRENT_SITE = site;

                // Reload data
                loadMonthlyData();
            });
        }
    }

    // ========================================================================
    // PERIOD TYPE SELECTOR
    // ========================================================================

    /**
     * Initialize period type selector (Year/Quarter/Month)
     */
    function initPeriodTypeSelector() {
        const periodTypeSelect = document.getElementById('periodType');
        const yearSelector = document.getElementById('yearSelector');
        const quarterSelector = document.getElementById('quarterSelector');
        const monthSelector = document.getElementById('monthSelector');

        if (!periodTypeSelect) return;

        periodTypeSelect.addEventListener('change', function () {
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

        });

        // Trigger initial state
        periodTypeSelect.dispatchEvent(new Event('change'));
    }

    /**
     * Initialize apply button
     */
    function initApplyButton() {
        const applyBtn = document.getElementById('monthlyApplyFilter');
        const yearSelect = document.getElementById('selectedYear');
        const quarterSelect = document.getElementById('selectedQuarter');
        const monthSelect = document.getElementById('selectedMonth');

        if (!applyBtn) return;

        applyBtn.addEventListener('click', function () {
            // Update config
            CONFIG.SELECTED_YEAR = yearSelect ? yearSelect.value : 'all';
            CONFIG.SELECTED_QUARTER = quarterSelect ? quarterSelect.value : 'all';
            CONFIG.SELECTED_MONTH = monthSelect ? monthSelect.value : 'all';


            // Reload data
            loadMonthlyData();
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
                // All years: study start to today
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                // Specific year: Jan 1 to Dec 31
                startDate = `${year}-01-01`;
                endDate = `${year}-12-31`;
            }
        } else if (periodType === 'quarter') {
            if (year === 'all' || quarter === 'all') {
                // All: study start to today
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                // Specific quarter
                const quarterMonths = {
                    'Q1': { start: '01', end: '03' },
                    'Q2': { start: '04', end: '06' },
                    'Q3': { start: '07', end: '09' },
                    'Q4': { start: '10', end: '12' },
                };
                const months = quarterMonths[quarter];
                startDate = `${year}-${months.start}-01`;

                // Last day of end month
                const endMonth = parseInt(months.end);
                const lastDay = new Date(parseInt(year), endMonth, 0).getDate();
                endDate = `${year}-${months.end}-${lastDay}`;
            }
        } else if (periodType === 'month') {
            if (year === 'all' || month === 'all') {
                // All: study start to today
                startDate = '2024-07-01';
                endDate = new Date().toISOString().split('T')[0];
            } else {
                // Specific month
                startDate = `${year}-${month}-01`;

                // Last day of month
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
     * Load monthly statistics data
     */
    function loadMonthlyData() {
        const chartContainer = document.getElementById('monthlyChart');
        const loadingIndicator = document.getElementById('monthlyChartLoading');

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
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                if (chartContainer) {
                    chartContainer.style.display = 'block';
                }

                // Render chart and table
                renderMonthlyChart(chartContainer, result.data);
                renderMonthlyTable(result.data);
            })
            .catch(error => {

                if (loadingIndicator) {
                    loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load monthly statistics: ${escapeHtml(error.message)}
                    </div>
                `;
                }
            });
    }

    // ========================================================================
    // CHART RENDERING
    // ========================================================================

    /**
     * Render monthly bar chart
     */
    function renderMonthlyChart(container, data) {
        // Initialize ECharts instance
        if (monthlyChart) {
            monthlyChart.dispose();
        }
        monthlyChart = echarts.init(container);

        // Chart options
        const option = {
            title: {
                text: `Monthly Statistics`,
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
                formatter: function (params) {
                    let html = `<div style="padding: 5px;">`;
                    html += `<strong>${params[0].axisValue}</strong><br/>`;

                    params.forEach(item => {
                        html += `
                            <div style="margin-top: 5px;">
                                ${item.marker} ${item.seriesName}: 
                                <strong>${item.value}</strong> patients
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
                name: 'Patients',
                nameTextStyle: {
                    fontSize: 12,
                    fontWeight: 'bold',
                },
                splitLine: {
                    lineStyle: {
                        color: CONFIG.CHART_COLORS.grid,
                    },
                },
                minInterval: 1,  // Integer values only
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
        monthlyChart.setOption(option);

        // Responsive resize
        window.addEventListener('resize', function () {
            if (monthlyChart) {
                monthlyChart.resize();
            }
        });
    }

    // ========================================================================
    // TABLE RENDERING
    // ========================================================================

    /**
     * Render monthly statistics table
     */
    function renderMonthlyTable(data) {
        const table = document.getElementById('monthlyStatsTable');
        if (!table) {
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
            screeningCell.className = 'text-end fw-semibold text-primary';
            screeningCell.textContent = data.screening[i];

            const enrollmentCell = document.createElement('td');
            enrollmentCell.className = 'text-end fw-semibold text-success';
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