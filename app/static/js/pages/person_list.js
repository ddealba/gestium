(function () {
  const tableBody = document.getElementById('persons-table-body');
  if (!tableBody) return;

  const searchInput = document.getElementById('persons-search');

  const escapeHtml = (value) => {
    if (value == null) return '';
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  };

  const render = (items) => {
    if (!items?.length) {
      tableBody.innerHTML = '<tr><td colspan="7" class="ff-muted">No hay personas registradas.</td></tr>';
      return;
    }

    tableBody.innerHTML = items
      .map(
        (person) => `<tr>
          <td>${escapeHtml(person.full_name || '-')}</td>
          <td>${escapeHtml(person.document_number || '-')}</td>
          <td>${escapeHtml(person.email || '-')}</td>
          <td>${escapeHtml(person.phone || '-')}</td>
          <td><span class="ff-tag ${person.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${escapeHtml(person.status || '-')}</span></td>
          <td>${escapeHtml(person.created_at || '-')}</td>
          <td><a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app/persons/${person.id}">Ver</a></td>
        </tr>`,
      )
      .join('');
  };

  const load = async () => {
    tableBody.innerHTML = '<tr><td colspan="7" class="ff-muted">Cargando personas...</td></tr>';
    const search = searchInput?.value?.trim();
    const qs = new URLSearchParams({ page: '1', limit: '50' });
    if (search) qs.set('search', search);

    try {
      const data = await window.apiFetch(`/persons?${qs.toString()}`);
      render(data?.items || []);
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar las personas.' });
      tableBody.innerHTML = '<tr><td colspan="7" class="ff-muted">No se pudieron cargar las personas.</td></tr>';
    }
  };

  let debounceId = null;
  searchInput?.addEventListener('input', () => {
    if (debounceId) clearTimeout(debounceId);
    debounceId = setTimeout(load, 250);
  });

  load();
})();
