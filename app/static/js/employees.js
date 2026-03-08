(function () {
  const list = document.getElementById('employees-list');
  if (!list) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  let companyId = list.dataset.companyId;
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

  const avatarPalette = ['#f6d6d3', '#d7e8fb', '#d8f4df', '#f8e6c7', '#eadbfb', '#d9f2f3'];

  const setMessage = (text, isError = false) => {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle('is-error', isError);
  };

  const updatePaginationButtons = () => {
    if (prevButton) prevButton.disabled = state.offset <= 0;
    if (nextButton) nextButton.disabled = state.offset + state.limit >= state.total;
  };

  const formatDate = (value) => {
    if (!value) return 'Sin fecha';
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return value;
    return new Intl.DateTimeFormat('es-ES').format(parsed);
  };

  const escapeHtml = (value) => {
    if (!value) return '';
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  };

  const initialsFromName = (name) => {
    const parts = (name || '')
      .split(' ')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 2);

    if (!parts.length) return '??';
    return parts.map((part) => part[0].toUpperCase()).join('');
  };

  const buildAvatar = (employee, index) => {
    const initials = initialsFromName(employee.person_full_name || employee.full_name);
    const paletteIndex = index % avatarPalette.length;
    return `
      <div class="ff-employee-card__avatar" style="background:${avatarPalette[paletteIndex]};">
        <span>${escapeHtml(initials)}</span>
      </div>
    `;
  };

  const statusMeta = (status) => {
    if (status === 'active') {
      return { label: 'Activo', className: 'ff-tag--success' };
    }
    if (status === 'terminated') {
      return { label: 'Terminado', className: 'ff-tag--warn' };
    }
    return { label: status || 'Sin estado', className: 'ff-tag--blue' };
  };

  const renderEmployees = (employees) => {
    list.innerHTML = '';

    if (!employees.length) {
      list.innerHTML = '<p class="ff-empty" style="grid-column:1 / -1;">No hay empleados para esta empresa.</p>';
      return;
    }

    employees.forEach((employee, index) => {
      const meta = statusMeta(employee.status);
      const card = document.createElement('article');
      card.className = 'ff-employee-card';
      card.innerHTML = `
        ${buildAvatar(employee, index)}
        <div class="ff-employee-card__content">
          <h3>${escapeHtml(employee.person_full_name || employee.full_name || 'Sin nombre')}</h3>
          <p>${escapeHtml(employee.person_document_number || 'Sin documento')}</p>
          <small>${escapeHtml(employee.person_id ? (employee.employee_ref || 'Empleado vinculado') : 'Sin persona vinculada')}</small>
          <small>Alta: ${escapeHtml(formatDate(employee.start_date))}</small>
        </div>
        <div class="ff-employee-card__status">
          <span class="ff-tag ${meta.className}">${meta.label}</span>
        </div>
      `;
      list.appendChild(card);
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
    if (!companyId) {
      try {
        const companiesResponse = await window.apiFetch('/companies?limit=1&offset=0&sort=created_at&order=desc');
        companyId = companiesResponse?.items?.[0]?.id || '';
      } catch (error) {
        window.handleApiError(error, { defaultMessage: 'No se pudieron cargar las empresas.' });
      }
    }

    if (!companyId) {
      setMessage('No hay empresas disponibles para mostrar empleados.');
      renderEmployees([]);
      updatePaginationButtons();
      return;
    }

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
