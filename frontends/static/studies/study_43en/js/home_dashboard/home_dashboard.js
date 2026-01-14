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

(function() {
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
    };
    
    // ========================================================================
    // STATE
    // ========================================================================
    
    let enrollmentChart = null;
    
    // ========================================================================
    // DOM READY
    // ========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        // Only load if on dashboard page with chart canvas
        const chartCanvas = document.getElementById('enrollmentChart');
        if (!chartCanvas) {
            console.log('[Dashboard] Chart canvas not found - skipping enrollment chart');
            return;
        }
        
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
            button.addEventListener('click', function() {
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
        
        // Chart options
        const option = {
            title: {
                text: `Target: ${data.site_target} patients`,
                subtext: `Study Period: Jul 2024 - Apr 2027 (${data.total_months} months) | Site Start: ${data.site_start_date}`,
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
                formatter: function(params) {
                    let html = `<div style="padding: 5px;">`;
                    html += `<strong>${params[0].axisValue}</strong><br/>`;
                    
                    params.forEach(item => {
                        const value = item.value;
                        
                        // Skip if value is null
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
                    
                    // Calculate progress (only if actual has value)
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
                data: data.months,
                axisLabel: {
                    rotate: 45,
                    fontSize: 10,
                    interval: 2, // Show every 3rd label
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
                // Set interval based on target size
                interval: data.site_target <= 200 ? 50 : 100,
                max: function(value) {
                    // Round up to nearest interval
                    const interval = data.site_target <= 200 ? 50 : 100;
                    return Math.ceil(value.max / interval) * interval;
                },
            },
            
            series: [
                {
                    name: 'Target Enrollment',
                    type: 'line',
                    data: data.target,
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
                    data: data.actual,
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
                    // Do NOT connect null data points (creates gaps)
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
                    // Area fill
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
        
        // Set option and render
        enrollmentChart.setOption(option);
        
        // Responsive resize
        window.addEventListener('resize', function() {
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
    
})();