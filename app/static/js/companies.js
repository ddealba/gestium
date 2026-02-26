(function () {
  const table = document.getElementById('companies-table');
  if (!table) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const tbody = table.querySelector('tbody');
  const message = document.getElementById('companies-message');
  const refreshButton = document.getElementById('refresh-companies');
  const qInput = document.getElementById('companies-q');
  const statusFilter = document.getElementById('companies-status');
  const orderFilter = document.getElementById('companies-order');
  const applyFiltersButton = document.getElementById('companies-apply-filters');
  const clearFiltersButton = document.getElementById('companies-clear-filters');
  const prevButton = document.getElementById('companies-prev');
  const nextButton = document.getElementById('companies-next');

  const aclSection = document.getElementById('company-access-panel');
  const aclTitle = document.getElementById('company-access-title');
  const aclMessage = document.getElementById('company-access-message');
  const aclTableBody = document.querySelector('#company-access-table tbody');
  const aclForm = document.getElementById('company-access-form');
  const aclUserId = document.getElementById('acl-user-id');
  const aclLevel = document.getElementById('acl-level');

  let selectedCompanyId = null;
  const state = { limit: 20, offset: 0, total: 0 };

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
  };

  const setAclMessage = (text, isError = false) => {
    if (!aclMessage) return;
    aclMessage.textContent = text;
    aclMessage.classList.toggle('is-error', isError);
  };

  const updatePaginationButtons = () => {
    if (prevButton) prevButton.disabled = state.offset <= 0;
    if (nextButton) nextButton.disabled = state.offset + state.limit >= state.total;
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    const q = qInput?.value?.trim();
    const status = statusFilter?.value || 'all';
    const [sort, order] = (orderFilter?.value || 'created_at:desc').split(':');

    if (q) params.set('q', q);
    if (status !== 'all') params.set('status', status);
    params.set('sort', sort);
    params.set('order', order);
    params.set('limit', String(state.limit));
    params.set('offset', String(state.offset));
    return params.toString();
  };

  const renderAccessRows = (items) => {
    aclTableBody.innerHTML = '';
    if (!items.length) {
      aclTableBody.innerHTML = '<tr><td colspan="4" class="ff-empty">Sin accesos asignados.</td></tr>';
      return;
    }

    items.forEach((entry) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${entry.email || '-'}</td>
        <td><code>${entry.user_id}</code></td>
        <td>${entry.access_level}</td>
        <td>
          <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="remove-access" data-user-id="${entry.user_id}">Quitar</button>
        </td>
      `;
      aclTableBody.appendChild(row);
    });
  };

  const loadAccess = async (companyId, companyName) => {
    selectedCompanyId = companyId;
    aclSection.hidden = false;
    aclTitle.textContent = `Accesos · ${companyName}`;
    setAclMessage('Cargando accesos…');
    try {
      const data = await window.apiFetch(`/admin/companies/${companyId}/access`);
      renderAccessRows(data?.items || []);
      setAclMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los accesos.' });
      setAclMessage('No se pudieron cargar los accesos.', true);
    }
  };

  const renderCompanies = (companies) => {
    tbody.innerHTML = '';

    if (!companies.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="ff-empty">No hay empresas disponibles.</td></tr>';
      return;
    }

    companies.forEach((company) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${company.name || '-'}</td>
        <td>${company.tax_id || '-'}</td>
        <td><span class="ff-tag ${company.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${company.status || '-'}</span></td>
        <td>
          <a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/companies/${company.id}/cases">Cases</a>
          <a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/companies/${company.id}/employees">Ver empleados</a>
          <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="manage-access" data-company-id="${company.id}" data-company-name="${company.name || '-'}">Gestionar accesos</button>
        </td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadCompanies = async () => {
    setMessage('Cargando empresas…');
    try {
      const data = await window.apiFetch(`/companies?${buildQuery()}`);
      renderCompanies(data?.items || []);
      state.total = data?.total || 0;
      state.limit = data?.limit || state.limit;
      state.offset = data?.offset ?? state.offset;
      updatePaginationButtons();
      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar las empresas.' });
      setMessage('No se pudieron cargar las empresas.', true);
    }
  };

  tbody.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action="manage-access"]');
    if (!button) return;
    loadAccess(button.dataset.companyId, button.dataset.companyName || 'Empresa');
  });

  aclTableBody?.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-action="remove-access"]');
    if (!button || !selectedCompanyId) return;
    try {
      await window.apiFetch(`/admin/companies/${selectedCompanyId}/access/${button.dataset.userId}`, {
        method: 'DELETE',
      });
      await loadAccess(selectedCompanyId, aclTitle.textContent.replace('Accesos · ', ''));
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo quitar el acceso.' });
      setAclMessage('No se pudo quitar el acceso.', true);
    }
  });

  aclForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selectedCompanyId) return;
    setAclMessage('Guardando acceso…');
    try {
      await window.apiFetch(`/admin/companies/${selectedCompanyId}/access`, {
        method: 'POST',
        body: JSON.stringify({ user_id: aclUserId.value, access_level: aclLevel.value }),
      });
      aclUserId.value = '';
      await loadAccess(selectedCompanyId, aclTitle.textContent.replace('Accesos · ', ''));
      setAclMessage('Acceso actualizado.');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo guardar el acceso.' });
      setAclMessage('No se pudo guardar el acceso.', true);
    }
  });

  applyFiltersButton?.addEventListener('click', () => {
    state.offset = 0;
    loadCompanies();
  });

  clearFiltersButton?.addEventListener('click', () => {
    if (qInput) qInput.value = '';
    if (statusFilter) statusFilter.value = 'all';
    if (orderFilter) orderFilter.value = 'created_at:desc';
    state.offset = 0;
    loadCompanies();
  });

  prevButton?.addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadCompanies();
  });

  nextButton?.addEventListener('click', () => {
    state.offset += state.limit;
    loadCompanies();
  });

  refreshButton?.addEventListener('click', loadCompanies);
  loadCompanies();
})();
