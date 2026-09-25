const API_BASE = '/api/v1';
const ADMIN_API_BASE = '/api/admin';

function apiUrl(base, path) {
  const cleanBase = String(base).replace(/\/+$/, '');
  const cleanPath = String(path || '').replace(/^\/+/, '');
  return `${cleanBase}/${cleanPath}`;
}

function storedAuthToken() {
  try {
    return window.localStorage.getItem('auth_token') || window.localStorage.getItem('access_token') || '';
  } catch (_) {
    return '';
  }
}

async function requestFrom(base, path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const token = storedAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response;
  try {
    response = await fetch(apiUrl(base, path), {
      ...options,
      headers,
      credentials: 'same-origin'
    });
  } catch (_) {
    throw new Error('تعذر الاتصال بالخادم');
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`;
    throw new Error(`تعذر الاتصال بالخادم: ${detail}`);
  }
  return data;
}

function adminRequest(path, options = {}) {
  return requestFrom(ADMIN_API_BASE, path, options);
}

function showMessage(message, type = 'info') {
  const box = document.getElementById('message');
  if (!box) return;
  box.className = `alert alert-${type}`;
  box.textContent = message;
  box.classList.remove('d-none');
}

function money(value) {
  return Number(value || 0).toLocaleString('ar-EG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function statusBadge(status, label) {
  const classes = {active: 'badge-soft-success', expired: 'badge-soft-warning', blocked: 'badge-soft-danger'};
  return `<span class="badge ${classes[status] || 'badge-soft-secondary'}">${escapeHtml(label || status || 'غير معروف')}</span>`;
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? escapeHtml(value) : date.toLocaleDateString('ar-EG');
}

function renderError(error) {
  showMessage(error.message || 'تعذر تحميل البيانات', 'danger');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal && window.bootstrap) {
    window.bootstrap.Modal.getOrCreateInstance(modal).hide();
  }
}

document.addEventListener('DOMContentLoaded', async function () {
  try {
    const subscriptionRows = document.getElementById('subscriptionRows');
    if (subscriptionRows) {
      const data = await adminRequest('subscriptions');
      const planSelect = document.getElementById('planId');
      (data.plans || []).forEach((plan) => {
        planSelect.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(plan.id)}">${escapeHtml(plan.name)}</option>`);
      });
      subscriptionRows.innerHTML = (data.items || []).length ? data.items.map((item) => `
        <tr><td>${escapeHtml(item.store_id)}</td><td>${escapeHtml(item.store_name)}</td><td>${escapeHtml(item.owner_name)}</td><td>${escapeHtml(item.plan_name || '-')}</td><td>${formatDate(item.subscription_end)}</td><td>${statusBadge(item.status, item.status_label)}</td></tr>`).join('') : '<tr><td colspan="6" class="text-center text-secondary py-5">لا توجد اشتراكات</td></tr>';
    }

    const plansGrid = document.getElementById('plansGrid');
    if (plansGrid) {
      const data = await adminRequest('plans');
      plansGrid.innerHTML = (data.items || []).map((plan) => `
        <div class="col-md-6 col-xl-4"><div class="card plan-card rounded-3 p-4 h-100"><h2 class="h4 fw-bold">${escapeHtml(plan.name)}</h2><div class="display-6 fw-bold mt-3">${money(plan.monthly_price)} <small class="fs-6 text-secondary">ج.م / شهر</small></div><div class="text-secondary">${money(plan.annual_price)} ج.م / سنة</div><ul class="list-unstyled mt-3">${(plan.features_list || []).map((feature) => `<li class="mb-2">✅ ${escapeHtml(feature)}</li>`).join('')}</ul></div></div>`).join('') || '<div class="col-12 text-center text-secondary">لا توجد خطط</div>';
    }

    const userRows = document.getElementById('userRows');
    if (userRows) {
      const data = await adminRequest('users');
      userRows.innerHTML = (data.items || []).length ? data.items.map((user) => `<tr><td>${escapeHtml(user.name)}</td><td>${escapeHtml(user.email)}</td><td>${escapeHtml(user.role)}</td><td>${formatDate(user.created_at)}</td></tr>`).join('') : '<tr><td colspan="4" class="text-center text-secondary py-5">لا يوجد مستخدمون</td></tr>';
      document.getElementById('loginRows').innerHTML = (data.history || []).map((entry) => `<tr><td>${escapeHtml(entry.user_name)}</td><td>${escapeHtml(entry.ip_address)}</td><td>${formatDate(entry.logged_at)}</td><td>${escapeHtml(entry.status)}</td></tr>`).join('') || '<tr><td colspan="4" class="text-center text-secondary py-4">لا يوجد سجل دخول</td></tr>';
    }
  } catch (error) {
    renderError(error);
  }

  const subscriptionForm = document.getElementById('subscriptionForm');
  if (subscriptionForm) subscriptionForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      await adminRequest('subscriptions', {method: 'POST', body: JSON.stringify({store_name: document.getElementById('storeName').value, owner_name: document.getElementById('ownerName').value, phone: document.getElementById('phone').value, plan_id: Number(document.getElementById('planId').value), days: 30})});
      closeModal('addModal'); window.location.reload();
    } catch (error) { renderError(error); }
  });

  const planForm = document.getElementById('planForm');
  if (planForm) planForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    try { await adminRequest('plans', {method: 'POST', body: JSON.stringify({name: document.getElementById('planName').value, monthly_price: Number(document.getElementById('monthlyPrice').value), annual_price: Number(document.getElementById('annualPrice').value), features: []})}); closeModal('planModal'); window.location.reload(); } catch (error) { renderError(error); }
  });

  const userForm = document.getElementById('userForm');
  if (userForm) userForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    try { await adminRequest('users', {method: 'POST', body: JSON.stringify({name: document.getElementById('userName').value, email: document.getElementById('userEmail').value, role: document.getElementById('userRole').value, permissions: []})}); closeModal('userModal'); window.location.reload(); } catch (error) { renderError(error); }
  });
});
