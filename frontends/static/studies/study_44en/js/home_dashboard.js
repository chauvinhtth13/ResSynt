/* static/studies/study_43en/js/home_dashboard_echarts.js */

/**
 * ========================================================================
 * DASHBOARD CHARTS - ECHARTS IMPLEMENTATION
 * Modern, interactive charts with Apache ECharts
 * ======================================================================== 
 */

const DashboardCharts = (function($) {
    'use strict';

    // ==================== CONFIGURATION ====================
    const CONFIG = {
        theme: {
            colors: {
                primary: ['#4b6fd3', '#3e5cb1', '#2f488c', '#23366d'],
                success: ['#28a745', '#20c997', '#17a2b8'],
                danger: ['#eb3239', '#dc3545', '#c82333'],
                warning: ['#ffc107', '#ff9800', '#f57c00'],
                info: ['#4b6fd3', '#5a7ee0', '#8b9de5'],
                gradient: {
                    primary: ['#4b6fd3', '#eb3239'],
                    success: ['#28a745', '#20c997'],
                    danger: ['#eb3239', '#8f1a1f']
                }
            },
            textStyle: {
                fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
                fontSize: 13
            }
        },
        animation: {
            duration: 1000,
            easing: 'cubicOut'
        },
        endpoints: {},
        siteId: 'all',      //  ADD: Store site_id
        filterType: ''      //  ADD: Store filter_type
    };

    // Store chart instances
    const chartInstances = {};

    // ==================== UTILITY FUNCTIONS ====================
    const Utils = {
        /**
         * Debounce function to limit rate of execution
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Initialize ECharts instance
         */
        initChart: function(elementId) {
            const element = document.getElementById(elementId);
            if (!element) {
                console.error(`Element ${elementId} not found`);
                return null;
            }

            // Dispose existing instance
            if (chartInstances[elementId]) {
                chartInstances[elementId].dispose();
            }

            const chart = echarts.init(element);
            chartInstances[elementId] = chart;

            // Responsive resize with debounce to prevent lag
            const debouncedResize = Utils.debounce(function() {
                if (chart && !chart.isDisposed()) {
                    chart.resize();
                }
            }, 150);
            
            window.addEventListener('resize', debouncedResize);

            return chart;
        },


        /**
         * Build URL with site parameter
         */
            buildUrl: function(baseUrl) {
                const url = new URL(baseUrl, window.location.origin);
                if (CONFIG.siteId && CONFIG.siteId !== 'all') {
                    url.searchParams.append('site_id', CONFIG.siteId);
                }
                return url.toString();
            }
        ,

        /**
         * Show loading state
         */
        showLoading: function(elementId) {
            const chart = chartInstances[elementId];
            if (chart) {
                chart.showLoading({
                    text: 'Loading...',
                    color: '#4b6fd3',
                    textColor: '#000',
                    maskColor: 'rgba(255, 255, 255, 0.8)',
                    zlevel: 0
                });
            }
        },

        /**
         * Hide loading state
         */
        hideLoading: function(elementId) {
            const chart = chartInstances[elementId];
            if (chart) {
                chart.hideLoading();
            }
        },

        /**
         * Get resistance color
         */
        getResistanceColor: function(value) {
            if (value >= 50) return '#eb3239';
            if (value >= 30) return '#ffc107';
            return '#28a745';
        },

        /**
         * Format number with commas
         */
        formatNumber: function(num) {
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        },

        /**
         * Animate counter
         */
        animateCounter: function(element, target, decimals = 0) {
            const duration = 1500;
            const start = 0;
            const increment = (target - start) / (duration / 16);
            let current = start;

            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    $(element).text(current.toFixed(decimals));
                    requestAnimationFrame(updateCounter);
                } else {
                    $(element).text(target.toFixed(decimals));
                }
            };

            updateCounter();
        },

        /**
         * Show error message
         */
        showError: function(elementId, message) {
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; min-height: 300px;">
                        <div style="text-align: center; color: #eb3239;">
                            <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                            <p style="margin: 0; font-weight: 600;">${message}</p>
                        </div>
                    </div>
                `;
            }
        },

        /**
         * Show no data message
         */
        showNoData: function(elementId, message) {
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; min-height: 300px;">
                        <div style="text-align: center; color: #6c757d;">
                            <i class="bi bi-info-circle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                            <p style="margin: 0; font-weight: 500;">${message}</p>
                        </div>
                    </div>
                `;
            }
        }
    };

    // ==================== MINI CHARTS FOR STAT CARDS ====================
    const MiniCharts = {
        /**
         * Create sparkline chart
         */
        createSparkline: function(elementId, data) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const option = {
                grid: {
                    left: 0,
                    right: 0,
                    top: 0,
                    bottom: 0
                },
                xAxis: {
                    type: 'category',
                    show: false,
                    data: data.map((_, i) => i)
                },
                yAxis: {
                    type: 'value',
                    show: false
                },
                series: [{
                    type: 'line',
                    data: data,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 2,
                        color: 'rgba(75, 111, 211, 0.8)'
                    },
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0, y: 0, x2: 0, y2: 1,
                            colorStops: [
                                { offset: 0, color: 'rgba(75, 111, 211, 0.3)' },
                                { offset: 1, color: 'rgba(75, 111, 211, 0.05)' }
                            ]
                        }
                    }
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create mini gauge
         */
        createMiniGauge: function(elementId, value, max) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const percentage = (value / max * 100).toFixed(1);

            const option = {
                series: [{
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    center: ['50%', '90%'],
                    radius: '100%',
                    min: 0,
                    max: max,
                    splitNumber: 4,
                    axisLine: {
                        lineStyle: {
                            width: 6,
                            color: [
                                [value / max, '#28a745'],
                                [1, 'rgba(0,0,0,0.1)']
                            ]
                        }
                    },
                    pointer: { show: false },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    axisLabel: { show: false },
                    detail: { show: false }
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create mini donut
         */
        createMiniDonut: function(elementId, value, total) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const percentage = total > 0 ? (value / total * 100).toFixed(1) : 0;

            const option = {
                series: [{
                    type: 'pie',
                    radius: ['60%', '90%'],
                    center: ['50%', '50%'],
                    startAngle: 90,
                    labelLine: { show: false },
                    label: { show: false },
                    data: [
                        {
                            value: value,
                            itemStyle: {
                                color: {
                                    type: 'linear',
                                    x: 0, y: 0, x2: 1, y2: 1,
                                    colorStops: [
                                        { offset: 0, color: '#ffc107' },
                                        { offset: 1, color: '#ff9800' }
                                    ]
                                }
                            }
                        },
                        {
                            value: total - value,
                            itemStyle: { color: 'rgba(0,0,0,0.05)' }
                        }
                    ]
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create mini bar chart
         */
        createMiniBar: function(elementId, data) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const option = {
                grid: {
                    left: 5,
                    right: 5,
                    top: 5,
                    bottom: 5
                },
                xAxis: {
                    type: 'category',
                    show: false,
                    data: data.map((_, i) => i)
                },
                yAxis: {
                    type: 'value',
                    show: false
                },
                series: [{
                    type: 'bar',
                    data: data,
                    barWidth: '60%',
                    itemStyle: {
                        color: {
                            type: 'linear',
                            x: 0, y: 0, x2: 0, y2: 1,
                            colorStops: [
                                { offset: 0, color: 'rgba(128, 130, 133, 0.8)' },
                                { offset: 1, color: 'rgba(128, 130, 133, 0.3)' }
                            ]
                        }
                    }
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create liquid fill gauge (for mortality rate)
         */
        createLiquidGauge: function(elementId, percentage) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            // Simple circular gauge instead of liquid fill
            const color = percentage >= 20 ? '#eb3239' : percentage >= 10 ? '#ffc107' : '#28a745';

            const option = {
                series: [{
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    center: ['50%', '90%'],
                    radius: '100%',
                    min: 0,
                    max: 100,
                    splitNumber: 4,
                    axisLine: {
                        lineStyle: {
                            width: 6,
                            color: [
                                [percentage / 100, color],
                                [1, 'rgba(0,0,0,0.1)']
                            ]
                        }
                    },
                    pointer: { show: false },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    axisLabel: { show: false },
                    detail: { show: false }
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create mini radar chart
         */
        createMiniRadar: function(elementId, value) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const data = [value, value * 0.8, value * 0.9, value * 0.7, value * 0.85];

            const option = {
                radar: {
                    indicator: data.map((_, i) => ({ max: 100 })),
                    center: ['50%', '50%'],
                    radius: '70%',
                    splitNumber: 3,
                    axisLine: { show: false },
                    splitLine: {
                        lineStyle: { color: 'rgba(111, 66, 193, 0.2)' }
                    },
                    splitArea: { show: false }
                },
                series: [{
                    type: 'radar',
                    symbol: 'none',
                    lineStyle: {
                        color: '#6f42c1',
                        width: 2
                    },
                    areaStyle: {
                        color: {
                            type: 'radial',
                            x: 0.5, y: 0.5, r: 0.5,
                            colorStops: [
                                { offset: 0, color: 'rgba(111, 66, 193, 0.4)' },
                                { offset: 1, color: 'rgba(111, 66, 193, 0.1)' }
                            ]
                        }
                    },
                    data: [{ value: data }]
                }]
            };

            chart.setOption(option);
        },

        /**
         * Create progress ring
         */
        createProgressRing: function(elementId, percentage) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            const option = {
                series: [{
                    type: 'gauge',
                    startAngle: 90,
                    endAngle: -270,
                    radius: '90%',
                    pointer: { show: false },
                    progress: {
                        show: true,
                        overlap: false,
                        roundCap: true,
                        clip: false,
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 1, y2: 1,
                                colorStops: [
                                    { offset: 0, color: '#20c997' },
                                    { offset: 1, color: '#28a745' }
                                ]
                            }
                        }
                    },
                    axisLine: {
                        lineStyle: {
                            width: 6,
                            color: [[1, 'rgba(0,0,0,0.08)']]
                        }
                    },
                    splitLine: { show: false },
                    axisTick: { show: false },
                    axisLabel: { show: false },
                    data: [{ value: percentage }],
                    detail: { show: false }
                }]
            };

            chart.setOption(option);
        }
    };

    // ==================== MAIN CHARTS ====================
    const Charts = {
        /**
         * Enrollment Gauge Chart
         */
        createEnrollmentGauge: function(enrolled, target) {
            const chart = Utils.initChart('enrollmentGaugeChart');
            if (!chart) return;

            const percentage = (enrolled / target * 100).toFixed(1);

            const option = {
                series: [{
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    center: ['50%', '75%'],
                    radius: '90%',
                    min: 0,
                    max: target,
                    splitNumber: 8,
                    axisLine: {
                        lineStyle: {
                            width: 30,
                            color: [
                                [0.3, '#eb3239'],
                                [0.7, '#ffc107'],
                                [1, '#28a745']
                            ]
                        }
                    },
                    pointer: {
                        icon: 'path://M2090.36389,615.30999 L2090.36389,615.30999 C2091.48372,615.30999 2092.40383,616.194028 2092.44859,617.312956 L2096.90698,728.755929 C2097.05155,732.369577 2094.2393,735.416212 2090.62566,735.56078 C2090.53845,735.564269 2090.45117,735.566014 2090.36389,735.566014 L2090.36389,735.566014 C2086.74736,735.566014 2083.81557,732.63423 2083.81557,729.017692 C2083.81557,728.930412 2083.81732,728.84314 2083.82081,728.755929 L2088.2792,617.312956 C2088.32396,616.194028 2089.24407,615.30999 2090.36389,615.30999 Z',
                        length: '75%',
                        width: 16,
                        offsetCenter: [0, '5%'],
                        itemStyle: {
                            color: '#4b6fd3',
                            shadowColor: 'rgba(0, 0, 0, 0.3)',
                            shadowBlur: 8,
                            shadowOffsetY: 3
                        }
                    },
                    axisTick: {
                        length: 12,
                        lineStyle: {
                            color: 'auto',
                            width: 2
                        }
                    },
                    splitLine: {
                        length: 20,
                        lineStyle: {
                            color: 'auto',
                            width: 5
                        }
                    },
                    axisLabel: {
                        color: '#464646',
                        fontSize: 14,
                        distance: -60,
                        rotate: 'tangential',
                        formatter: function(value) {
                            return value === target ? target : value === 0 ? '0' : '';
                        }
                    },
                    title: {
                        offsetCenter: [0, '-10%'],
                        fontSize: 20,
                        color: '#464646'
                    },
                    detail: {
                        fontSize: 36,
                        offsetCenter: [0, '-35%'],
                        valueAnimation: true,
                        formatter: function(value) {
                            return Math.round(value);
                        },
                        color: '#4b6fd3',
                        fontWeight: 'bold'
                    },
                    data: [{
                        value: enrolled,
                        name: window.translations.enrolled || 'Enrolled'
                    }]
                }]
            };

            chart.setOption(option);
        },

        /**
         * Gender Distribution Pie Chart
         */
        createGenderPieChart: function(elementId, data, title) {
            const chart = Utils.initChart(elementId);
            if (!chart) return;

            // Responsive configuration
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)',
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: isMobile ? 11 : 13
                    }
                },
                legend: {
                    orient: 'horizontal',
                    bottom: isMobile ? '2%' : '5%',
                    left: 'center',
                    textStyle: {
                        fontSize: isMobile ? 11 : 13,
                        fontWeight: 500
                    },
                    itemWidth: isMobile ? 20 : 25,
                    itemHeight: isMobile ? 12 : 14
                },
                series: [{
                    name: title,
                    type: 'pie',
                    radius: isMobile ? ['40%', '65%'] : ['45%', '70%'],
                    center: ['50%', isMobile ? '42%' : '45%'],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: isMobile ? 6 : 10,
                        borderColor: '#fff',
                        borderWidth: isMobile ? 2 : 3
                    },
                    label: {
                        show: true,
                        position: 'outside',
                        formatter: '{d}%',
                        fontSize: isMobile ? 11 : 14,
                        fontWeight: 'bold',
                        color: '#333'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: isMobile ? 13 : 16,
                            fontWeight: 'bold'
                        },
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    labelLine: {
                        show: true,
                        length: isMobile ? 10 : 15,
                        length2: isMobile ? 6 : 10
                    },
                    data: data.labels.map((label, index) => ({
                        name: label,
                        value: data.data[index],
                        itemStyle: {
                            color: data.colors[index]
                        }
                    }))
                }]
            };

            chart.setOption(option);
        },

        /**
         * Screening Comparison Chart (Mixed Bar + Line)
         */
        createScreeningComparisonChart: function(data) {
            const chart = Utils.initChart('screeningComparisonChart');
            if (!chart) return;

            // Responsive configuration
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross',
                        crossStyle: {
                            color: '#999'
                        }
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: isMobile ? 11 : 13
                    }
                },
                barGap: '0%',  //  Loại bỏ khoảng trống giữa Patient và Contact bars
                barCategoryGap: '40%',  // Khoảng cách giữa các nhóm tháng
                legend: {
                    data: [
                        window.translations.patients || 'Patients',
                        window.translations.contacts || 'Contacts',
                        window.translations.cumulativePatients || 'Cumulative (Patients)',
                        window.translations.cumulativeContacts || 'Cumulative (Contacts)'
                    ],
                    top: '3%',
                    textStyle: {
                        fontSize: isMobile ? 9 : 13,
                        fontWeight: 500
                    },
                    itemWidth: isMobile ? 18 : 25,
                    itemHeight: isMobile ? 10 : 14,
                    itemGap: isMobile ? 8 : 10
                },
                grid: {
                    left: isMobile ? '5%' : '3%',
                    right: isMobile ? '5%' : '4%',
                    bottom: isMobile ? '15%' : '10%',
                    top: isMobile ? '22%' : '15%',
                    containLabel: true
                },
                xAxis: [{
                    type: 'category',
                    data: data.labels,
                    axisPointer: {
                        type: 'shadow'
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    },
                    axisLabel: {
                        fontSize: isMobile ? 9 : 12,
                        color: '#666',
                        rotate: isMobile ? 60 : 45,
                        interval: isMobile ? 'auto' : 0
                    }
                }],
                yAxis: [
                    {
                        type: 'value',
                        name: isMobile ? '' : (window.translations.monthlyCount || 'Monthly Count'),
                        nameTextStyle: {
                            fontSize: isMobile ? 10 : 13,
                            fontWeight: 600,
                            color: '#666'
                        },
                        axisLabel: {
                            formatter: '{value}',
                            fontSize: isMobile ? 9 : 12,
                            color: '#666'
                        },
                        axisLine: {
                            lineStyle: {
                                color: '#ddd'
                            }
                        },
                        splitLine: {
                            lineStyle: {
                                color: '#f0f0f0'
                            }
                        }
                    },
                    {
                        type: 'value',
                        name: isMobile ? '' : (window.translations.cumulativeCount || 'Cumulative'),
                        nameTextStyle: {
                            fontSize: isMobile ? 10 : 13,
                            fontWeight: 600,
                            color: '#666'
                        },
                        axisLabel: {
                            formatter: '{value}',
                            fontSize: isMobile ? 9 : 12,
                            color: '#666'
                        },
                        axisLine: {
                            lineStyle: {
                                color: '#ddd'
                            }
                        },
                        splitLine: {
                            show: false
                        }
                    }
                ],
                series: [
                    {
                        name: window.translations.patients || 'Patients',
                        type: 'bar',
                        data: data.patients,
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: '#4b6fd3' },
                                    { offset: 1, color: '#3e5cb1' }
                                ]
                            },
                            borderRadius: [isMobile ? 4 : 8, isMobile ? 4 : 8, 0, 0]
                        }
                    },
                    {
                        name: window.translations.contacts || 'Contacts',
                        type: 'bar',
                        data: data.contacts,
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: '#17a2b8' },
                                    { offset: 1, color: '#138496' }
                                ]
                            },
                            borderRadius: [isMobile ? 4 : 8, isMobile ? 4 : 8, 0, 0]
                        }
                    },
                    {
                        name: window.translations.cumulativePatients || 'Cumulative (Patients)',
                        type: 'line',
                        yAxisIndex: 1,
                        data: data.patientsCumulative,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: isMobile ? 6 : 8,
                        lineStyle: {
                            width: isMobile ? 2 : 3,
                            color: '#eb3239'
                        },
                        itemStyle: {
                            color: '#eb3239',
                            borderWidth: isMobile ? 1 : 2,
                            borderColor: '#fff'
                        },
                        areaStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(235, 50, 57, 0.3)' },
                                    { offset: 1, color: 'rgba(235, 50, 57, 0.05)' }
                                ]
                            }
                        }
                    },
                    {
                        name: window.translations.cumulativeContacts || 'Cumulative (Contacts)',
                        type: 'line',
                        yAxisIndex: 1,
                        data: data.contactsCumulative,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: isMobile ? 6 : 8,
                        lineStyle: {
                            width: isMobile ? 2 : 3,
                            color: '#28a745'
                        },
                        itemStyle: {
                            color: '#28a745',
                            borderWidth: isMobile ? 1 : 2,
                            borderColor: '#fff'
                        },
                        areaStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(40, 167, 69, 0.3)' },
                                    { offset: 1, color: 'rgba(40, 167, 69, 0.05)' }
                                ]
                            }
                        }
                    }
                ]
            };

            chart.setOption(option);
        },

        /**
         * Patient Enrollment Chart
         */
        createPatientEnrollmentChart: function(data) {
            const chart = Utils.initChart('patientEnrollmentChart');
            if (!chart) return;

            // Responsive configuration
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: isMobile ? 11 : 13
                    }
                },
                legend: {
                    data: [
                        window.translations.monthlyEnrollment || 'Monthly Enrollment',
                        window.translations.cumulativeTotal || 'Cumulative Total'
                    ],
                    top: '3%',
                    textStyle: {
                        fontSize: isMobile ? 10 : 13,
                        fontWeight: 500
                    },
                    itemWidth: isMobile ? 20 : 25,
                    itemHeight: isMobile ? 12 : 14
                },
                grid: {
                    left: isMobile ? '5%' : '3%',
                    right: isMobile ? '5%' : '4%',
                    bottom: isMobile ? '15%' : '10%',
                    top: isMobile ? '18%' : '15%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: data.labels,
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    },
                    axisLabel: {
                        fontSize: isMobile ? 9 : 12,
                        color: '#666',
                        rotate: isMobile ? 60 : 45,
                        interval: isMobile ? 'auto' : 0
                    }
                },
                yAxis: [
                    {
                        type: 'value',
                        name: isMobile ? '' : (window.translations.monthlyCount || 'Monthly'),
                        nameTextStyle: {
                            fontSize: isMobile ? 10 : 13,
                            fontWeight: 600,
                            color: '#666'
                        },
                        axisLabel: {
                            formatter: '{value}',
                            fontSize: isMobile ? 9 : 12,
                            color: '#666'
                        },
                        axisLine: {
                            lineStyle: {
                                color: '#ddd'
                            }
                        },
                        splitLine: {
                            lineStyle: {
                                color: '#f0f0f0'
                            }
                        }
                    },
                    {
                        type: 'value',
                        name: isMobile ? '' : (window.translations.cumulativeTotal || 'Cumulative'),
                        nameTextStyle: {
                            fontSize: isMobile ? 10 : 13,
                            fontWeight: 600,
                            color: '#666'
                        },
                        axisLabel: {
                            formatter: '{value}',
                            fontSize: isMobile ? 9 : 12,
                            color: '#666'
                        },
                        axisLine: {
                            lineStyle: {
                                color: '#ddd'
                            }
                        },
                        splitLine: {
                            show: false
                        }
                    }
                ],
                series: [
                    {
                        name: window.translations.monthlyEnrollment || 'Monthly Enrollment',
                        type: 'bar',
                        data: data.monthly,
                        barWidth: isMobile ? '50%' : '60%',
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: '#4b6fd3' },
                                    { offset: 1, color: '#3e5cb1' }
                                ]
                            },
                            borderRadius: [isMobile ? 4 : 8, isMobile ? 4 : 8, 0, 0]
                        },
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(75, 111, 211, 0.5)'
                            }
                        }
                    },
                    {
                        name: window.translations.cumulativeTotal || 'Cumulative Total',
                        type: 'line',
                        yAxisIndex: 1,
                        data: data.cumulative,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: isMobile ? 6 : 8,
                        lineStyle: {
                            width: isMobile ? 2 : 3,
                            color: '#28a745'
                        },
                        itemStyle: {
                            color: '#28a745',
                            borderWidth: isMobile ? 1 : 2,
                            borderColor: '#fff'
                        },
                        areaStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(40, 167, 69, 0.3)' },
                                    { offset: 1, color: 'rgba(40, 167, 69, 0.05)' }
                                ]
                            }
                        }
                    }
                ]
            };

            chart.setOption(option);
        },

        /**
         * Infection Focus Distribution (Donut Chart)
         */
        createInfectionFocusChart: function(data) {
            const chart = Utils.initChart('infectionFocusChart');
            if (!chart) return;

            // Responsive configuration
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)',
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: isMobile ? 11 : 13
                    }
                },
                legend: {
                    type: isMobile ? 'scroll' : 'plain',
                    orient: 'horizontal',
                    bottom: isMobile ? '0%' : '2%',
                    left: 'center',
                    textStyle: {
                        fontSize: isMobile ? 10 : 12,
                        fontWeight: 500
                    },
                    itemGap: isMobile ? 8 : 15,
                    itemWidth: isMobile ? 18 : 25,
                    itemHeight: isMobile ? 12 : 14,
                    pageIconSize: isMobile ? 10 : 12,
                    formatter: function(name) {
                        const item = data.labels.indexOf(name);
                        const value = data.counts[item];
                        const total = data.counts.reduce((a, b) => a + b, 0);
                        const percent = ((value / total) * 100).toFixed(1);
                        // Mobile: chỉ hiển thị tên ngắn gọn
                        if (isMobile) {
                            return name.length > 15 ? name.substring(0, 13) + '...' : name;
                        }
                        return `${name} (${percent}%)`;
                    }
                },
                series: [{
                    name: 'Infection Focus',
                    type: 'pie',
                    radius: isMobile ? ['35%', '50%'] : (isTablet ? ['38%', '53%'] : ['40%', '55%']),
                    center: isMobile ? ['50%', '38%'] : (isTablet ? ['50%', '42%'] : ['50%', '45%']),
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: isMobile ? 6 : 10,
                        borderColor: '#fff',
                        borderWidth: isMobile ? 2 : 3
                    },
                    label: {
                        show: !isMobile, // Ẩn label trên mobile để tránh chồng chéo
                        position: 'outside',
                        formatter: '{d}%',
                        fontSize: isMobile ? 10 : 13,
                        fontWeight: 600
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: isMobile ? 13 : 16,
                            fontWeight: 'bold'
                        },
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    labelLine: {
                        show: !isMobile,
                        length: isMobile ? 8 : 15,
                        length2: isMobile ? 5 : 10
                    },
                    data: data.labels.map((label, index) => ({
                        name: label,
                        value: data.counts[index],
                        itemStyle: {
                            color: data.colors[index]
                        }
                    }))
                }]
            };

            chart.setOption(option);
        },

        /**
         * Antibiotic Resistance Chart (Horizontal Bar)
         */
        createAntibioticResistanceChart: function(data) {
            const chart = Utils.initChart('antibioticResistanceChart');
            if (!chart) return;

            // Responsive configuration
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: isMobile ? 11 : 13
                    },
                    formatter: function(params) {
                        const item = params[0];
                        const resistance = item.value;
                        const total = data.totals[item.dataIndex];
                        return `${item.name}<br/>
                                ${window.translations.resistanceRate || 'Resistance Rate'}: ${resistance}%<br/>
                                ${window.translations.totalTests || 'Total tests'}: ${total}`;
                    }
                },
                grid: {
                    left: isMobile ? '30%' : (isTablet ? '28%' : '25%'),
                    right: isMobile ? '8%' : '10%',
                    top: '5%',
                    bottom: '5%',
                    containLabel: false
                },
                xAxis: {
                    type: 'value',
                    max: 100,
                    axisLabel: {
                        formatter: '{value}%',
                        fontSize: isMobile ? 10 : 12,
                        color: '#666'
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    },
                    splitLine: {
                        lineStyle: {
                            color: '#f0f0f0'
                        }
                    }
                },
                yAxis: {
                    type: 'category',
                    data: data.labels,
                    axisLabel: {
                        fontSize: isMobile ? 10 : (isTablet ? 11 : 13),
                        color: '#333',
                        fontWeight: isMobile ? 'normal' : 'bold',
                        width: isMobile ? 80 : 150,
                        overflow: 'truncate'
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    }
                },
                series: [{
                    name: window.translations.resistanceRate || 'Resistance Rate',
                    type: 'bar',
                    data: data.resistance.map(value => ({
                        value: value,
                        itemStyle: {
                            color: Utils.getResistanceColor(value),
                            borderRadius: [0, isMobile ? 4 : 8, isMobile ? 4 : 8, 0]
                        }
                    })),
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{c}%',
                        fontSize: isMobile ? 9 : 11,
                        fontWeight: 600,
                        color: '#333'
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.3)'
                        }
                    }
                }]
            };

            chart.setOption(option);
        },

        /**
         * Resistance by Comorbidity Chart
         */
        createResistanceComorbidityChart: function(data) {
            const chart = Utils.initChart('resistanceComorbidityChart');
            if (!chart) return;

            const labels = Object.keys(data);
            const values = labels.map(label => data[label].resistance_rate);

            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#4b6fd3',
                    borderWidth: 1,
                    textStyle: {
                        color: '#fff',
                        fontSize: 13
                    },
                    formatter: function(params) {
                        const item = params[0];
                        const label = item.name;
                        const info = data[label];
                        
                        return `<strong>${label}</strong><br/>
                                ${window.translations.resistanceRate || 'Resistance Rate'}: <strong>${info.resistance_rate}%</strong><br/><br/>
                                ${window.translations.patientsWithCondition || 'Patients with condition'}: ${info.patient_count}<br/>
                                ${window.translations.totalTests || 'Total AST tests'}: ${info.total_tests}<br/>
                                ${window.translations.resistant || 'Resistant'}: ${info.resistant_tests}<br/>
                                ${window.translations.sensitive || 'Sensitive'}: ${info.sensitive_tests}<br/>
                                ${window.translations.intermediate || 'Intermediate'}: ${info.intermediate_tests}`;
                    }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '10%',
                    top: '5%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: labels,
                    axisLabel: {
                        fontSize: 12,
                        color: '#666',
                        rotate: 45,
                        interval: 0
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    max: 100,
                    axisLabel: {
                        formatter: '{value}%',
                        fontSize: 12,
                        color: '#666'
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#ddd'
                        }
                    },
                    splitLine: {
                        lineStyle: {
                            color: '#f0f0f0'
                        }
                    }
                },
                series: [{
                    name: window.translations.resistanceRate || 'Resistance Rate',
                    type: 'bar',
                    barWidth: '60%',
                    data: values.map(value => ({
                        value: value,
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: Utils.getResistanceColor(value) },
                                    { offset: 1, color: Utils.getResistanceColor(value) + 'CC' }
                                ]
                            },
                            borderRadius: [8, 8, 0, 0]
                        }
                    })),
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '{c}%',
                        fontSize: 12,
                        fontWeight: 600,
                        color: function(params) {
                            return Utils.getResistanceColor(params.value);
                        }
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.3)'
                        }
                    }
                }]
            };

            chart.setOption(option);
        }
    };

    // ==================== DATA LOADERS ====================
    const DataLoaders = {
        /**
         * Load Gender Distribution
         */
        loadGenderDistribution: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.genderDistribution), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('patientGenderChart');
                    Utils.showLoading('contactGenderChart');
                },
                success: function(response) {
                    Charts.createGenderPieChart(
                        'patientGenderChart',
                        response.data.patient,
                        'Patient Gender'
                    );
                    Charts.createGenderPieChart(
                        'contactGenderChart',
                        response.data.contact,
                        'Contact Gender'
                    );
                    Utils.hideLoading('patientGenderChart');
                    Utils.hideLoading('contactGenderChart');
                },
                error: function(xhr, status, error) {
                    console.error('Gender distribution error:', error);
                    Utils.showError('patientGenderChart', window.translations.errorLoading);
                    Utils.showError('contactGenderChart', window.translations.errorLoading);
                }
            });
        },

        /**
         * Load Screening Comparison
         */
        loadScreeningComparison: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.screeningComparison), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('screeningComparisonChart');
                },
                success: function(response) {
                    Charts.createScreeningComparisonChart(response.data);
                    Utils.hideLoading('screeningComparisonChart');
                },
                error: function(xhr, status, error) {
                    console.error('Screening comparison error:', error);
                    Utils.showError('screeningComparisonChart', window.translations.errorLoading);
                }
            });
        },

        /**
         * Load Patient Enrollment
         */
        loadPatientEnrollment: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.patientEnrollment), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('patientEnrollmentChart');
                },
                success: function(response) {
                    Charts.createPatientEnrollmentChart(response.data);
                    Utils.hideLoading('patientEnrollmentChart');
                },
                error: function(xhr, status, error) {
                    console.error('Patient enrollment error:', error);
                    Utils.showError('patientEnrollmentChart', window.translations.errorLoading);
                }
            });
        },

        /**
         * Load Infection Focus
         */
        loadInfectionFocus: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.infectionFocus), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('infectionFocusChart');
                },
                success: function(response) {
                    Charts.createInfectionFocusChart(response.data);
                    Utils.hideLoading('infectionFocusChart');
                },
                error: function(xhr, status, error) {
                    console.error('Infection focus error:', error);
                    Utils.showError('infectionFocusChart', window.translations.errorLoading);
                }
            });
        },

        /**
         * Load Antibiotic Resistance
         */
        loadAntibioticResistance: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.antibioticResistance), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('antibioticResistanceChart');
                },
                success: function(response) {
                    Charts.createAntibioticResistanceChart(response.data);
                    Utils.hideLoading('antibioticResistanceChart');
                },
                error: function(xhr, status, error) {
                    console.error('Antibiotic resistance error:', error);
                    Utils.showError('antibioticResistanceChart', window.translations.errorLoading);
                }
            });
        },

        /**
         * Load Resistance by Comorbidity
         */
        loadResistanceComorbidity: function() {
            $.ajax({
                url: Utils.buildUrl(CONFIG.endpoints.resistanceComorbidity), //  CHANGED
                type: 'GET',
                dataType: 'json',
                beforeSend: function() {
                    Utils.showLoading('resistanceComorbidityChart');
                },
                success: function(response) {
                    if (response.status === 'error') {
                        Utils.showError('resistanceComorbidityChart', response.error);
                        return;
                    }

                    const data = response.data;
                    const labels = Object.keys(data);

                    if (labels.length === 0) {
                        Utils.showNoData('resistanceComorbidityChart', 
                            window.translations.insufficientData);
                        return;
                    }

                    Charts.createResistanceComorbidityChart(data);
                    Utils.hideLoading('resistanceComorbidityChart');
                },
                error: function(xhr, status, error) {
                    console.error('Resistance comorbidity error:', error);
                    Utils.showError('resistanceComorbidityChart', window.translations.errorLoading);
                }
            });
        }
    };

    // ==================== INITIALIZATION ====================
    const init = function(config) {
        console.log('Initializing ECharts Dashboard...');
        console.log('Site ID:', config.siteId);
        console.log('Filter Type:', config.filterType);

        // Check dependencies
        if (typeof echarts === 'undefined') {
            console.error('ECharts library not loaded!');
            return;
        }

        if (typeof $ === 'undefined') {
            console.error('jQuery not loaded!');
            return;
        }

        // Set configuration
        CONFIG.endpoints = config.endpoints || {};
        CONFIG.siteId = config.siteId || 'all';           //  STORE site_id
        CONFIG.filterType = config.filterType || '';      //  STORE filter_type

        console.log('📍 Using Site ID:', CONFIG.siteId);

        //  SKIP counter animation - handled by home_dashboard.html
        // The counters are already initialized with or without animation
        // based on isAutoRefresh flag in the HTML template

        // Initialize mini charts in stat cards
        setTimeout(() => {
            MiniCharts.createSparkline('sparkline-screening-patients', [20, 25, 30, 35, 40, 45, 52]);
            MiniCharts.createSparkline('sparkline-screening-contacts', [10, 15, 18, 22, 25, 26, 28]);
            MiniCharts.createMiniDonut('donut-enrolled-contacts', config.enrolledContacts, config.screeningContacts);
            MiniCharts.createMiniBar('bar-hospital-stay', [42, 45, 48, 50, 46, 48]);
            MiniCharts.createMiniRadar('radar-active-cases', config.enrolledPatients);
            MiniCharts.createProgressRing('ring-study-progress', config.percentTarget);
        }, 500);

        // Load AJAX charts with site_id
        DataLoaders.loadGenderDistribution();
        DataLoaders.loadScreeningComparison();
        DataLoaders.loadPatientEnrollment();
        DataLoaders.loadInfectionFocus();
        DataLoaders.loadAntibioticResistance();

        console.log('Dashboard initialized successfully!');
    };

    // ==================== PUBLIC API ====================
    return {
        init: init,
        refreshChart: function(chartType) {
            console.log('Refreshing chart:', chartType);
            switch(chartType) {
                case 'screeningComparison':
                    DataLoaders.loadScreeningComparison();
                    break;
                case 'patientEnrollment':
                    DataLoaders.loadPatientEnrollment();
                    break;
                case 'genderDistribution':
                    DataLoaders.loadGenderDistribution();
                    break;
                case 'infectionFocus':
                    DataLoaders.loadInfectionFocus();
                    break;
                case 'antibioticResistance':
                    DataLoaders.loadAntibioticResistance();
                    break;
            }
        },
        Utils: Utils,
        Charts: Charts
    };

})(jQuery);

// Auto-initialize when document is ready
$(document).ready(function() {
    setTimeout(function() {
        if (typeof window.dashboardConfig !== 'undefined') {
            console.log('Initializing dashboard with config:', window.dashboardConfig);
            DashboardCharts.init(window.dashboardConfig);
        } else {
            console.error('Dashboard configuration not found!');
            console.log('Available window properties:', Object.keys(window));
        }
    }, 100);
});