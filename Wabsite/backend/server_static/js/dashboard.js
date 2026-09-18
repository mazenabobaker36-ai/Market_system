document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('salesChart');
  if (!canvas || typeof Chart === 'undefined') return;

  let labels = [];
  let values = [];
  try {
    labels = JSON.parse(canvas.dataset.labels || '[]');
    values = JSON.parse(canvas.dataset.values || '[]');
  } catch (error) {
    console.error('تعذر قراءة بيانات الرسم البياني', error);
  }

  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'المبيعات',
        data: values,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,.12)',
        fill: true,
        tension: .35
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true } },
      scales: { y: { beginAtZero: true } }
    }
  });
});
