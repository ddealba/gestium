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
  const employeeDocumentsTable = document.getElementById('employee-documents-table');
  const employeeDocumentsMessage = document.getElementById('employee-documents-message');
  const employeeForm = document.getElementById('employee-manage-form');
  const employeeIdInput = document.getElementById('employee-id');
  const employeePersonId = document.getElementById('employee-person-id');
  const employeeFullName = document.getElementById('employee-full-name');
  const employeeRef = document.getElementById('employee-ref');
  const employeeStatus = document.getElementById('employee-status');
  const employeeStartDate = document.getElementById('employee-start-date');
  const employeeEndDate = document.getElementById('employee-end-date');
  const employeeNewButton = document.getElementById('employee-new');
  const employeeModal = document.getElementById('employee-create-modal');

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
      card.dataset.employeeId = employee.id;
      card.dataset.personId = employee.person_id || '';
      card.dataset.fullName = employee.full_name || '';
      card.dataset.employeeRef = employee.employee_ref || '';
      card.dataset.status = employee.status || 'active';
      card.dataset.startDate = employee.start_date || '';
      card.dataset.endDate = employee.end_date || '';

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
          <button class="ff-btn ff-btn--ghost ff-btn--sm" type="button" data-action="terminate">Terminar</button>
        </div>
      `;
      list.appendChild(card);
    });
  };



  const renderEmployeeDocuments = (items) => {
    if (!employeeDocumentsTable) return;
    if (!items?.length) {
      employeeDocumentsTable.innerHTML = '<tr><td colspan="4" class="ff-muted">Sin documentos laborales.</td></tr>';
      return;
    }
    employeeDocumentsTable.innerHTML = items
      .map((item) => `<tr><td>${escapeHtml(item.original_filename || '-')}</td><td>${escapeHtml(item.doc_type || '-')}</td><td>${escapeHtml(item.status || '-')}</td><td>${escapeHtml(item.created_at || '-')}</td></tr>`)
      .join('');
  };

  const loadEmployeeDocuments = async (employeeId) => {
    if (!employeeId) return;
    if (employeeDocumentsMessage) employeeDocumentsMessage.textContent = 'Cargando documentos laborales…';
    try {
      const data = await window.apiFetch(`/documents?employee_id=${employeeId}&limit=50&offset=0`);
      renderEmployeeDocuments(data?.items || []);
      if (employeeDocumentsMessage) employeeDocumentsMessage.textContent = '';
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los documentos laborales.' });
      if (employeeDocumentsMessage) employeeDocumentsMessage.textContent = 'No se pudieron cargar los documentos laborales.';
    }
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


  list.addEventListener('click', async (event) => {
    const card = event.target.closest('.ff-employee-card[data-employee-id]');
    if (!card) return;
    if (employeeIdInput) employeeIdInput.value = card.dataset.employeeId || '';
    if (employeePersonId) employeePersonId.value = card.dataset.personId || '';
    if (employeeFullName) employeeFullName.value = card.dataset.fullName || '';
    if (employeeRef) employeeRef.value = card.dataset.employeeRef || '';
    if (employeeStatus) employeeStatus.value = card.dataset.status || 'active';
    if (employeeStartDate) employeeStartDate.value = card.dataset.startDate || '';
    if (employeeEndDate) employeeEndDate.value = card.dataset.endDate || '';

    if (event.target.closest('[data-action="terminate"]')) {
      const endDate = window.prompt('Fecha de baja (YYYY-MM-DD)', card.dataset.endDate || '');
      if (endDate) {
        await window.apiFetch(`/companies/${companyId}/employees/${card.dataset.employeeId}/terminate`, {
          method: 'POST',
          body: { end_date: endDate },
        });
        await loadEmployees();
      }
      return;
    }
    employeeModal?.classList.add('is-open');
    employeeModal?.setAttribute('aria-hidden', 'false');
    employeePersonId?.focus();
    loadEmployeeDocuments(card.dataset.employeeId);
  });



  const resetEmployeeForm = () => {
    if (!employeeForm) return;
    employeeForm.reset();
    if (employeeIdInput) employeeIdInput.value = '';
    if (employeeStatus) employeeStatus.value = 'active';
  };

  employeeForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!companyId) return;
    const body = {
      person_id: employeePersonId.value || null,
      full_name: employeeFullName.value || null,
      employee_ref: employeeRef.value || null,
      status: employeeStatus.value,
      start_date: employeeStartDate.value,
      end_date: employeeEndDate.value || null,
    };
    try {
      if (employeeIdInput.value) {
        await window.apiFetch(`/companies/${companyId}/employees/${employeeIdInput.value}`, { method: 'PATCH', body });
      } else {
        await window.apiFetch(`/companies/${companyId}/employees`, { method: 'POST', body });
      }
      resetEmployeeForm();
      employeeModal?.classList.remove('is-open');
      employeeModal?.setAttribute('aria-hidden', 'true');
      await loadEmployees();
      setMessage('Empleado guardado correctamente.');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo guardar el empleado.' });
      setMessage('No se pudo guardar el empleado.', true);
    }
  });

  employeeNewButton?.addEventListener('click', resetEmployeeForm);

  refreshButton?.addEventListener('click', loadEmployees);
  loadEmployees();
})();
