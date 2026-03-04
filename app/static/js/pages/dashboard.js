(function () {
  const root = document.getElementById('dashboard-page');
  if (!root) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const loading = document.getElementById('dashboard-loading');
  const overdueBody = document.querySelector('#dashboard-overdue-table tbody');
  const overdueEmpty = document.getElementById('overdue-empty');
  const myCasesBody = document.querySelector('#dashboard-my-cases-table tbody');
  const myCasesEmpty = document.getElementById('my-cases-empty');
  const activityList = document.getElementById('dashboard-activity');
  const activityEmpty = document.getElementById('activity-empty');

  const fmtDate = (isoDate) => {
    if (!isoDate) return '-';
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return isoDate;
    return d.toLocaleDateString('es-ES');
  };

  const fmtDateTime = (isoDate) => {
    if (!isoDate) return '-';
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return isoDate;
    return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
  };

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value ?? 0);
  };

  const isOverdue = (isoDate) => {
    if (!isoDate) return false;
    const due = new Date(`${isoDate}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return !Number.isNaN(due.getTime()) && due < today;
  };

  const statusClass = (status) => {
    if (status === 'done') return 'ff-tag--success';
    if (status === 'cancelled') return 'ff-tag--warn';
    if (status === 'open') return 'ff-tag--blue';
    if (status === 'in_progress') return 'ff-tag--blue';
    return 'ff-tag--danger';
  };

  const renderKpis = (kpis) => {
    setText('kpi-active-cases', kpis.active_cases || 0);
    setText('kpi-overdue-cases', kpis.overdue_cases || 0);
    setText('kpi-docs-pending', kpis.docs_pending || 0);
    setText('kpi-docs-no-extraction', kpis.docs_no_extraction || 0);
    setText('kpi-coverage', kpis.extract_coverage_pct || 0);
    setText('kpi-companies-active', kpis.companies_active || 0);
    setText('kpi-companies-open-cases', kpis.companies_with_open_cases || 0);
    setText('kpi-employees-total', kpis.employees_total || 0);
    setText('kpi-my-cases', kpis.my_cases || 0);
    setText('kpi-cases-last-days', `${kpis.cases_created_last_days || 0} en ventana`);
    setText('kpi-docs-last-days', `${kpis.docs_uploaded_last_days || 0} subidos en ventana`);
    setText('kpi-due-today', `${kpis.due_today || 0} vencen hoy`);
  };

  const renderDonut = (labels, values) => {
    const el = document.getElementById('chart-cases-by-status');
    if (!el || !window.ApexCharts) return;
    el.innerHTML = '';
    new ApexCharts(el, {
      chart: { type: 'donut', height: 260, toolbar: { show: false } },
      series: values,
      labels,
      legend: { position: 'bottom' },
      dataLabels: { enabled: false },
    }).render();
  };

  const renderDocsBar = (labels, values) => {
    const el = document.getElementById('chart-docs-by-status');
    if (!el || !window.ApexCharts) return;
    el.innerHTML = '';
    new ApexCharts(el, {
      chart: { type: 'bar', height: 260, toolbar: { show: false } },
      plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
      series: [{ name: 'Documentos', data: values }],
      xaxis: { categories: labels },
      dataLabels: { enabled: false },
    }).render();
  };

  const renderEmployeesBar = (labels, values) => {
    const el = document.getElementById('chart-employees-by-company');
    if (!el || !window.ApexCharts) return;
    el.innerHTML = '';
    new ApexCharts(el, {
      chart: { type: 'bar', height: 260, toolbar: { show: false } },
      plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
      series: [{ name: 'Empleados', data: values }],
      xaxis: { categories: labels },
      dataLabels: { enabled: false },
    }).render();
  };

  const renderRadial = (value) => {
    const el = document.getElementById('chart-extract-coverage');
    if (!el || !window.ApexCharts) return;
    el.innerHTML = '';
    new ApexCharts(el, {
      chart: { type: 'radialBar', height: 260, toolbar: { show: false } },
      series: [value],
      labels: ['Cobertura'],
      plotOptions: { radialBar: { dataLabels: { value: { formatter: (v) => `${Math.round(v)}%` } } } },
    }).render();
  };

  const renderOverdue = (items) => {
    overdueBody.innerHTML = '';
    if (!Array.isArray(items) || !items.length) {
      overdueEmpty.hidden = false;
      return;
    }
    overdueEmpty.hidden = true;
    items.forEach((item) => {
      const tr = document.createElement('tr');
      tr.classList.add('ff-row-overdue');
      const href = `/app/companies/${item.company_id}/cases/${item.case_id}`;
      tr.innerHTML = `
        <td><a href="${href}">${item.title || item.case_id}</a></td>
        <td>${item.company_name || '-'}</td>
        <td><span class="ff-tag ff-tag--danger">${item.status || '-'}</span></td>
        <td>${fmtDate(item.due_date)}</td>
        <td>${item.responsible_email || '-'}</td>
      `;
      overdueBody.appendChild(tr);
    });
  };

  const renderMyCases = (items) => {
    myCasesBody.innerHTML = '';
    if (!Array.isArray(items) || !items.length) {
      myCasesEmpty.hidden = false;
      return;
    }
    myCasesEmpty.hidden = true;
    items.forEach((item) => {
      const tr = document.createElement('tr');
      const href = `/app/companies/${item.company_id}/cases/${item.case_id}`;
      const dueLabel = fmtDate(item.due_date);
      tr.innerHTML = `
        <td><a href="${href}">${item.title || item.case_id}</a></td>
        <td>${item.company_name || '-'}</td>
        <td><span class="ff-tag ${statusClass(item.status)}">${item.status || '-'}</span></td>
        <td ${isOverdue(item.due_date) ? 'style="color:var(--ff-danger,#c22c4a);font-weight:600"' : ''}>${dueLabel}</td>
      `;
      myCasesBody.appendChild(tr);
    });
  };

  const renderActivity = (items) => {
    activityList.innerHTML = '';
    if (!Array.isArray(items) || !items.length) {
      activityEmpty.hidden = false;
      return;
    }
    activityEmpty.hidden = true;

    items.forEach((item) => {
      const li = document.createElement('li');
      li.classList.add('ff-timeline__item');
      const href = item.case_id
        ? `/app/companies/${item.company_id}/cases/${item.case_id}`
        : item.document_id
          ? `/app/documents`
          : null;
      const icon = item.document_id ? '📄' : item.case_id ? '📌' : '📝';
      li.innerHTML = `
        <div class="ff-timeline__meta"><span>${icon}</span><span>${item.kind || 'actividad'}</span></div>
        <div>${href ? `<a href="${href}">${item.title || '-'}</a>` : item.title || '-'}</div>
        <small class="ff-muted">${item.company_name || '-'} · ${fmtDateTime(item.ts)}</small>
      `;
      activityList.appendChild(li);
    });
  };

  const loadDashboard = async () => {
    try {
      const data = await window.apiFetch('/dashboard/summary?days=14&overdue_limit=8&activity_limit=12&my_cases_limit=5');
      renderKpis(data?.kpis || {});
      renderDonut(data?.cases_by_status?.labels || [], data?.cases_by_status?.values || []);
      renderDocsBar(data?.docs_by_status?.labels || [], data?.docs_by_status?.values || []);
      renderEmployeesBar(data?.employees_by_company?.labels || [], data?.employees_by_company?.values || []);
      renderRadial(data?.kpis?.extract_coverage_pct || 0);
      renderOverdue(data?.overdue_cases || []);
      renderMyCases(data?.my_cases_list || []);
      renderActivity(data?.activity || []);
      if (loading) loading.hidden = true;
    } catch (err) {
      window.handleApiError(err, { defaultMessage: 'No se pudo cargar el dashboard' });
      if (err?.status === 400 && err?.data?.error?.code === 'tenant_context_required') {
        window.location.href = '/app/platform/tenants';
        return;
      }
      if (loading) loading.textContent = 'No se pudo cargar el dashboard.';
    }
  };

  loadDashboard();
})();
