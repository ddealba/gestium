(function () {
  const table = document.getElementById('audit-table');
  if (!table) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const tbody = table.querySelector('tbody');
  const filter = document.getElementById('audit-entity-type-filter');
  const message = document.getElementById('audit-message');

  const setMessage = (text, isError = false) => {
    if (!message) return;
    message.textContent = text || '';
    message.classList.toggle('is-error', Boolean(isError && text));
    message.classList.toggle('is-success', Boolean(!isError && text));
  };

  const renderRows = (items) => {
    tbody.innerHTML = '';
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="ff-empty">Sin registros.</td></tr>';
      return;
    }

    items.forEach((item) => {
      const row = document.createElement('tr');
      const dateCell = document.createElement('td');
      const userCell = document.createElement('td');
      const actionCell = document.createElement('td');
      const entityCell = document.createElement('td');

      dateCell.textContent = item.created_at ? new Date(item.created_at).toLocaleString() : '-';
      userCell.textContent = item.actor_email || item.actor_user_id || 'system';
      actionCell.textContent = item.action || '-';
      entityCell.textContent = `${item.entity_type || '-'}:${item.entity_id || '-'}`;

      row.append(dateCell, userCell, actionCell, entityCell);
      tbody.appendChild(row);
    });
  };

  const loadAudit = async () => {
    const params = new URLSearchParams({ limit: '100', offset: '0' });
    if (filter?.value) params.set('entity_type', filter.value);

    setMessage('Cargando auditoría...');
    try {
      const response = await window.apiFetch(`/admin/audit?${params.toString()}`);
      renderRows(response?.items || []);
      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo cargar la auditoría.' });
      setMessage('No se pudo cargar la auditoría.', true);
      renderRows([]);
    }
  };

  filter?.addEventListener('change', loadAudit);
  loadAudit();
})();
