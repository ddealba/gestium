(function () {
  const table = document.getElementById('companies-table');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  const message = document.getElementById('companies-message');
  const refreshButton = document.getElementById('refresh-companies');

  const aclSection = document.getElementById('company-access-panel');
  const aclTitle = document.getElementById('company-access-title');
  const aclMessage = document.getElementById('company-access-message');
  const aclTableBody = document.querySelector('#company-access-table tbody');
  const aclForm = document.getElementById('company-access-form');
  const aclUserId = document.getElementById('acl-user-id');
  const aclLevel = document.getElementById('acl-level');

  let selectedCompanyId = null;

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
  };

  const setAclMessage = (text, isError = false) => {
    if (!aclMessage) return;
    aclMessage.textContent = text;
    aclMessage.classList.toggle('is-error', isError);
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
      const data = await window.apiFetch('/admin/companies');
      renderCompanies(data?.items || []);
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

  refreshButton?.addEventListener('click', loadCompanies);
  loadCompanies();
})();
