(function () {
  const table = document.getElementById('employees-table');
  if (!table) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const companyId = table.dataset.companyId;
  const tbody = table.querySelector('tbody');
  const message = document.getElementById('employees-message');
  const refreshButton = document.getElementById('refresh-employees');
  const qInput = document.getElementById('employees-q');
  const statusFilter = document.getElementById('employees-status');
  const orderFilter = document.getElementById('employees-order');
  const applyFiltersButton = document.getElementById('employees-apply-filters');
  const clearFiltersButton = document.getElementById('employees-clear-filters');
  const prevButton = document.getElementById('employees-prev');
  const nextButton = document.getElementById('employees-next');

  const state = { limit: 20, offset: 0, total: 0 };

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
  };

  const updatePaginationButtons = () => {
    if (prevButton) prevButton.disabled = state.offset <= 0;
    if (nextButton) nextButton.disabled = state.offset + state.limit >= state.total;
  };

  const formatDate = (value) => value || '-';

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
        <td>${employee.employee_ref || '-'}</td>
        <td>${formatDate(employee.start_date)}</td>
        <td><span class="ff-tag ${employee.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${employee.status || '-'}</span></td>
      `;
      tbody.appendChild(row);
    });
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    const q = qInput?.value?.trim();
    const status = statusFilter?.value || 'all';
    const [sort, order] = (orderFilter?.value || 'name:asc').split(':');

    if (q) params.set('q', q);
    if (status !== 'all') params.set('status', status);
    params.set('sort', sort);
    params.set('order', order);
    params.set('limit', String(state.limit));
    params.set('offset', String(state.offset));
    return params.toString();
  };

  const loadEmployees = async () => {
    setMessage('Cargando empleados…');
    try {
      const data = await window.apiFetch(`/companies/${companyId}/employees?${buildQuery()}`);
      renderEmployees(data?.items || []);
      state.total = data?.total || 0;
      state.limit = data?.limit || state.limit;
      state.offset = data?.offset ?? state.offset;
      updatePaginationButtons();
      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los empleados.' });
      setMessage('No se pudieron cargar los empleados.', true);
    }
  };

  applyFiltersButton?.addEventListener('click', () => {
    state.offset = 0;
    loadEmployees();
  });

  clearFiltersButton?.addEventListener('click', () => {
    if (qInput) qInput.value = '';
    if (statusFilter) statusFilter.value = 'all';
    if (orderFilter) orderFilter.value = 'name:asc';
    state.offset = 0;
    loadEmployees();
  });

  prevButton?.addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadEmployees();
  });

  nextButton?.addEventListener('click', () => {
    state.offset += state.limit;
    loadEmployees();
  });

  refreshButton?.addEventListener('click', loadEmployees);
  loadEmployees();
})();
