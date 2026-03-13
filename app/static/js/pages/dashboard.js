(() => {
  const root = document.getElementById('dashboard-page');
  if (!root || !window.apiFetch) return;

  const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('es-ES') : '-');
  const fmtDateTime = (value) => (value ? new Date(value).toLocaleString('es-ES') : '-');
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value ?? 0);
  };

  const renderTable = (bodyId, emptyId, rows, rowRenderer) => {
    const body = document.getElementById(bodyId);
    const empty = document.getElementById(emptyId);
    if (!body) return;
    body.innerHTML = '';
    if (!Array.isArray(rows) || !rows.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    rows.forEach((row) => body.appendChild(rowRenderer(row)));
  };

  const tr = (html) => {
    const row = document.createElement('tr');
    row.innerHTML = html;
    return row;
  };

  const renderKpis = (kpis) => {
    setText('kpi-persons-total', kpis.persons_total);
    setText('kpi-persons-active', kpis.persons_active);
    setText('kpi-persons-incomplete', kpis.persons_incomplete);
    setText('kpi-requests-pending', kpis.requests_pending);
    setText('kpi-requests-overdue', kpis.requests_overdue);
    setText('kpi-requests-sent-today', kpis.requests_submitted_today);
    setText('kpi-documents-today', kpis.documents_today);
    setText('kpi-documents-pending', kpis.documents_pending_processing);
    setText('kpi-cases-open', kpis.cases_open);
    setText('kpi-cases-overdue', kpis.cases_overdue);
  };

  const loadDashboard = async () => {
    try {
      const data = await window.apiFetch('/dashboard/tenant');
      renderKpis(data.kpis || {});

      renderTable('attention-persons-body', 'attention-persons-empty', data.attention_persons, (item) => tr(`
        <td>${item.person_name || '-'}</td>
        <td>${item.company_name || '-'}</td>
        <td><span class="ff-tag">${item.onboarding_status || '-'}</span></td>
        <td>${item.pending_requests || 0}</td>
        <td>${fmtDateTime(item.last_activity)}</td>
        <td><a href="/app/persons/${item.person_id}">Ver persona</a></td>
      `));

      renderTable('pending-requests-body', 'pending-requests-empty', data.pending_requests, (item) => tr(`
        <td><a href="/app/persons/${item.person_id}">${item.person_name || '-'}</a></td>
        <td>${item.company_name || '-'}</td>
        <td>${item.request_type || '-'}</td>
        <td>${item.status || '-'}</td>
        <td>${fmtDate(item.due_date)}</td>
        <td><a href="/app/persons/${item.person_id}/requests">Abrir</a></td>
      `));

      renderTable('recent-activity-body', 'recent-activity-empty', data.recent_activity, (item) => tr(`
        <td>${fmtDateTime(item.date)}</td>
        <td>${item.person_name || '-'}</td>
        <td>${item.action || '-'}</td>
        <td>${item.entity || '-'}</td>
      `));

      renderTable('recent-documents-body', 'recent-documents-empty', data.recent_documents, (item) => tr(`
        <td>${item.person_name || '-'}</td>
        <td>${item.company_name || '-'}</td>
        <td>${item.document_type || '-'}</td>
        <td>${fmtDateTime(item.uploaded_at)}</td>
        <td>${item.status || '-'}</td>
        <td><a href="/app/documents">Ver documento</a></td>
      `));

      renderTable('cases-attention-body', 'cases-attention-empty', data.cases_attention, (item) => tr(`
        <td>${item.company_name || '-'}</td>
        <td>${item.person_name || '-'}</td>
        <td><a href="/app/cases/${item.case_id}">${item.title || '-'}</a></td>
        <td>${item.status || '-'}</td>
        <td>${fmtDate(item.due_date)}</td>
      `));

      const loading = document.getElementById('dashboard-loading');
      if (loading) loading.hidden = true;
    } catch (err) {
      window.handleApiError?.(err, { defaultMessage: 'No se pudo cargar el dashboard' });
    }
  };

  loadDashboard();
})();
