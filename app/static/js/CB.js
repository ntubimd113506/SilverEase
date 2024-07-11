document.addEventListener('DOMContentLoaded', function() {
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

        var canvas = document.createElement('canvas');
        canvas.id = id;
        canvas.width = 100;
        canvas.height = 50;
        div.appendChild(canvas);

        chartContainer.appendChild(div);
        return canvas.getContext('2d');
    }

    fetch('/all_weekly')
        .then(response => response.json())
        .then(data => {
            var sosData = data.sos_data.map(item => item[1]); // item[1] 對應 CountPerWeek
            var memoData = data.memo_data.map(item => item[1]); // item[1] 對應 CountPerWeek
            var labels = data.sos_data.map(item => item[0]); // item[0] 對應 CreateDate

            var ctx1 = createChartBox('myChart1', '圓餅圖');
            var pieData = {
                labels: labels,
                datasets: [{
                    data: sosData,
                    backgroundColor: [
                        'rgba(255, 99, 132)',
                        'rgba(54, 162, 235)',
                        'rgba(255, 206, 86)',
                        'rgba(75, 192, 192)',
                        'rgba(153, 102, 255)',
                        'rgba(255, 159, 64)'
                    ],
                    borderWidth: 1
                }]
            };
            var myPieChart = new Chart(ctx1, {
                type: 'pie',
                data: pieData,
                options: {}
            });

            var ctx2 = createChartBox('myChart2', '折線圖');
            var lineData = {
                labels: labels,
                datasets: [{
                    label: 'SOS 數量',
                    data: sosData,
                    fill: false,
                    backgroundColor: 'rgba(212, 106, 106, 1)',
                    borderColor: 'rgba(212, 106, 106, 1)'
                }, {
                    label: 'Memo 數量',
                    data: memoData,
                    fill: false,
                    backgroundColor: 'rgba(128, 21, 21, 1)',            
                    borderColor: 'rgba(128, 21, 21, 1)'
                }]
            };
            var myLineChart = new Chart(ctx2, {
                type: 'line',
                data: lineData,
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        });
});
