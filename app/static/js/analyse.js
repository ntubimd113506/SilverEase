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

    function fetchData(url, chartTitle) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                var sosData = data.SOSdata.map(item => item[1]);
                var labels = data.SOSdata.map(item => item[0]);

                function setupChart(chartInfo, label, data, bgColor, borderColor) {
                    return {
                        labels: labels,
                        datasets: [{
                            label: label,
                            data: data,
                            fill: false,
                            backgroundColor: bgColor,
                            borderColor: borderColor
                        }]
                    };
                }

                var chartInfo = createChartBox('myChart', chartTitle);
                var SOS = setupChart(chartInfo, '求救', sosData, 'rgba(255, 38, 38, 0.8)', 'rgba(255, 38, 38, 0.8)');
                var chart = createChart(chartInfo, 'bar', SOS, {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                });

                chartInfo.select.addEventListener('change', function () {
                    chart.destroy();
                    chart = createChart(chartInfo, this.value, SOS, {
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    });
                });
            });
    }

    if (window.location.pathname === '/analyse/all_weekly') {
        fetchData('/analyse/all_weekly_data', '求救次數(所有成員)');
    } else {
        fetchData('/analyse/mem_weekly_data', '求救次數');
    }
});
