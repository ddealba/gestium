(function () {
  const table = document.getElementById('cases-table');
  const form = document.getElementById('create-case-form');
  if (!table || !form) return;

  const companyId = table.dataset.companyId;
  const tbody = table.querySelector('tbody');
  const message = document.getElementById('cases-message');
  const createMessage = document.getElementById('create-case-message');
  const refreshButton = document.getElementById('refresh-cases');
  const statusFilter = document.getElementById('filter-status');
  const orderFilter = document.getElementById('filter-order');
  const applyFiltersButton = document.getElementById('apply-filters');
  const clearFiltersButton = document.getElementById('clear-filters');

  const TERMINAL_STATUSES = new Set(['done', 'cancelled']);

  const setMessage = (el, text, isError = false, isSuccess = false) => {
    el.textContent = text;
    el.classList.toggle('is-error', isError);
    el.classList.toggle('is-success', isSuccess);
  };

  const statusClass = (status) => {
    if (status === 'done') return 'ff-tag--success';
    if (status === 'cancelled') return 'ff-tag--danger';
    if (status === 'waiting') return 'ff-tag--warn';
    return 'ff-tag--blue';
  };

  const isOverdue = (item) => {
    if (!item.due_date || TERMINAL_STATUSES.has(item.status)) return false;
    const dueDate = new Date(`${item.due_date}T00:00:00`);
    if (Number.isNaN(dueDate.getTime())) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
  };

  const getFiltersFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    return {
      status: params.get('status') || 'all',
      order: `${params.get('sort') || 'due_date'}:${params.get('order') || 'asc'}`,
    };
  };

  const updateUrl = ({ status, sort, order }) => {
    const params = new URLSearchParams(window.location.search);
    if (status && status !== 'all') params.set('status', status);
    else params.delete('status');
    params.set('sort', sort);
    params.set('order', order);
    const qs = params.toString();
    const nextUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState({}, '', nextUrl);
  };

  const buildQuery = () => {
    const status = statusFilter?.value || 'all';
    const [sort, order] = (orderFilter?.value || 'due_date:asc').split(':');
    const params = new URLSearchParams();
    if (status !== 'all') {
      params.set('status', status);
    }
    params.set('sort', sort);
    params.set('order', order);
    return { queryString: params.toString(), status, sort, order };
  };

  const renderCases = (cases) => {
    tbody.innerHTML = '';

    if (!cases.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="ff-empty">No hay cases para esta empresa.</td></tr>';
      return;
    }

    cases.forEach((item) => {
      const row = document.createElement('tr');
      const overdue = isOverdue(item);
      if (overdue) {
        row.classList.add('ff-row-overdue');
      }
      row.innerHTML = `
        <td>${item.title || '-'}</td>
        <td>${item.type || '-'}</td>
        <td>
          <span class="ff-tag ${statusClass(item.status)}">${item.status || '-'}</span>
          ${overdue ? '<span class="ff-tag ff-tag--danger">Overdue</span>' : ''}
        </td>
        <td>${item.due_date || '—'}</td>
        <td><a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/companies/${companyId}/cases/${item.id}">Ver detalle</a></td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadCases = async () => {
    setMessage(message, 'Cargando cases…');
    const { queryString, status, sort, order } = buildQuery();
    updateUrl({ status, sort, order });
    try {
      const data = await window.apiFetch(`/companies/${companyId}/cases?${queryString}`);
      renderCases(data?.cases || []);
      setMessage(message, '');
    } catch (error) {
      if (error?.noAccess) {
        window.showToast('error', 'No tienes acceso');
      }
      setMessage(message, error?.data?.message || 'No se pudieron cargar los cases.', true);
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      title: form.elements.title.value.trim(),
      type: form.elements.type.value.trim(),
      description: form.elements.description.value.trim() || null,
      due_date: form.elements.due_date.value || null,
    };

    if (!payload.title || !payload.type) {
      setMessage(createMessage, 'Título y tipo son obligatorios.', true);
      return;
    }

    setMessage(createMessage, 'Creando case…');
    try {
      await window.apiFetch(`/companies/${companyId}/cases`, {
        method: 'POST',
        body: payload,
      });

      form.reset();
      setMessage(createMessage, 'Case creado correctamente.', false, true);
      loadCases();
    } catch (error) {
      if (error?.noAccess) {
        window.showToast('error', 'No tienes acceso');
      }
      setMessage(createMessage, error?.data?.message || 'No tienes permisos o faltan datos para crear el case.', true);
    }
  });

  applyFiltersButton?.addEventListener('click', loadCases);
  clearFiltersButton?.addEventListener('click', () => {
    if (statusFilter) statusFilter.value = 'all';
    if (orderFilter) orderFilter.value = 'due_date:asc';
    loadCases();
  });

  const initialFilters = getFiltersFromUrl();
  if (statusFilter) statusFilter.value = initialFilters.status;
  if (orderFilter) orderFilter.value = initialFilters.order;

  refreshButton?.addEventListener('click', loadCases);
  loadCases();
})();
