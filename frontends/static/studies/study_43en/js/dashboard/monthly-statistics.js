/**
 * Monthly Statistics Charts - Patient & Contact
 * ==============================================
 * 
 * Features:
 * - Integrated with SiteSelect dropdown
 * - Flexible view: Quarter or Month by Year
 * - Bar chart with screening & enrollment data
 * - Auto-reload on filter change
 * - Responsive design
 * 
 * Version: 3.0 - SiteSelect Integration + Simplified UX
 */

(function() {
    'use strict';

    // ========================================================================
    // CONFIGURATION
    // ========================================================================

    const CONFIG = {
        PATIENT_API: '/studies/43en/api/patient-monthly-stats/',
        CONTACT_API: '/studies/43en/api/contact-monthly-stats/',
        
        // System font stack
        FONT_FAMILY: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        
        COLORS: {
            screening: {
                bar: '#3b82f6',      // Blue-500
                hover: '#2563eb'     // Blue-600
            },
            enrollment: {
                bar: '#22c55e',      // Green-500
                hover: '#16a34a'     // Green-600
            },
            grid: '#e2e8f0',
            text: {
                primary: '#1e293b',
                secondary: '#475569',
                muted: '#64748b'
            }
        },
        
        QUARTER_MONTHS: {
            'Q1': ['01', '02', '03'],
            'Q2': ['04', '05', '06'],
            'Q3': ['07', '08', '09'],
            'Q4': ['10', '11', '12']
        },
        
        MONTH_NAMES: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    };

    // ========================================================================
    // STATE MANAGEMENT
    // ========================================================================

    const State = {
        patientChart: null,
        contactChart: null,
        
        // Get current site from SiteSelect or hidden input
        getCurrentSite() {
            // Try SiteSelect API first
            if (window.SiteSelect && typeof window.SiteSelect.getSelectedSite === 'function') {
                return window.SiteSelect.getSelectedSite();
            }
            // Fallback to hidden input
            const input = document.getElementById('selectedSiteInput');
            return input ? input.value : 'all';
        }
    };

    // ========================================================================
    // DATA PROCESSOR
    // ========================================================================

    const DataProcessor = {
        /**
         * Filter out data points with no values (both screening and enrollment = 0)
         * @param {Object} data - Processed data with labels, screening, enrollment
         * @returns {Object} - Filtered data
         */
        filterEmptyData(data) {
            if (!data.labels || !data.screening || !data.enrollment) {
                return { labels: [], screening: [], enrollment: [] };
            }
            
            const filtered = { labels: [], screening: [], enrollment: [] };
            
            data.labels.forEach((label, idx) => {
                const s = data.screening[idx] || 0;
                const e = data.enrollment[idx] || 0;
                
                // Only include if there's actual data
                if (s > 0 || e > 0) {
                    filtered.labels.push(label);
                    filtered.screening.push(s);
                    filtered.enrollment.push(e);
                }
            });
            
            return filtered;
        },
        
        /**
         * Aggregate monthly data into years
         * @param {Object} data - Raw data with months, screening, enrollment
         */
        aggregateToYears(data) {
            if (!data.months || !data.screening || !data.enrollment) {
                return { labels: [], screening: [], enrollment: [] };
            }
            
            const yearMap = {};  // { "2024": { screening: 0, enrollment: 0 } }
            
            data.months.forEach((monthLabel, idx) => {
                let yearVal;
                if (monthLabel.includes('/')) {
                    // Format: MM/YYYY
                    yearVal = monthLabel.split('/')[1];
                } else if (monthLabel.includes('-')) {
                    // Format: YYYY-MM
                    yearVal = monthLabel.split('-')[0];
                } else {
                    return;
                }
                
                if (!yearMap[yearVal]) {
                    yearMap[yearVal] = { screening: 0, enrollment: 0 };
                }
                yearMap[yearVal].screening += data.screening[idx] || 0;
                yearMap[yearVal].enrollment += data.enrollment[idx] || 0;
            });
            
            // Sort by year and filter empty
            const sortedYears = Object.keys(yearMap).sort();
            const result = {
                labels: sortedYears,
                screening: sortedYears.map(y => yearMap[y].screening),
                enrollment: sortedYears.map(y => yearMap[y].enrollment)
            };
            
            return this.filterEmptyData(result);
        },
        
        /**
         * Aggregate monthly data into quarters
         * @param {Object} data - Raw data with months, screening, enrollment
         * @param {string} year - Selected year or 'all'
         */
        aggregateToQuarters(data, year = null) {
            if (!data.months || !data.screening || !data.enrollment) {
                return { labels: [], screening: [], enrollment: [] };
            }
            
            // For single year: Q1-YYYY, Q2-YYYY, etc.
            if (year && year !== 'all') {
                const quarters = [`Q1-${year}`, `Q2-${year}`, `Q3-${year}`, `Q4-${year}`];
                const result = {
                    labels: quarters,
                    screening: [0, 0, 0, 0],
                    enrollment: [0, 0, 0, 0]
                };
                
                data.months.forEach((monthLabel, idx) => {
                    let month;
                    if (monthLabel.includes('/')) {
                        month = parseInt(monthLabel.split('/')[0], 10);
                    } else if (monthLabel.includes('-')) {
                        month = parseInt(monthLabel.split('-')[1], 10);
                    } else {
                        return;
                    }
                    const qIdx = Math.floor((month - 1) / 3);
                    result.screening[qIdx] += data.screening[idx] || 0;
                    result.enrollment[qIdx] += data.enrollment[idx] || 0;
                });
                
                return this.filterEmptyData(result);
            }
            
            // For 'all' years: group by Q1-YYYY format
            const quarterMap = {};  // { "Q3-2024": { screening: 0, enrollment: 0 } }
            
            data.months.forEach((monthLabel, idx) => {
                let yearVal, month;
                if (monthLabel.includes('/')) {
                    // Format: MM/YYYY
                    const parts = monthLabel.split('/');
                    month = parseInt(parts[0], 10);
                    yearVal = parts[1];
                } else if (monthLabel.includes('-')) {
                    // Format: YYYY-MM
                    const parts = monthLabel.split('-');
                    yearVal = parts[0];
                    month = parseInt(parts[1], 10);
                } else {
                    return;
                }
                
                const qNum = Math.floor((month - 1) / 3) + 1;
                const key = `Q${qNum}-${yearVal}`;
                const sortKey = `${yearVal}-Q${qNum}`;  // For sorting
                
                if (!quarterMap[key]) {
                    quarterMap[key] = { screening: 0, enrollment: 0, sortKey };
                }
                quarterMap[key].screening += data.screening[idx] || 0;
                quarterMap[key].enrollment += data.enrollment[idx] || 0;
            });
            
            // Sort by year-quarter and build result
            const sortedKeys = Object.keys(quarterMap).sort((a, b) => {
                return quarterMap[a].sortKey.localeCompare(quarterMap[b].sortKey);
            });
            const result = {
                labels: sortedKeys,  // "Q3-2024", "Q4-2024", "Q1-2025"...
                screening: sortedKeys.map(k => quarterMap[k].screening),
                enrollment: sortedKeys.map(k => quarterMap[k].enrollment)
            };
            
            return this.filterEmptyData(result);
        },
        
        /**
         * Process monthly data with proper labels (MM/YYYY format)
         * @param {Object} data - Raw data
         * @param {string} year - Selected year or 'all'
         */
        processMonthly(data, year = null) {
            if (!data.months) return data;
            
            // Convert to MM/YYYY format
            const labels = data.months.map(monthLabel => {
                let month, yearVal;
                if (monthLabel.includes('/')) {
                    // Already MM/YYYY format
                    return monthLabel;
                } else if (monthLabel.includes('-')) {
                    // Format: YYYY-MM -> convert to MM/YYYY
                    const parts = monthLabel.split('-');
                    yearVal = parts[0];
                    month = parts[1];
                    return `${month}/${yearVal}`;
                }
                return monthLabel;
            });
            
            const result = {
                labels,
                screening: data.screening || [],
                enrollment: data.enrollment || []
            };
            
            return this.filterEmptyData(result);
        }
    };

    // ========================================================================
    // CHART BUILDER
    // ========================================================================

    const ChartBuilder = {
        /**
         * Build chart options
         */
        buildOptions(data, title, year, viewMode) {
            const labels = data.labels || [];
            
            return {
                animation: true,
                animationDuration: 600,
                
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    textStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.primary,
                        fontSize: 12
                    },
                    formatter: (params) => {
                        let html = `<div style="padding: 6px 8px;">
                            <strong style="color: ${CONFIG.COLORS.text.primary}; font-size: 12px;">${params[0].axisValue}</strong>
                            <div style="margin-top: 8px;">`;
                        
                        params.forEach(item => {
                            html += `<div style="display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px;">
                                ${item.marker}
                                <span>${item.seriesName}:</span>
                                <strong>${item.value}</strong>
                            </div>`;
                        });
                        
                        html += '</div></div>';
                        return html;
                    }
                },

                legend: {
                    data: ['Screening', 'Enrollment'],
                    top: 0,
                    textStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        fontSize: 12,
                        color: CONFIG.COLORS.text.secondary
                    },
                    itemWidth: 16,
                    itemHeight: 10,
                    itemGap: 24
                },

                grid: {
                    left: 25,
                    right: 5,
                    top: 35,
                    bottom: 10,
                    containLabel: true
                },

                xAxis: {
                    type: 'category',
                    data: labels,
                    axisLine: { lineStyle: { color: CONFIG.COLORS.grid } },
                    axisTick: { lineStyle: { color: CONFIG.COLORS.grid } },
                    axisLabel: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        fontSize: 12,
                        color: CONFIG.COLORS.text.muted
                    }
                },

                yAxis: {
                    type: 'value',
                    name: 'Number of Patients',
                    nameLocation: 'middle',
                    nameRotate: 90,
                    nameGap: 36,
                    nameTextStyle: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        color: CONFIG.COLORS.text.secondary,
                        fontSize: 12,
                        fontWeight: 500
                    },
                    axisLine: { show: false },
                    axisTick: { show: false },
                    axisLabel: {
                        fontFamily: CONFIG.FONT_FAMILY,
                        fontSize: 12,
                        color: CONFIG.COLORS.text.muted
                    },
                    splitLine: {
                        lineStyle: { color: CONFIG.COLORS.grid, type: 'dashed' }
                    },
                    minInterval: 1
                },

                series: [
                    {
                        name: 'Screening',
                        type: 'bar',
                        data: data.screening || [],
                        barWidth: viewMode === 'quarter' ? '30%' : '25%',
                        itemStyle: {
                            color: CONFIG.COLORS.screening.bar,
                            borderRadius: [3, 3, 0, 0]
                        },
                        emphasis: {
                            itemStyle: { color: CONFIG.COLORS.screening.hover }
                        }
                    },
                    {
                        name: 'Enrollment',
                        type: 'bar',
                        data: data.enrollment || [],
                        barWidth: viewMode === 'quarter' ? '30%' : '25%',
                        itemStyle: {
                            color: CONFIG.COLORS.enrollment.bar,
                            borderRadius: [3, 3, 0, 0]
                        },
                        emphasis: {
                            itemStyle: { color: CONFIG.COLORS.enrollment.hover }
                        }
                    }
                ]
            };
        }
    };

    // ========================================================================
    // DATA TABLE BUILDER
    // ========================================================================

    const DataTableBuilder = {
        /**
         * Build and populate data table
         * Only shows rows that have data (screening > 0 OR enrollment > 0)
         * @param {Object} data - Chart data with labels, screening, enrollment
         * @param {string} prefix - 'patient' or 'contact'
         */
        populate(data, prefix) {
            const container = document.getElementById(`${prefix}DataTableContainer`);
            const tbody = document.getElementById(`${prefix}DataTableBody`);
            const screeningTotal = document.getElementById(`${prefix}ScreeningTotal`);
            const enrollmentTotal = document.getElementById(`${prefix}EnrollmentTotal`);
            const rateTotal = document.getElementById(`${prefix}RateTotal`);
            
            if (!container || !tbody) return;
            
            // Filter only rows with data (screening > 0 OR enrollment > 0)
            const labels = data.labels || [];
            const rowsWithData = [];
            
            labels.forEach((label, idx) => {
                const screening = data.screening[idx] || 0;
                const enrollment = data.enrollment[idx] || 0;
                
                // Only include if there's actual data
                if (screening > 0 || enrollment > 0) {
                    rowsWithData.push({ label, screening, enrollment });
                }
            });
            
            // Calculate totals from filtered data
            const totalScreening = rowsWithData.reduce((sum, r) => sum + r.screening, 0);
            const totalEnrollment = rowsWithData.reduce((sum, r) => sum + r.enrollment, 0);
            const totalRate = totalScreening > 0 
                ? ((totalEnrollment / totalScreening) * 100).toFixed(1) 
                : '0.0';
            
            // Update header totals
            if (screeningTotal) screeningTotal.textContent = `(N=${totalScreening})`;
            if (enrollmentTotal) enrollmentTotal.textContent = `(N=${totalEnrollment})`;
            if (rateTotal) rateTotal.textContent = `(${totalRate}%)`;
            
            // Build table rows from filtered data
            let html = '';
            
            rowsWithData.forEach(({ label, screening, enrollment }) => {
                const rate = screening > 0 
                    ? ((enrollment / screening) * 100).toFixed(1) 
                    : '0.0';
                
                html += `
                    <tr>
                        <td class="text-center align-middle">${label}</td>
                        <td class="text-center align-middle">${screening}</td>
                        <td class="text-center align-middle">${enrollment}</td>
                        <td class="text-center align-middle">${rate}%</td>
                    </tr>
                `;
            });
            
            // Add empty state if no data
            if (rowsWithData.length === 0) {
                html = `
                    <tr>
                        <td colspan="4" class="text-center text-muted py-3">
                            <i class="bi bi-inbox me-2"></i>No data available
                        </td>
                    </tr>
                `;
            }
            
            tbody.innerHTML = html;
            container.style.display = 'block';
        },
        
        /**
         * Hide data table
         */
        hide(prefix) {
            const container = document.getElementById(`${prefix}DataTableContainer`);
            if (container) container.style.display = 'none';
        }
    };

    // ========================================================================
    // CHART CONTROLLER - PATIENT
    // ========================================================================

    const PatientChartController = {
        elements: {
            chart: null,
            loading: null,
            viewMode: null,
            year: null
        },

        init() {
            this.elements.chart = document.getElementById('patientMonthlyChart');
            this.elements.loading = document.getElementById('patientChartLoading');
            this.elements.viewMode = document.getElementById('patientViewMode');
            this.elements.year = document.getElementById('patientYear');

            if (!this.elements.chart) return;

            this.bindEvents();
            this.load();
        },

        bindEvents() {
            // View mode change
            this.elements.viewMode?.addEventListener('change', () => this.load());
            
            // Year change
            this.elements.year?.addEventListener('change', () => this.load());
            
            // Listen for site changes (custom event from SiteSelect)
            document.addEventListener('siteChanged', () => this.load());
        },

        showLoading() {
            if (this.elements.loading) {
                this.elements.loading.style.display = 'flex';
            }
        },

        hideLoading() {
            if (this.elements.loading) {
                this.elements.loading.style.display = 'none';
            }
        },

        async load() {
            this.showLoading();

            const viewMode = this.elements.viewMode?.value || 'quarter';
            const year = this.elements.year?.value || new Date().getFullYear().toString();
            
            // Calculate date range
            let startDate, endDate;
            if (year === 'all') {
                startDate = '2024-07-01';  // Study start date
                endDate = '2027-04-30';    // Study end date
            } else {
                startDate = `${year}-01-01`;
                endDate = `${year}-12-31`;
            }

            const params = new URLSearchParams({
                site: State.getCurrentSite(),
                start_date: startDate,
                end_date: endDate
            });

            try {
                const response = await fetch(`${CONFIG.PATIENT_API}?${params}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin'
                });

                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const result = await response.json();
                if (!result.success) throw new Error(result.error || 'API Error');

                this.hideLoading();
                
                // Process data based on view mode
                let chartData;
                if (viewMode === 'year') {
                    chartData = DataProcessor.aggregateToYears(result.data);
                } else if (viewMode === 'quarter') {
                    chartData = DataProcessor.aggregateToQuarters(result.data, year);
                } else {
                    chartData = DataProcessor.processMonthly(result.data, year);
                }
                
                this.render(chartData, year, viewMode);

            } catch (error) {
                console.error('Patient chart error:', error);
                this.hideLoading();
                this.showError(error.message);
            }
        },

        render(data, year, viewMode) {
            if (State.patientChart) {
                State.patientChart.dispose();
            }

            State.patientChart = echarts.init(this.elements.chart, null, {
                renderer: 'canvas',
                devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2)
            });

            const options = ChartBuilder.buildOptions(data, 'Patient Statistics', year, viewMode);
            State.patientChart.setOption(options);
            
            // Populate data table
            DataTableBuilder.populate(data, 'patient');
            
            // Observe container for resize
            ResizeHandler.observeContainer(this.elements.chart);
        },

        showError(message) {
            if (this.elements.chart) {
                this.elements.chart.innerHTML = `
                    <div class="alert alert-danger m-3">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${message}
                    </div>`;
            }
        }
    };

    // ========================================================================
    // CHART CONTROLLER - CONTACT
    // ========================================================================

    const ContactChartController = {
        elements: {
            chart: null,
            loading: null,
            viewMode: null,
            year: null
        },

        init() {
            this.elements.chart = document.getElementById('contactMonthlyChart');
            this.elements.loading = document.getElementById('contactChartLoading');
            this.elements.viewMode = document.getElementById('contactViewMode');
            this.elements.year = document.getElementById('contactYear');

            if (!this.elements.chart) return;

            this.bindEvents();
            this.load();
        },

        bindEvents() {
            this.elements.viewMode?.addEventListener('change', () => this.load());
            this.elements.year?.addEventListener('change', () => this.load());
            document.addEventListener('siteChanged', () => this.load());
        },

        showLoading() {
            if (this.elements.loading) {
                this.elements.loading.style.display = 'flex';
            }
        },

        hideLoading() {
            if (this.elements.loading) {
                this.elements.loading.style.display = 'none';
            }
        },

        async load() {
            this.showLoading();

            const viewMode = this.elements.viewMode?.value || 'quarter';
            const year = this.elements.year?.value || new Date().getFullYear().toString();
            
            // Calculate date range
            let startDate, endDate;
            if (year === 'all') {
                startDate = '2024-07-01';  // Study start date
                endDate = '2027-04-30';    // Study end date
            } else {
                startDate = `${year}-01-01`;
                endDate = `${year}-12-31`;
            }

            const params = new URLSearchParams({
                site: State.getCurrentSite(),
                start_date: startDate,
                end_date: endDate
            });

            try {
                const response = await fetch(`${CONFIG.CONTACT_API}?${params}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin'
                });

                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const result = await response.json();
                if (!result.success) throw new Error(result.error || 'API Error');

                this.hideLoading();
                
                // Process data based on view mode
                let chartData;
                if (viewMode === 'year') {
                    chartData = DataProcessor.aggregateToYears(result.data);
                } else if (viewMode === 'quarter') {
                    chartData = DataProcessor.aggregateToQuarters(result.data, year);
                } else {
                    chartData = DataProcessor.processMonthly(result.data, year);
                }
                
                this.render(chartData, year, viewMode);

            } catch (error) {
                console.error('Contact chart error:', error);
                this.hideLoading();
                this.showError(error.message);
            }
        },

        render(data, year, viewMode) {
            if (State.contactChart) {
                State.contactChart.dispose();
            }

            State.contactChart = echarts.init(this.elements.chart, null, {
                renderer: 'canvas',
                devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2)
            });

            const options = ChartBuilder.buildOptions(data, 'Contact Statistics', year, viewMode);
            State.contactChart.setOption(options);
            
            // Populate data table
            DataTableBuilder.populate(data, 'contact');
            
            // Observe container for resize
            ResizeHandler.observeContainer(this.elements.chart);
        },

        showError(message) {
            if (this.elements.chart) {
                this.elements.chart.innerHTML = `
                    <div class="alert alert-danger m-3">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${message}
                    </div>`;
            }
        }
    };

    // ========================================================================
    // RESIZE HANDLER
    // ========================================================================
    
    const ResizeHandler = {
        observer: null,
        resizeTimeout: null,
        
        /**
         * Resize all active charts
         */
        resizeCharts() {
            if (State.patientChart && !State.patientChart.isDisposed()) {
                State.patientChart.resize();
            }
            if (State.contactChart && !State.contactChart.isDisposed()) {
                State.contactChart.resize();
            }
        },
        
        /**
         * Debounced resize handler
         */
        handleResize() {
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.resizeCharts();
            }, 100);
        },
        
        /**
         * Initialize resize handling
         */
        init() {
            // Cleanup existing
            this.cleanup();
            
            // Bind handler to preserve 'this' context
            const boundHandler = this.handleResize.bind(this);
            
            // Window resize event
            window.addEventListener('resize', boundHandler);
            
            // Store for cleanup
            this._boundHandler = boundHandler;
        },
        
        /**
         * Setup ResizeObserver for a container
         */
        observeContainer(container) {
            if (!container || typeof ResizeObserver === 'undefined') return;
            
            // Create single observer if not exists
            if (!this.observer) {
                this.observer = new ResizeObserver(() => {
                    this.handleResize();
                });
            }
            
            this.observer.observe(container);
        },
        
        /**
         * Cleanup
         */
        cleanup() {
            if (this.observer) {
                this.observer.disconnect();
                this.observer = null;
            }
            if (this._boundHandler) {
                window.removeEventListener('resize', this._boundHandler);
            }
            clearTimeout(this.resizeTimeout);
        }
    };

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    function init() {
        // Initialize resize handler
        ResizeHandler.init();
        
        // Initialize chart controllers
        PatientChartController.init();
        ContactChartController.init();
    }

    // DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for external access
    window.MonthlyStatsCharts = {
        refreshPatient: () => PatientChartController.load(),
        refreshContact: () => ContactChartController.load(),
        refreshAll: () => {
            PatientChartController.load();
            ContactChartController.load();
        }
    };

})();
