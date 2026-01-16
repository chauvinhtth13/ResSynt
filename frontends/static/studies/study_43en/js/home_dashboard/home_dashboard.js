/**
 * Dashboard JavaScript for Study 43EN
 * ====================================
 * 
 * Features:
 * - Enrollment chart with ECharts
 * - Target vs Actual comparison
 * - Responsive design
 * 
 * Version: 2.2 - Fixed
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/enrollment-chart/',
        CHART_COLORS: {
            target: '#FF6B6B',          // Red for target
            actual: '#4ECDC4',          // Teal for actual
            grid: '#E8E8E8',            // Light gray for grid
        },
        CURRENT_SITE: 'all',  // Track current site filter
        ALLOWED_SITES: [],    // Sites user can access (from API)
    };

    // ========================================================================
    // STATE
    // ========================================================================

    let enrollmentChart = null;

    // ========================================================================
    // DOM READY
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function () {
        console.log('[Dashboard] Initializing...');
        initEnrollmentChart();
        initSiteFilterButtons();
    });

    // ========================================================================
    // SITE FILTER BUTTONS
    // ========================================================================

    /**
     * Initialize site filter buttons
     */
    function initSiteFilterButtons() {
        const filterButtons = document.querySelectorAll('.site-filter-btn');

        filterButtons.forEach(button => {
            button.addEventListener('click', function () {
                const site = this.getAttribute('data-site');

                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Update current site
                CONFIG.CURRENT_SITE = site;

                // Reload chart with new site
                console.log('[Filter] Switching to site:', site);
                loadChartData(site);
            });
        });
    }

    /**
     * Load chart data for specific site
     */
    function loadChartData(site) {
        const chartContainer = document.getElementById('enrollmentChart');
        const loadingIndicator = document.getElementById('chartLoading');

        // Show loading
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        if (chartContainer) {
            chartContainer.style.display = 'none';
        }

        // Build API URL with site parameter
        const url = site === 'all'
            ? CONFIG.API_ENDPOINT
            : `${CONFIG.API_ENDPOINT}?site=${site}`;

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

                console.log('[Chart] Data received for site:', site, result.data);

                // Update allowed sites from API response
                if (result.allowed_sites) {
                    CONFIG.ALLOWED_SITES = result.allowed_sites;
                    updateSiteFilterButtons(result.allowed_sites);
                }

                // Hide loading
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                if (chartContainer) {
                    chartContainer.style.display = 'block';
                }

                // Render chart
                renderEnrollmentChart(chartContainer, result.data);
            })
            .catch(error => {
                console.error('[Chart] Load error:', error);

                if (loadingIndicator) {
                    loadingIndicator.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load chart: ${escapeHtml(error.message)}
                    </div>
                `;
                }
            });
    }

    /**
     * Update site filter buttons based on user's allowed sites
     * Hides buttons for sites user cannot access
     */
    function updateSiteFilterButtons(allowedSites) {
        const filterButtons = document.querySelectorAll('.site-filter-btn');

        filterButtons.forEach(button => {
            const site = button.getAttribute('data-site');

            // 'all' button only shown if user has 'all' in allowedSites
            if (site === 'all') {
                if (!allowedSites.includes('all')) {
                    button.style.display = 'none';
                }
            } else {
                // Individual site buttons - hide if not in allowed list
                if (!allowedSites.includes(site)) {
                    button.style.display = 'none';
                }
            }
        });

        // If current active button is now hidden, select first visible one
        const activeButton = document.querySelector('.site-filter-btn.active');
        if (activeButton && activeButton.style.display === 'none') {
            const firstVisible = document.querySelector('.site-filter-btn:not([style*="display: none"])');
            if (firstVisible) {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                firstVisible.classList.add('active');
                CONFIG.CURRENT_SITE = firstVisible.getAttribute('data-site');
            }
        }

        console.log('[Filter] Updated buttons for allowed sites:', allowedSites);
    }

    // ========================================================================
    // ENROLLMENT CHART
    // ========================================================================

    /**
     * Initialize enrollment chart with ECharts
     */
    function initEnrollmentChart() {
        loadChartData(CONFIG.CURRENT_SITE);
    }

    /**
     * Render enrollment chart with ECharts
     * 
     * @param {HTMLElement} container - Chart container
     * @param {Object} data - Chart data from backend
     */
    function renderEnrollmentChart(container, data) {
        // Initialize ECharts instance
        if (enrollmentChart) {
            enrollmentChart.dispose();
        }
        enrollmentChart = echarts.init(container);

        // ✅ FIX: Find first month with ANY data (target or actual)
        let startIndex = 0;

        for (let i = 0; i < data.months.length; i++) {
            if (data.target[i] !== null || data.actual[i] !== null) {
                startIndex = i;  // ✅ EXACT - no buffer
                break;
            }
        }

        // Trim arrays to start from first data point
        const trimmedMonths = data.months.slice(startIndex);
        const trimmedTarget = data.target.slice(startIndex);
        const trimmedActual = data.actual.slice(startIndex);

        console.log('[Chart] Exact trim:', {
            original: data.months.length + ' months',
            trimmed: trimmedMonths.length + ' months',
            startFrom: trimmedMonths[0],
            firstTarget: trimmedTarget.find(v => v !== null),
            firstActual: trimmedActual.find(v => v !== null)
        });

        // Chart options (rest stays the same)
        const option = {
            title: {
                text: `Target: ${data.site_target} patients`,
                subtext: formatStudyPeriodSubtext(data),
                left: 'center',
                textStyle: {
                    fontSize: 16,
                    fontWeight: 'bold',
                },
                subtextStyle: {
                    fontSize: 12,
                    color: '#666',
                },
            },

            tooltip: {
                trigger: 'axis',
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
                        const value = item.value;

                        if (value === null || value === undefined) {
                            return;
                        }

                        html += `
                            <div style="margin-top: 5px;">
                                ${item.marker} ${item.seriesName}: 
                                <strong>${value}</strong> patients
                            </div>
                        `;
                    });

                    const targetValue = params[0] ? params[0].value : null;
                    const actualValue = params[1] && params[1].value !== null ? params[1].value : null;

                    if (targetValue !== null && actualValue !== null && targetValue > 0) {
                        const progress = ((actualValue / targetValue) * 100).toFixed(1);

                        html += `
                            <div style="margin-top: 8px; padding-top: 5px; border-top: 1px solid #eee;">
                                Progress: <strong>${progress}%</strong>
                            </div>
                        `;
                    }

                    html += `</div>`;
                    return html;
                },
            },

            legend: {
                data: ['Target Enrollment', 'Actual Enrollment'],
                top: 50,
                textStyle: {
                    fontSize: 13,
                },
            },

            grid: {
                left: '3%',
                right: '4%',
                bottom: '10%',
                top: 100,
                containLabel: true,
            },

            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: trimmedMonths,
                axisLabel: {
                    rotate: 45,
                    fontSize: 10,
                    interval: 'auto',
                },
                axisTick: {
                    alignWithLabel: true,
                },
            },

            yAxis: {
                type: 'value',
                name: 'Patients',
                nameTextStyle: {
                    fontSize: 13,
                    fontWeight: 'bold',
                },
                axisLabel: {
                    formatter: '{value}',
                },
                splitLine: {
                    lineStyle: {
                        color: CONFIG.CHART_COLORS.grid,
                    },
                },
                min: 0,
                interval: data.site_target <= 200 ? 50 : 100,
                max: function (value) {
                    const interval = data.site_target <= 200 ? 50 : 100;
                    return Math.ceil(value.max / interval) * interval;
                },
            },

            series: [
                {
                    name: 'Target Enrollment',
                    type: 'line',
                    data: trimmedTarget,
                    smooth: false,
                    lineStyle: {
                        color: CONFIG.CHART_COLORS.target,
                        width: 3,
                        type: 'solid',
                    },
                    itemStyle: {
                        color: CONFIG.CHART_COLORS.target,
                    },
                    symbol: 'circle',
                    symbolSize: 6,
                    connectNulls: false,
                    emphasis: {
                        focus: 'series',
                        itemStyle: {
                            borderWidth: 2,
                        },
                    },
                },
                {
                    name: 'Actual Enrollment',
                    type: 'line',
                    data: trimmedActual,
                    smooth: true,
                    lineStyle: {
                        color: CONFIG.CHART_COLORS.actual,
                        width: 3,
                    },
                    itemStyle: {
                        color: CONFIG.CHART_COLORS.actual,
                    },
                    symbol: 'circle',
                    symbolSize: 8,
                    connectNulls: false,
                    emphasis: {
                        focus: 'series',
                        itemStyle: {
                            borderColor: CONFIG.CHART_COLORS.actual,
                            borderWidth: 2,
                            shadowBlur: 10,
                            shadowColor: 'rgba(78, 205, 196, 0.5)',
                        },
                    },
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0,
                            y: 0,
                            x2: 0,
                            y2: 1,
                            colorStops: [{
                                offset: 0,
                                color: 'rgba(78, 205, 196, 0.3)',
                            }, {
                                offset: 1,
                                color: 'rgba(78, 205, 196, 0.05)',
                            }],
                        },
                    },
                },
            ],
        };

        enrollmentChart.setOption(option);

        window.addEventListener('resize', function () {
            if (enrollmentChart) {
                enrollmentChart.resize();
            }
        });

        console.log('[Chart] Rendered successfully');
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

    /**
     * Format study period subtext based on site-specific data
     */
    function formatStudyPeriodSubtext(data) {
        // Parse site start month for display
        const siteStartMonth = data.site_start_month || data.site_start_date;

        // For individual sites, show their specific period
        // For 'all', show full study period
        if (CONFIG.CURRENT_SITE === 'all') {
            return `Study Period: Jul 2024 - Apr 2027 (${data.total_months} months)`;
        } else {
            // Format site start month nicely
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            let siteStartDisplay = siteStartMonth;

            // If in MM/YYYY format, convert to Mon YYYY
            if (siteStartMonth && siteStartMonth.includes('/')) {
                const parts = siteStartMonth.split('/');
                if (parts.length === 2) {
                    const monthIdx = parseInt(parts[0], 10) - 1;
                    const year = parts[1];
                    if (monthIdx >= 0 && monthIdx < 12) {
                        siteStartDisplay = `${monthNames[monthIdx]} ${year}`;
                    }
                }
            }

            return `Site Start: ${siteStartDisplay} | Study End: Apr 2027 (${data.total_months} months total)`;
        }
    }

})();