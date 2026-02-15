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

  const getAuthHeaders = () => {
    const token = localStorage.getItem('gestium_access_token');
    if (!token) return null;
    return { Authorization: `Bearer ${token}` };
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
          <a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/companies/${company.id}/employees">Ver empleados</a>
        </td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadCompanies = async () => {
    const headers = getAuthHeaders();
    if (!headers) {
      setMessage('Debes iniciar sesión para consultar empresas.', true);
      return;
    }

    setMessage('Cargando empresas…');
    try {
      const response = await fetch('/companies', { headers });
      const data = await response.json();

      if (!response.ok) {
        setMessage('No se pudieron cargar las empresas.', true);
        return;
      }

      renderCompanies(data.companies || []);
      setMessage('');
    } catch (error) {
      setMessage('Error de red al consultar empresas.', true);
    }
  };

  refreshButton?.addEventListener('click', loadCompanies);
  loadCompanies();
})();
