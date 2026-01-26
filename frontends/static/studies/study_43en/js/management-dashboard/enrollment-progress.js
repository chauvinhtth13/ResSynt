/**
 * Dashboard JavaScript for Study 43EN - Enrollment Progress Chart
 * ================================================================
 * 
 * Features:
 * - Modern ECharts line chart with gradient fills
 * - Responsive design with debounced resize
 * - Data zoom for large datasets  
 * - Enhanced tooltips with progress indicator
 * - Current month marker
 * - Loading states and error handling
 * - Request caching and abort controller
 * - Integration with site multiselect dropdown
 * - Refresh button support
 * 
 * Version: 3.1 - Optimized & Integrated
 */

(function () {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        API_ENDPOINT: '/studies/43en/api/enrollment-chart/',
        
        // System font stack - No external fonts, crisp rendering
        FONT_FAMILY: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        
        // Light theme color palette - Professional & Clean
        COLORS: {
            target: {
                line: '#dc2626',       // Tailwind red-600
                glow: 'rgba(220, 38, 38, 0.15)',
                gradient: ['rgba(220, 38, 38, 0.08)', 'rgba(220, 38, 38, 0)']
            },
            actual: {
                line: '#0284c7',       // Tailwind sky-600  
                glow: 'rgba(2, 132, 199, 0.25)',
                gradient: ['rgba(2, 132, 199, 0.20)', 'rgba(2, 132, 199, 0.02)']
            },
            grid: '#e2e8f0',           // Tailwind slate-200
            axis: '#94a3b8',           // Tailwind slate-400
            text: {
                primary: '#1e293b',    // Tailwind slate-800 (darker for clarity)
                secondary: '#334155',  // Tailwind slate-700 (darker)
                muted: '#64748b'       // Tailwind slate-500 (darker)
            },
            tooltip: {
                bg: 'rgba(255, 255, 255, 0.98)',
                border: '#e2e8f0',
                text: '#1e293b'
            },
            currentMonth: '#d97706',   // Tailwind amber-600
            progressGood: '#16a34a',   // Tailwind green-600
            progressWarning: '#d97706', // Tailwind amber-600
            progressBad: '#dc2626'     // Tailwind red-600
        },
        
        // Performance settings
        DEBOUNCE_MS: 150,
        CACHE_TTL_MS: 60000,  // 1 minute cache
        
        // State
        currentSite: 'all',
        allowedSites: []
    };

    // ========================================================================
    // STATE MANAGEMENT
    // ========================================================================

    const State = {
        chart: null,
        resizeObserver: null,
        abortController: null,
        cache: new Map(),
        
        // Debounce helper
        debounceTimer: null,
        debounce(fn, ms = CONFIG.DEBOUNCE_MS) {
            return (...args) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => fn.apply(this, args), ms);
            };
        }
    };

    // ========================================================================
    // DOM UTILITIES
    // ========================================================================

    const $ = (selector, parent = document) => parent.querySelector(selector);
    const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];

    const DOM = {
        get chartContainer() { return $('#enrollmentChart'); },
        get loadingIndicator() { return $('#chartLoading'); },
        get filterSelect() { return $('.site-filter-select'); },
        get refreshBtn() { return $('#refreshBtn'); },
        get refreshIcon() { return $('#refreshIcon'); },
        get selectedSiteInput() { return $('#selectedSiteInput'); },
        
        showLoading() {
            const loading = this.loadingIndicator;
            const chart = this.chartContainer;
            if (loading) {
                loading.style.display = 'flex';
                loading.style.opacity = '1';
            }
            if (chart) chart.style.opacity = '0.3';
            this.setRefreshSpinning(true);
        },
        
        hideLoading() {
            const loading = this.loadingIndicator;
            const chart = this.chartContainer;
            if (loading) loading.style.display = 'none';
            if (chart) {
                chart.style.opacity = '1';
                chart.style.transition = 'opacity 0.3s ease';
            }
            this.setRefreshSpinning(false);
        },
        
        setRefreshSpinning(spinning) {
            const icon = this.refreshIcon;
            if (icon) {
                icon.classList.toggle('spin', spinning);
            }
        },
        
        showError(message) {
            const loading = this.loadingIndicator;
            if (loading) {
                loading.innerHTML = `
                    <div class="chart-error">
                        <i class="bi bi-exclamation-triangle"></i>
                        <span>${escapeHtml(message)}</span>
                        <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="retryChartBtn">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </div>
                `;
                // Bind retry button
                const retryBtn = $('#retryChartBtn');
                if (retryBtn) {
                    retryBtn.addEventListener('click', () => {
                        SiteFilterController.loadChart(CONFIG.currentSite, true);
                    });
                }
            }
            this.setRefreshSpinning(false);
        },
        
        /**
         * Get currently selected site from dropdown
         */
        getSelectedSite() {
            const input = this.selectedSiteInput;
            return input ? input.value : 'all';
        }
    };

    // ========================================================================
    // DATA PROCESSING
    // ========================================================================

    const DataProcessor = {
        /**
         * Find index of first month with data
         */
        findDataStartIndex(data) {
            for (let i = 0; i < data.months.length; i++) {
                if (data.target[i] !== null || data.actual[i] !== null) {
                    return i;
                }
            }
            return 0;
        },
        
        /**
         * Get current month index in dataset
         */
        getCurrentMonthIndex(months) {
            const now = new Date();
            const currentMonth = `${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
            return months.indexOf(currentMonth);
        },
        
        /**
         * Calculate progress percentage
         */
        calculateProgress(actual, target) {
            if (!target || target === 0) return null;
            return ((actual / target) * 100).toFixed(1);
        },
        
        /**
         * Get progress color based on percentage
         */
        getProgressColor(progress) {
            if (progress >= 90) return CONFIG.COLORS.progressGood;
            if (progress >= 70) return CONFIG.COLORS.progressWarning;
            return CONFIG.COLORS.progressBad;
        },
        
        /**
         * Trim data to start from first actual data point and ensure ends at 04/2027
         */
        trimData(data) {
            const startIndex = this.findDataStartIndex(data);
            const studyEnd = '04/2027';
            
            let months = data.months.slice(startIndex);
            let target = data.target.slice(startIndex);
            let actual = data.actual.slice(startIndex);
            
            // Ensure data ends exactly at 04/2027 (remove any months after)
            const endIndex = months.indexOf(studyEnd);
            if (endIndex !== -1 && endIndex < months.length - 1) {
                months = months.slice(0, endIndex + 1);
                target = target.slice(0, endIndex + 1);
                actual = actual.slice(0, endIndex + 1);
            }
            
            // Ensure data extends to study end (04/2027) if needed
            const lastMonth = months[months.length - 1];
            if (lastMonth !== studyEnd) {
                // Parse last month and study end
                const [lastM, lastY] = lastMonth.split('/').map(Number);
                const [endM, endY] = studyEnd.split('/').map(Number);
                
                // Add missing months until 04/2027
                let currentM = lastM;
                let currentY = lastY;
                
                while (currentY < endY || (currentY === endY && currentM < endM)) {
                    currentM++;
                    if (currentM > 12) {
                        currentM = 1;
                        currentY++;
                    }
                    
                    const newMonth = `${String(currentM).padStart(2, '0')}/${currentY}`;
                    months.push(newMonth);
                    target.push(null);
                    actual.push(null);
                }
            }
            
            return { months, target, actual, startIndex };
        },
        
        /**
         * Get last valid actual value
         */
        getLastActualValue(actual) {
            for (let i = actual.length - 1; i >= 0; i--) {
                if (actual[i] !== null && actual[i] !== undefined) {
                    return { value: actual[i], index: i };
                }
            }
            return { value: 0, index: -1 };
        }
    };

    // ========================================================================
    // CHART RENDERER
    // ========================================================================

    const ChartRenderer = {
        /**
         * Initialize or get ECharts instance
         */
        getChartInstance(container) {
            if (State.chart) {
                State.chart.dispose();
            }
            State.chart = echarts.init(container, null, {
                renderer: 'canvas',
                useDirtyRect: true,  // Performance optimization
                devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2)  // Crisp text on all displays
            });
            return State.chart;
        },
        
        /**
         * Create linear gradient for area fill
         */
        createGradient(colorStops) {
            return {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                    { offset: 0, color: colorStops[0] },
                    { offset: 1, color: colorStops[1] }
                ]
            };
        },
        
        /**
         * Build tooltip formatter
         */
        buildTooltipFormatter(data, trimmedData) {
            return (params) => {
                if (!params || !params.length) return '';
                
                const monthLabel = params[0].axisValue;
                let targetVal = null;
                let actualVal = null;
                
                params.forEach(item => {
                    if (item.seriesName.includes('Target')) targetVal = item.value;
                    if (item.seriesName.includes('Actual')) actualVal = item.value;
                });
                
                let html = `
                    <div class="chart-tooltip">
                        <div class="tooltip-header">${monthLabel}</div>
                        <div class="tooltip-body">
                `;
                
                if (targetVal !== null && targetVal !== undefined) {
                    html += `
                        <div class="tooltip-row">
                            <span class="tooltip-marker" style="background: ${CONFIG.COLORS.target.line}"></span>
                            <span class="tooltip-label">Target:</span>
                            <span class="tooltip-value">${targetVal}</span>
                        </div>
                    `;
                }
                
                if (actualVal !== null && actualVal !== undefined) {
                    html += `
                        <div class="tooltip-row">
                            <span class="tooltip-marker" style="background: ${CONFIG.COLORS.actual.line}"></span>
                            <span class="tooltip-label">Actual:</span>
                            <span class="tooltip-value">${actualVal}</span>
                        </div>
                    `;
                }
                
                html += '</div></div>';
                return html;
            };
        },
        
        /**
         * Build mark line for current month
         */
        buildCurrentMonthMarker(trimmedMonths) {
            const currentIdx = DataProcessor.getCurrentMonthIndex(trimmedMonths);
            if (currentIdx === -1) return null;
            
            return {
                silent: true,
                symbol: 'none',
                lineStyle: {
                    color: CONFIG.COLORS.currentMonth,
                    type: 'dashed',
                    width: 2,
                    opacity: 0.8
                },
                label: {
                    show: true,
                    formatter: 'Now',
                    position: 'insideEndTop',
                    color: CONFIG.COLORS.currentMonth,
                    fontSize: 11,
                    fontWeight: 'bold'
                },
                data: [[
                    { xAxis: currentIdx, yAxis: 0 },
                    { xAxis: currentIdx, yAxis: 'max' }
                ]]
            };
        },
        
        /**
         * Build complete chart options
         */
        buildChartOptions(data, container) {
            const trimmed = DataProcessor.trimData(data);
            const { months, target, actual } = trimmed;
            const lastActual = DataProcessor.getLastActualValue(actual);
            const currentProgress = DataProcessor.calculateProgress(lastActual.value, data.site_target);
            
            // Calculate smart Y-axis max
            const maxValue = Math.max(
                data.site_target,
                ...target.filter(v => v !== null),
                ...actual.filter(v => v !== null)
            );
            const yAxisMax = Math.ceil(maxValue * 1.1 / 50) * 50;
            
            return {
                // Animation
                animation: true,
                animationDuration: 800,
                animationEasing: 'cubicOut',
                
                // Title with progress
                title: {
                    text: `Target: ${data.site_target} patients`,
                    subtext: this.buildSubtext(data, currentProgress),
                    left: 'center',
                    top: 8,
                    itemGap: 4,
                    textStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.primary,
                        fontSize: 15,
                        fontWeight: 600
                    },
                    subtextStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.secondary,
                        fontSize: 12
                    }
                },
                
                // Enhanced tooltip
                tooltip: {
                    trigger: 'axis',
                    backgroundColor: CONFIG.COLORS.tooltip.bg,
                    borderColor: CONFIG.COLORS.tooltip.border,
                    borderWidth: 1,
                    padding: 0,
                    textStyle: { 
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.tooltip.text, 
                        fontSize: 12 
                    },
                    formatter: this.buildTooltipFormatter(data, trimmed),
                    axisPointer: {
                        type: 'line',
                        lineStyle: {
                            color: CONFIG.COLORS.actual.line,
                            width: 1,
                            type: 'dashed'
                        },
                        crossStyle: {
                            color: CONFIG.COLORS.actual.line
                        }
                    },
                    extraCssText: 'border-radius: 8px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);'
                },
                
                // Legend - line with circle for line-point chart
                legend: {
                    data: ['Target Enrollment', 'Actual Enrollment'],
                    top: 52,
                    textStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.secondary,
                        fontSize: 12
                    },
                    itemGap: 50,
                    itemWidth: 24,
                    itemHeight: 12
                },
                
                // Grid - centered chart area with proper margins
                grid: {
                    left: 40,
                    right: 20,
                    top: 80,
                    bottom: 40,
                    containLabel: true
                },
                
                // No dataZoom - show full enrollment progress
                dataZoom: [],
                
                // X Axis - Clear month/year display
                xAxis: {
                    type: 'category',
                    name: 'Timeline (Months)',
                    nameLocation: 'center',
                    nameGap: 45,
                    nameTextStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.secondary,
                        fontSize: 12,
                        fontWeight: 500
                    },
                    boundaryGap: false,
                    data: months,
                    axisLine: {
                        lineStyle: { color: CONFIG.COLORS.grid }
                    },
                    axisTick: {
                        alignWithLabel: true,
                        lineStyle: { color: CONFIG.COLORS.grid },
                        interval: 0
                    },
                    axisLabel: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.muted,
                        fontSize: 11,
                        interval: 0,
                        rotate: 0,
                        formatter: (value, index) => {
                            const [m, y] = value.split('/');
                            const monthNum = parseInt(m, 10);
                            const shortYear = y.slice(2);
                            
                            // January: show with year highlight
                            if (monthNum === 1) {
                                return `{year|${m}}\n{yearLabel|${y}}`;
                            }
                            // First data point also shows year
                            if (index === 0) {
                                return `{month|${m}}\n{yearLabel|${y}}`;
                            }
                            // Other months: just number
                            return `{month|${m}}`;
                        },
                        rich: {
                            month: {
                                fontFamily: CONFIG.FONT_FAMILY,
                                color: CONFIG.COLORS.text.muted,
                                fontSize: 11
                            },
                            year: {
                                fontFamily: CONFIG.FONT_FAMILY,
                                color: CONFIG.COLORS.text.primary,
                                fontSize: 11,
                                fontWeight: 600
                            },
                            yearLabel: {
                                fontFamily: CONFIG.FONT_FAMILY,
                                color: CONFIG.COLORS.text.secondary,
                                fontSize: 10,
                                fontWeight: 600
                            }
                        }
                    },
                    splitLine: {
                        show: true,
                        interval: (index, value) => {
                            // Show vertical line at January (year boundary)
                            const [m] = value.split('/');
                            return parseInt(m, 10) === 1;
                        },
                        lineStyle: {
                            color: CONFIG.COLORS.axis,
                            type: 'solid',
                            width: 1,
                            opacity: 0.3
                        }
                    }
                },
                
                // Y Axis - Dynamic range based on site
                yAxis: {
                    type: 'value',
                    name: 'Number of Patients',
                    nameLocation: 'middle',
                    nameRotate: 90,
                    nameGap: 40,
                    nameTextStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.secondary,
                        fontSize: 12,
                        fontWeight: 500
                    },
                    min: 0,
                    max: CONFIG.currentSite === 'all' 
                        ? 750  // All sites: fixed 0-750
                        : Math.ceil(data.site_target * 1.1 / 10) * 10,  // Per site: 110% of target, rounded to nearest 10
                    interval: CONFIG.currentSite === 'all' ? 50 : null,  // Auto interval for per-site
                    axisLine: { show: false },
                    axisTick: { show: false },
                    axisLabel: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.muted,
                        fontSize: 11
                    },
                    splitLine: {
                        lineStyle: {
                            color: CONFIG.COLORS.grid,
                            type: 'dashed'
                        }
                    }
                },
                
                // Series
                series: [
                    // Target line - Solid red line with solid red points
                    {
                        name: 'Target Enrollment',
                        type: 'line',
                        data: target,
                        smooth: false,
                        symbol: 'circle',
                        symbolSize: 6,
                        showSymbol: true,
                        lineStyle: {
                            color: CONFIG.COLORS.target.line,
                            width: 2,
                            type: 'solid'
                        },
                        itemStyle: {
                            color: CONFIG.COLORS.target.line,
                            borderColor: CONFIG.COLORS.target.line,
                            borderWidth: 0
                        },
                        emphasis: {
                            focus: 'series',
                            scale: 1.5,
                            itemStyle: {
                                color: CONFIG.COLORS.target.line,
                                borderColor: '#ffffff',
                                borderWidth: 2,
                                shadowBlur: 8,
                                shadowColor: CONFIG.COLORS.target.glow
                            }
                        },
                        connectNulls: false
                    },
                    
                    // Actual line - Solid blue line with solid blue points
                    {
                        name: 'Actual Enrollment',
                        type: 'line',
                        data: actual,
                        smooth: false,
                        symbol: 'circle',
                        symbolSize: 8,
                        showSymbol: true,
                        lineStyle: {
                            color: CONFIG.COLORS.actual.line,
                            width: 3,
                            type: 'solid'
                        },
                        itemStyle: {
                            color: CONFIG.COLORS.actual.line,
                            borderColor: CONFIG.COLORS.actual.line,
                            borderWidth: 0
                        },
                        emphasis: {
                            focus: 'series',
                            scale: 1.6,
                            itemStyle: {
                                color: CONFIG.COLORS.actual.line,
                                borderColor: '#ffffff',
                                borderWidth: 2,
                                shadowBlur: 12,
                                shadowColor: CONFIG.COLORS.actual.glow
                            }
                        },
                        // Mark the latest data point with a pin
                        markPoint: lastActual.index >= 0 ? {
                            symbol: 'pin',
                            symbolSize: 42,
                            animation: true,
                            data: [{
                                name: 'Current',
                                coord: [lastActual.index, lastActual.value],
                                value: lastActual.value,
                                itemStyle: {
                                    color: CONFIG.COLORS.progressGood,
                                    shadowColor: 'rgba(22, 163, 74, 0.4)',
                                    shadowBlur: 8
                                },
                                label: {
                                    color: '#ffffff',
                                    fontWeight: 'bold',
                                    fontSize: 11
                                }
                            }]
                        } : undefined,
                        markLine: this.buildCurrentMonthMarker(months),
                        connectNulls: false
                    }
                ]
            };
        },
        
        /**
         * Build subtitle text
         */
        buildSubtext(data, progress) {
            const period = CONFIG.currentSite === 'all' 
                ? `Study Period: Jul 2024 - Apr 2027 (${data.total_months} months)`
                : `Site Start: ${this.formatMonth(data.site_start_month)} | Study End: Apr 2027`;
            
            const progressText = progress !== null 
                ? `  •  Current Progress: ${progress}%` 
                : '';
            
            return period + progressText;
        },
        
        /**
         * Format month string
         */
        formatMonth(monthStr) {
            if (!monthStr || !monthStr.includes('/')) return monthStr;
            
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const [m, y] = monthStr.split('/');
            const monthIdx = parseInt(m, 10) - 1;
            
            return monthIdx >= 0 && monthIdx < 12 
                ? `${monthNames[monthIdx]} ${y}` 
                : monthStr;
        },
        
        /**
         * Render chart with data
         */
        render(container, data) {
            const chart = this.getChartInstance(container);
            const options = this.buildChartOptions(data, container);
            
            chart.setOption(options, true);
            
            // Setup resize observer
            this.setupResizeHandling(chart, container);
            
            return chart;
        },
        
        /**
         * Setup responsive resize handling
         */
        setupResizeHandling(chart, container) {
            // Clean up existing observer
            if (State.resizeObserver) {
                State.resizeObserver.disconnect();
            }
            
            // Use ResizeObserver for container-based resizing
            if (typeof ResizeObserver !== 'undefined') {
                State.resizeObserver = new ResizeObserver(
                    State.debounce(() => {
                        if (chart && !chart.isDisposed()) {
                            chart.resize();
                        }
                    })
                );
                State.resizeObserver.observe(container);
            }
            
            // Fallback window resize
            window.addEventListener('resize', 
                State.debounce(() => {
                    if (chart && !chart.isDisposed()) {
                        chart.resize();
                    }
                })
            );
        }
    };

    // ========================================================================
    // API SERVICE
    // ========================================================================

    const ApiService = {
        /**
         * Build cache key from site
         */
        getCacheKey(site) {
            return `enrollment_${site}`;
        },
        
        /**
         * Check if cached data is still valid
         */
        isCacheValid(cacheEntry) {
            if (!cacheEntry) return false;
            return Date.now() - cacheEntry.timestamp < CONFIG.CACHE_TTL_MS;
        },
        
        /**
         * Fetch chart data from API
         */
        async fetchData(site) {
            // Check cache first
            const cacheKey = this.getCacheKey(site);
            const cached = State.cache.get(cacheKey);
            
            if (this.isCacheValid(cached)) {
                return cached.data;
            }
            
            // Abort any pending request
            if (State.abortController) {
                State.abortController.abort();
            }
            State.abortController = new AbortController();
            
            // Build URL
            const url = site === 'all' 
                ? CONFIG.API_ENDPOINT 
                : `${CONFIG.API_ENDPOINT}?site=${encodeURIComponent(site)}`;
            
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin',
                    signal: State.abortController.signal
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                if (!result.success) {
                    throw new Error(result.error || 'Unknown API error');
                }
                
                // Cache the result
                State.cache.set(cacheKey, {
                    data: result,
                    timestamp: Date.now()
                });
                
                return result;
                
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw new Error('Request cancelled');
                }
                throw error;
            }
        }
    };

    // ========================================================================
    // SITE FILTER CONTROLLER
    // ========================================================================

    const SiteFilterController = {
        /**
         * Initialize site filter dropdown
         */
        init() {
            const select = DOM.filterSelect;
            if (!select) return;
            
            select.addEventListener('change', (e) => {
                CONFIG.currentSite = e.target.value;
                this.loadChart(CONFIG.currentSite);
            });
        },
        
        /**
         * Update available options based on allowed sites
         */
        updateOptions(allowedSites) {
            CONFIG.allowedSites = allowedSites;
            
            const select = DOM.filterSelect;
            if (!select) return;
            
            $$('option', select).forEach(opt => {
                const site = opt.value;
                
                if (site === 'all') {
                    opt.hidden = !allowedSites.includes('all');
                } else {
                    opt.hidden = !allowedSites.includes(site);
                }
            });
            
            // If current selection is now hidden, select first visible
            const currentOption = $(`option[value="${CONFIG.currentSite}"]`, select);
            if (currentOption && currentOption.hidden) {
                const firstVisible = $('option:not([hidden])', select);
                if (firstVisible) {
                    select.value = firstVisible.value;
                    CONFIG.currentSite = firstVisible.value;
                }
            }
        },
        
        /**
         * Load chart for specific site
         * @param {string} site - Site code or 'all'
         * @param {boolean} forceRefresh - Skip cache if true
         */
        async loadChart(site, forceRefresh = false) {
            const container = DOM.chartContainer;
            if (!container) return;
            
            DOM.showLoading();
            
            try {
                // Clear cache on force refresh
                if (forceRefresh) {
                    const cacheKey = ApiService.getCacheKey(site);
                    State.cache.delete(cacheKey);
                }
                
                const result = await ApiService.fetchData(site);
                
                // Update allowed sites
                if (result.allowed_sites) {
                    this.updateOptions(result.allowed_sites);
                }
                
                DOM.hideLoading();
                
                // Render chart
                ChartRenderer.render(container, result.data);
                
            } catch (error) {
                if (error.message !== 'Request cancelled') {
                    console.error('Chart load error:', error);
                    DOM.showError(error.message);
                }
            }
        },
        
        /**
         * Refresh chart with current selection
         */
        refresh() {
            const site = DOM.getSelectedSite();
            CONFIG.currentSite = site;
            this.loadChart(site, true);
        }
    };

    // ========================================================================
    // REFRESH BUTTON CONTROLLER
    // ========================================================================
    
    const RefreshController = {
        init() {
            const btn = DOM.refreshBtn;
            if (!btn) return;
            
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                SiteFilterController.refresh();
            });
        }
    };

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

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

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    function init() {
        // Initialize controllers
        SiteFilterController.init();
        RefreshController.init();
        
        // Get initial site from dropdown or default to 'all'
        const initialSite = DOM.getSelectedSite() || 'all';
        CONFIG.currentSite = initialSite;
        
        // Load initial chart
        SiteFilterController.loadChart(initialSite);
    }

    // DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.EnrollmentChart = {
        refresh: () => SiteFilterController.refresh(),
        loadSite: (site) => {
            CONFIG.currentSite = site;
            SiteFilterController.loadChart(site, true);
        }
    };

})();
