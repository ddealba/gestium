(() => {
  const root = document.getElementById('dashboard-page');
  if (!root || !window.apiFetch) return;

  const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('es-ES') : '-');
  const fmtDateTime = (value) => (value ? new Date(value).toLocaleString('es-ES') : '-');
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value ?? 0);
  };

  const asTag = (value, variant = '') => `<span class="ff-tag${variant ? ` ff-tag--${variant}` : ''}">${value || '-'}</span>`;

  const renderTable = (bodyId, emptyId, rows, rowRenderer, maxRows = 5) => {
    const body = document.getElementById(bodyId);
    const empty = document.getElementById(emptyId);
    if (!body) return;
    body.innerHTML = '';
    const visibleRows = Array.isArray(rows) ? rows.slice(0, maxRows) : [];
    if (!visibleRows.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    visibleRows.forEach((row) => body.appendChild(rowRenderer(row)));
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
        <td>${asTag(item.onboarding_status || '-', item.onboarding_status === 'incomplete' ? 'warn' : 'success')}</td>
        <td>${item.pending_requests || 0}</td>
        <td><a href="/app/persons/${item.person_id}">Ver</a></td>
      `));

      renderTable('pending-requests-body', 'pending-requests-empty', data.pending_requests, (item) => tr(`
        <td><a href="/app/persons/${item.person_id}">${item.person_name || '-'}</a></td>
        <td>${item.request_type || '-'}</td>
        <td>${fmtDate(item.due_date)}</td>
        <td><a href="/app/persons/${item.person_id}/requests">Abrir</a></td>
      `));

      renderTable('recent-activity-body', 'recent-activity-empty', data.recent_activity, (item) => tr(`
        <td>${fmtDateTime(item.date)}</td>
        <td><strong>${item.person_name || '-'}</strong><br><span class="ff-muted">${item.action || '-'} · ${item.entity || '-'}</span></td>
      `));

      renderTable('recent-documents-body', 'recent-documents-empty', data.recent_documents, (item) => tr(`
        <td><strong>${item.person_name || '-'}</strong><br><span class="ff-muted">${item.company_name || '-'}</span></td>
        <td>${item.document_type || '-'}</td>
        <td>${asTag(item.status || '-')}</td>
      `));

      renderTable('cases-attention-body', 'cases-attention-empty', data.cases_attention, (item) => tr(`
        <td>${item.company_name || '-'}</td>
        <td><a href="/app/cases/${item.case_id}">${item.title || '-'}</a></td>
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
