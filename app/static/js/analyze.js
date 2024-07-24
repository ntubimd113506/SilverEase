document.addEventListener('DOMContentLoaded', function () {
    var chartContainer = document.getElementById('chartContainer');

    function createChartBox(id, title) {
        var div = document.createElement('div');
        div.className = 'chart-box';
        div.style.border = '1px solid #000';
        div.style.padding = '10px';
        div.style.margin = '10px 0';

        var h2 = document.createElement('h2');
        h2.textContent = title;
        div.appendChild(h2);

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
        return { ctx: canvas.getContext('2d'), select: select };
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

    function fetchData(url, chartTitle) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // SOS Chart
                var sosData = data.SOSdata.map(item => item[1]);
                var sosLabels = data.SOSdata.map(item => item[0]);

                var sosChartInfo = createChartBox('sosChart', chartTitle + ' (長條圖/折線圖)');
                var SOS = setupChart(sosChartInfo, '求救次數', { labels: sosLabels, values: sosData }, 'rgba(255, 38, 38, 0.8)', 'rgba(255, 38, 38, 0.8)');
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

                var typeLabels = data.SOSTypedata.map(item => item[0]);
                var typeData = data.SOSTypedata.map(item => item[1]);

                var typeChartInfo = createChartBox('sosTypeChart', '求救類型分布（圓餅圖）');
                typeChartInfo.select.style.display = 'none';

                var SOSType = {
                    labels: typeLabels,
                    datasets: [{
                        data: typeData,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(153, 102, 255, 0.2)',
                            'rgba(255, 159, 64, 0.2)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                            'rgba(255, 159, 64, 1)'
                        ],
                        borderWidth: 1
                    }]
                };

                createChart(typeChartInfo, 'pie', SOSType);
            });
    }

    if (window.location.pathname === '/analyze/all_weekly') {
        fetchData('/analyze/all_weekly_data', '求救次數（所有成員）');
    } else {
        fetchData('/analyze/mem_weekly_data', '求救次數');
    }
});
