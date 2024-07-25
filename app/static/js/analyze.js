document.addEventListener('DOMContentLoaded', function () {
    var chartContainer = document.getElementById('chartContainer');

    function createChartBox(id, title, dateRange) {
        var div = document.createElement('div');
        div.className = 'chart-box';
        div.style.border = '1px solid #000';
        div.style.padding = '10px';
        div.style.margin = '10px 0';

        var h2 = document.createElement('h2');
        h2.textContent = title;
        div.appendChild(h2);

        var dateDiv = document.createElement('div');
        dateDiv.textContent = dateRange;
        dateDiv.style.fontSize = '12px';
        dateDiv.style.color = '#555';
        div.appendChild(dateDiv);

        var select = document.createElement('select');
        select.innerHTML = `
            <option value="bar">長條圖</option>
            <option value="line">折線圖</option>
        `;
        div.appendChild(select);
        select.style.fontSize = '14px';

        var canvas = document.createElement('canvas');
        canvas.id = id;
        canvas.width = 100;
        canvas.height = 50;
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

    function formatDateRange(startDate, endDate) {
        var start = formatDateToROC(startDate);
        var end = formatDateToROC(endDate);
        return `${start} - ${end}`;
    }

    function fetchData(url, chartTitle) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                var currentDate = new Date();
                var dateRange = getWeekRange(currentDate);
                var formattedDateRange = formatDateRange(dateRange.start, dateRange.end);

                var sosData = data.SOSdata.map(item => item[1]);
                var sosLabels = data.SOSdata.map(item => item[0]);

                if (sosData.length === 0 || sosData.every(item => item === 0)) {
                    var noDataMessage = document.createElement('div');
                    noDataMessage.textContent = chartTitle + '：目前無資料';
                    noDataMessage.style.color = 'red';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var sosChartInfo = createChartBox('sosChart', chartTitle, formattedDateRange);
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
                    noDataMessage.style.color = 'red';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var typeChartInfo = createChartBox('sosTypeChart', '求救類型分布', formattedDateRange);
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
                    noDataMessage.style.color = 'red';
                    chartContainer.appendChild(noDataMessage);
                } else {
                    var placeChartInfo = createChartBox('sosPlaceChart', '求救家中地點分布', formattedDateRange);
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
            });
    }

    const apiEndpoints = {
        '/analyze/all_weekly': '/analyze/all_weekly_data',
        '/analyze/all_monthly': '/analyze/all_monthly_data',
        '/analyze/all_yearly': '/analyze/all_yearly_data',
        '/analyze/mem_weekly': '/analyze/mem_weekly_data',
        '/analyze/mem_monthly': '/analyze/mem_monthly_data',
        '/analyze/mem_yearly': '/analyze/mem_yearly_data',
    };

    const currentPath = window.location.pathname;
    const endpoint = apiEndpoints[currentPath];
    const title = '求救次數';

    if (endpoint) {
        fetchData(endpoint, title);
    }
});
