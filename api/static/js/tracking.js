document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('severityChart');
  const chartData = window.dashboardChart;

  if (!canvas || typeof Chart === 'undefined' || !chartData) {
    return;
  }

  const labels = Array.isArray(chartData.labels) ? chartData.labels : [];
  const values = Array.isArray(chartData.values) ? chartData.values : [];

  if (labels.length === 0 || values.length === 0) {
    return;
  }

  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Severity',
          data: values,
          borderColor: '#b77868',
          backgroundColor: 'rgba(227, 213, 202, 0.38)',
          pointBackgroundColor: '#2d2424',
          pointBorderColor: '#fdfcfb',
          pointBorderWidth: 2,
          pointRadius: 4.5,
          fill: true,
          tension: 0.38,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(109, 90, 86, 0.10)',
            drawBorder: false,
          },
          ticks: {
            stepSize: 20,
            color: 'rgba(45, 36, 36, 0.58)',
          },
        },
        x: {
          grid: {
            display: false,
            drawBorder: false,
          },
          ticks: {
            color: 'rgba(45, 36, 36, 0.58)',
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
      },
    },
  });
});

