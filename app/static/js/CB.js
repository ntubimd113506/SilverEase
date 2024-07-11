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

    fetch('/analyze/all_data')
        .then(response => response.json())
        .then(data => {
            var endpoints = data.endpoints;
            fetch(endpoints.abc)
                .then(response => response.json())
                .then(data => {
                    var sosData = data.sos_data.map(item => item[1]);
                    var memoData = data.memo_data.map(item => item[1]);
                    var labels = data.sos_data.map(item => item[0]);
                    var respondData = data.respond_data;

                    var chartInfo1 = createChartBox('myChart1', '求救次數');
                    var SOS = {
                        labels: labels,
                        datasets: [{
                            label: '求救',
                            data: sosData,
                            fill: false,
                            backgroundColor: 'rgba(255, 38, 38, 0.8)',
                            borderColor: 'rgba(255, 38, 38, 0.8)'
                        }]
                    };
                    var chart1 = createChart(chartInfo1, 'bar', SOS, {
                        scales: {
                            y: {
                                beginAtZero: true
                                
                            }
                        }
                    });

                    var chartInfo2 = createChartBox('myChart2', '新增次數');
                    var Memo = {
                        labels: labels,
                        datasets: [{
                            label: '新增',
                            data: memoData,
                            fill: false,
                            backgroundColor: 'rgba(38, 97, 255, 0.8)',
                            borderColor: 'rgba(38, 97, 255, 0.8)'
                        }]
                    };
                    var chart2 = createChart(chartInfo2, 'bar', Memo, {
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    });

                    var chartInfo3 = createChartBox('myChart3', '回應次數');
                    var Respond = {
                        labels: labels,
                        datasets: [{
                            label: '沒回應',
                            data: respondData.map(item => item[1]),
                            fill: false,
                            backgroundColor: 'rgba(255, 99, 132, 0.8)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }, {
                            label: '1次內',
                            data: respondData.map(item => item[2]),
                            fill: false,
                            backgroundColor: 'rgba(54, 162, 235, 0.8)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }, {
                            label: '2次內',
                            data: respondData.map(item => item[3]),
                            fill: false,
                            backgroundColor: 'rgba(255, 206, 86, 0.8)',
                            borderColor: 'rgba(255, 206, 86, 1)',
                            borderWidth: 1
                        }, {
                            label: '3次內',
                            data: respondData.map(item => item[4]),
                            fill: false,
                            backgroundColor: 'rgba(75, 192, 192, 0.8)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    };
                    var chart3 = createChart(chartInfo3, 'bar', Respond, {
                        scales: {
                            x: {
                                stacked: true
                            },
                            y: {
                                stacked: true,
                                beginAtZero: true
                            }
                        }
                    });

                    chartInfo1.select.addEventListener('change', function () {
                        chart1.destroy();
                        chart1 = createChart(chartInfo1, this.value, SOS, {
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        });
                    });

                    chartInfo2.select.addEventListener('change', function () {
                        chart2.destroy();
                        chart2 = createChart(chartInfo2, this.value, Memo, {
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        });
                    });

                    chartInfo3.select.addEventListener('change', function () {
                        chart3.destroy();
                        chart3 = createChart(chartInfo3, this.value, Respond, {
                            scales: {
                                x: {
                                    stacked: true
                                },
                                y: {
                                    stacked: true,
                                    beginAtZero: true
                                }
                            }
                        });
                    });
                });
        });
});
