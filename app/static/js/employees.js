(function () {
  const table = document.getElementById('employees-table');
  if (!table) return;

  const companyId = table.dataset.companyId;
  const tbody = table.querySelector('tbody');
  const message = document.getElementById('employees-message');
  const refreshButton = document.getElementById('refresh-employees');

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
  };

  const renderEmployees = (employees) => {
    tbody.innerHTML = '';

    if (!employees.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="ff-empty">No hay empleados para esta empresa.</td></tr>';
      return;
    }

    employees.forEach((employee) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${employee.full_name || '-'}</td>
        <td>${employee.email || '-'}</td>
        <td>${employee.position || '-'}</td>
        <td><span class="ff-tag ${employee.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${employee.status || '-'}</span></td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadEmployees = async () => {
    setMessage('Cargando empleados…');
    try {
      const data = await window.apiFetch(`/companies/${companyId}/employees`);
      renderEmployees(data?.employees || []);
      setMessage('');
    } catch (error) {
      if (error?.noAccess) {
        window.showToast('error', 'No tienes acceso');
      }
      setMessage(error?.data?.message || 'No se pudieron cargar los empleados.', true);
    }
  };

  refreshButton?.addEventListener('click', loadEmployees);
  loadEmployees();
})();
