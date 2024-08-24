document.addEventListener('DOMContentLoaded', function () {
    var chartContainer = document.getElementById('chartContainer');
    var buttonContainer = document.getElementById('buttonContainer');
    var dateRangeContainer = document.createElement('div');
    dateRangeContainer.className = 'date-range-container';
    document.body.insertBefore(dateRangeContainer, chartContainer);

    function createChartBox(id, title) {
        var div = document.createElement('div');
        div.className = 'chart-box';

        var h2 = document.createElement('h2');
        h2.textContent = title;
        div.appendChild(h2);

        var select = document.createElement('select');
        select.innerHTML = `
            <option value="bar">長條圖</option>
            <option value="line">折線圖</option>
        `;
        select.className = 'chart-select';
        div.appendChild(select);

        var canvas = document.createElement('canvas');
        canvas.id = id;
        div.appendChild(canvas);

        chartContainer.appendChild(div);
        return { div: div, ctx: canvas.getContext('2d'), select: select };
    }

    function createChart(chartInfo, type, data, options) {
        return new Chart(chartInfo.ctx, {
            type: type,
            data: data,
            options: options
        });
    }

    function setupChart(chartInfo, label, data, bgColor, borderColor) {
        return {
            labels: data.labels,
            datasets: [{
                label: label,
                data: data.values,
                fill: false,
                backgroundColor: bgColor,
                borderColor: borderColor,
                borderWidth: 1
            }]
        };
    }

    const predefinedColors = [
        'rgba(255, 99, 132, 0.5)', 'rgba(54, 162, 235, 0.5)',
        'rgba(255, 206, 86, 0.5)', 'rgba(75, 192, 192, 0.5)',
        'rgba(153, 102, 255, 0.5)', 'rgba(255, 159, 64, 0.5)',
        'rgba(201, 203, 207, 0.5)', 'rgba(160, 100, 50, 0.5)',
        'rgba(60, 180, 75, 0.5)', 'rgba(255, 225, 25, 0.5)',
        'rgba(0, 130, 200, 0.5)', 'rgba(245, 130, 48, 0.5)',
        'rgba(145, 30, 180, 0.5)', 'rgba(70, 240, 240, 0.5)',
        'rgba(240, 50, 230, 0.5)', 'rgba(210, 245, 60, 0.5)',
        'rgba(250, 190, 212, 0.5)', 'rgba(0, 128, 128, 0.5)',
        'rgba(220, 190, 255, 0.5)', 'rgba(170, 110, 40, 0.5)',
        'rgba(255, 250, 200, 0.5)', 'rgba(128, 0, 0, 0.5)',
        'rgba(170, 255, 195, 0.5)', 'rgba(128, 128, 0, 0.5)',
        'rgba(255, 215, 180, 0.5)', 'rgba(0, 0, 128, 0.5)'
    ];

    const predefinedBorderColors = predefinedColors.map(color => color.replace('0.5', '1'));

    function getWeekRange(date) {
        var day = date.getDay();
        var diff = date.getDate() - day;
        var startDate = new Date(date);
        startDate.setDate(diff);
        var endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6);

        return {
            start: startDate,
            end: endDate
        };
    }

    function formatDateToROC(date) {
        var rocYear = date.getFullYear() - 1911;
        var month = (date.getMonth() + 1).toString().padStart(2, '0');
        var day = date.getDate().toString().padStart(2, '0');
        return `${rocYear}年${month}月${day}日`;
    }

    function formatDateRange(startDate, endDate, type) {
        var start, end;
        if (type === 'weekly') {
            start = formatDateToROC(startDate);
            end = formatDateToROC(endDate);
            return `${start} - ${end}`;
        } else if (type === 'monthly') {
            var rocYear = startDate.getFullYear() - 1911;
            var month = (startDate.getMonth() + 1).toString().padStart(2, '0');
            return `${rocYear}年${month}月`;
        } else if (type === 'yearly') {
            var rocYear = startDate.getFullYear() - 1911;
            return `${rocYear}年`;
        }
    }

    function fetchData(url, chartTitle, type, date) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                chartContainer.innerHTML = '';

                var dateRange;
                if (type === 'weekly') {
                    dateRange = getWeekRange(date);
                } else if (type === 'monthly') {
                    dateRange = { start: new Date(date.getFullYear(), date.getMonth(), 1), end: new Date(date.getFullYear(), date.getMonth() + 1, 0) };
                } else if (type === 'yearly') {
                    dateRange = { start: new Date(date.getFullYear(), 0, 1), end: new Date(date.getFullYear(), 11, 31) };
                }
                var formattedDateRange = formatDateRange(dateRange.start, dateRange.end, type);

                dateRangeContainer.textContent = formattedDateRange;

                var sosData = data.SOSdata.map(item => item[1]);
                var sosLabels = data.SOSdata.map(item => item[0]);

                if (sosData.length === 0 || sosData.every(item => item === 0)) {
                    var noDataMessage = document.createElement('div');
                    noDataMessage.textContent = chartTitle + '：目前無資料';
                    noDataMessage.className = 'no-data-message';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var sosChartInfo = createChartBox('sosChart', chartTitle);
                    var SOS = setupChart(sosChartInfo, '求救次數', { labels: sosLabels, values: sosData }, 'rgba(255, 38, 38, 0.5)', 'rgba(255, 38, 38, 0.5)');
                    var sosChart = createChart(sosChartInfo, 'bar', SOS, {
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    });

                    sosChartInfo.select.addEventListener('change', function () {
                        sosChart.destroy();
                        sosChart = createChart(sosChartInfo, this.value, SOS, {
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        });
                    });
                }

                var typeLabels = data.SOSTypedata.map(item => item[0]);
                var typeData = data.SOSTypedata.map(item => item[1]);

                if (typeData.length === 0 || typeData.every(item => item === 0)) {
                    var noDataMessage = document.createElement('div');
                    noDataMessage.textContent = '求救類型分布：目前無資料';
                    noDataMessage.className = 'no-data-message';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var typeChartInfo = createChartBox('sosTypeChart', '求救類型分布');
                    typeChartInfo.select.style.display = 'none';

                    var SOSType = {
                        labels: typeLabels,
                        datasets: [{
                            data: typeData,
                            backgroundColor: predefinedColors.slice(0, typeLabels.length),
                            borderColor: predefinedBorderColors.slice(0, typeLabels.length),
                            borderWidth: 1
                        }]
                    };

                    createChart(typeChartInfo, 'pie', SOSType);
                }

                var placeLabels = data.SOSPlacedata.map(item => item[0]);
                var placeData = data.SOSPlacedata.map(item => item[1]);

                if (placeData.length === 0 || placeData.every(item => item === 0)) {
                    var noDataMessage = document.createElement('div');
                    noDataMessage.textContent = '求救家中地點分布：目前無資料';
                    noDataMessage.className = 'no-data-message';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var placeChartInfo = createChartBox('sosPlaceChart', '求救家中地點分布');
                    placeChartInfo.select.style.display = 'none';

                    var SOSPlace = {
                        labels: placeLabels,
                        datasets: [{
                            data: placeData,
                            backgroundColor: predefinedColors.slice(0, placeLabels.length),
                            borderColor: predefinedBorderColors.slice(0, placeLabels.length),
                            borderWidth: 1
                        }]
                    };

                    createChart(placeChartInfo, 'pie', SOSPlace);
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                var errorMessage = document.createElement('div');
                errorMessage.textContent = '資料加載失敗：' + error.message;
                errorMessage.className = 'error-message';
                chartContainer.appendChild(errorMessage);
            });
    }

    function createNavButton(periodType, link, isCurrent) {
        var button = document.createElement('button');
        button.textContent = isCurrent ?
            (periodType === 'weekly' ? '查看當週' :
                periodType === 'monthly' ? '查看當月' :
                    '查看當年') :
            (periodType === 'weekly' ? '查看上一週' :
                periodType === 'monthly' ? '查看上個月' :
                    '查看上一年');
        button.className = 'nav-button';
        button.addEventListener('click', function () {
            var newLink = isCurrent ? link.replace('_prev', '') : link;
            window.location.href = newLink;
        });
        return button;
    }

    const apiEndpoints = {
        '/analyze/all_weekly': '/analyze/all_weekly_data',
        '/analyze/all_monthly': '/analyze/all_monthly_data',
        '/analyze/all_yearly': '/analyze/all_yearly_data',
        '/analyze/mem_weekly': '/analyze/mem_weekly_data',
        '/analyze/mem_monthly': '/analyze/mem_monthly_data',
        '/analyze/mem_yearly': '/analyze/mem_yearly_data',
        '/analyze/all_weekly_prev': '/analyze/all_prev_weekly_data',
        '/analyze/all_monthly_prev': '/analyze/all_prev_monthly_data',
        '/analyze/all_yearly_prev': '/analyze/all_prev_yearly_data',
        '/analyze/mem_weekly_prev': '/analyze/mem_prev_weekly_data',
        '/analyze/mem_monthly_prev': '/analyze/mem_prev_monthly_data',
        '/analyze/mem_yearly_prev': '/analyze/mem_prev_yearly_data',
    };

    const currentPath = window.location.pathname;
    const endpoint = apiEndpoints[currentPath];
    const title = '求救次數';

    if (endpoint) {
        let type = 'weekly';
        let linkType = '/analyze/all_weekly_prev';
        if (currentPath.includes('monthly')) {
            type = 'monthly';
            linkType = currentPath.includes('all') ? '/analyze/all_monthly_prev' : '/analyze/mem_monthly_prev';
        } else if (currentPath.includes('yearly')) {
            type = 'yearly';
            linkType = currentPath.includes('all') ? '/analyze/all_yearly_prev' : '/analyze/mem_yearly_prev';
        } else {
            linkType = currentPath.includes('all') ? '/analyze/all_weekly_prev' : '/analyze/mem_weekly_prev';
        }

        var isCurrent = currentPath.includes('_prev');
        var currentDate = new Date();

        if (isCurrent) {
            if (type === 'weekly') {
                currentDate.setDate(currentDate.getDate() - 7);
            } else if (type === 'monthly') {
                currentDate.setMonth(currentDate.getMonth() - 1);
            } else if (type === 'yearly') {
                currentDate.setFullYear(currentDate.getFullYear() - 1);
            }
        }

        var navButton = createNavButton(type, linkType, isCurrent);
        buttonContainer.appendChild(navButton);

        fetchData(endpoint, title, type, currentDate);
    }
});
