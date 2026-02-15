(function () {
  const table = document.getElementById('cases-table');
  const form = document.getElementById('create-case-form');
  if (!table || !form) return;

  const companyId = table.dataset.companyId;
  const tbody = table.querySelector('tbody');
  const message = document.getElementById('cases-message');
  const createMessage = document.getElementById('create-case-message');
  const refreshButton = document.getElementById('refresh-cases');

  const setMessage = (el, text, isError = false, isSuccess = false) => {
    el.textContent = text;
    el.classList.toggle('is-error', isError);
    el.classList.toggle('is-success', isSuccess);
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('gestium_access_token');
    if (!token) return null;
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  };

  const statusClass = (status) => {
    if (status === 'done') return 'ff-tag--success';
    if (status === 'cancelled') return 'ff-tag--danger';
    if (status === 'waiting') return 'ff-tag--warn';
    return 'ff-tag--blue';
  };

  const renderCases = (cases) => {
    tbody.innerHTML = '';

    if (!cases.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="ff-empty">No hay cases para esta empresa.</td></tr>';
      return;
    }

    cases.forEach((item) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${item.title || '-'}</td>
        <td>${item.type || '-'}</td>
        <td><span class="ff-tag ${statusClass(item.status)}">${item.status || '-'}</span></td>
        <td>${item.due_date || '-'}</td>
        <td><a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/companies/${companyId}/cases/${item.id}">Ver detalle</a></td>
      `;
      tbody.appendChild(row);
    });
  };

  const loadCases = async () => {
    const headers = getAuthHeaders();
    if (!headers) {
      setMessage(message, 'Debes iniciar sesión para consultar cases.', true);
      return;
    }

    setMessage(message, 'Cargando cases…');
    try {
      const response = await fetch(`/companies/${companyId}/cases`, { headers });
      const data = await response.json();

      if (!response.ok) {
        setMessage(message, 'No se pudieron cargar los cases.', true);
        return;
      }

      renderCases(data.cases || []);
      setMessage(message, '');
    } catch (error) {
      setMessage(message, 'Error de red al consultar cases.', true);
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const headers = getAuthHeaders();
    if (!headers) {
      setMessage(createMessage, 'Debes iniciar sesión para crear cases.', true);
      return;
    }

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
      const response = await fetch(`/companies/${companyId}/cases`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        setMessage(createMessage, 'No tienes permisos o faltan datos para crear el case.', true);
        return;
      }

      form.reset();
      setMessage(createMessage, 'Case creado correctamente.', false, true);
      loadCases();
    } catch (error) {
      setMessage(createMessage, 'Error de red al crear el case.', true);
    }
  });

  refreshButton?.addEventListener('click', loadCases);
  loadCases();
})();
