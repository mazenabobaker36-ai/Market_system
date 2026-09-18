document.addEventListener('DOMContentLoaded', async function () {
  const canvas = document.getElementById('salesChart');
  let chart;

  if (canvas && typeof Chart !== 'undefined') {
    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'المبيعات',
          data: [],
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.12)',
          fill: true,
          tension: 0.35
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {y: {beginAtZero: true}}
      }
    });
  }

  try {
    const data = await adminRequest('dashboard');
    const metrics = data.metrics || {};
    const metricMap = {
      revenue: money(metrics.revenue),
      active: metrics.active || 0,
      expiring: metrics.expiring || 0,
      suspended: metrics.suspended || 0
    };
    Object.entries(metricMap).forEach(([key, value]) => {
      const element = document.querySelector(`[data-metric="${key}"]`);
      if (element) element.textContent = value;
    });

    if (chart) {
      chart.data.labels = data.chart_labels || [];
      chart.data.datasets[0].data = data.chart_values || [];
      chart.update();
    }

    const body = document.getElementById('telemetryRows');
    if (body) {
      const rows = data.telemetry || [];
      body.innerHTML = rows.length ? rows.map((row) => `
        <tr>
          <td>${escapeHtml(row.store_id)}</td>
          <td>${formatDate(row.received_at)}</td>
          <td>${money(row.total_daily_sales)}</td>
          <td>${escapeHtml(row.app_status)}</td>
        </tr>`).join('') : '<tr><td colspan="4" class="text-center text-secondary py-4">لا توجد دفعات مزامنة</td></tr>';
    }
  } catch (error) {
    renderError(error);
  }
});
