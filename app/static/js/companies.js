(function () {
  const table = document.getElementById('companies-table');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  const message = document.getElementById('companies-message');
  const refreshButton = document.getElementById('refresh-companies');

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
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
        </td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadCompanies = async () => {
    setMessage('Cargando empresas…');
    try {
      const data = await window.apiFetch('/companies');
      renderCompanies(data?.companies || []);
      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar las empresas.' });
      setMessage('No se pudieron cargar las empresas.', true);
    }
  };

  refreshButton?.addEventListener('click', loadCompanies);
  loadCompanies();
})();
