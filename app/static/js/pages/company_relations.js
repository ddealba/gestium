(function () {
  const root = document.getElementById('company-relations-root');
  if (!root) return;
  const companyId = root.dataset.companyId;
  if (!companyId) return;

  const table = document.getElementById('company-relations-table');

  const render = (items) => {
    if (!items?.length) {
      table.innerHTML = '<tr><td colspan="5" class="ff-muted">Sin personas relacionadas.</td></tr>';
      return;
    }

    table.innerHTML = items
      .map(
        (item) => `<tr>
          <td>${item.full_name || '-'}</td>
          <td>${item.document_number || '-'}</td>
          <td>${item.relation_type || '-'}</td>
          <td><span class="ff-tag ${item.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${item.status || '-'}</span></td>
          <td><button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="deactivate" data-relation-id="${item.relation_id}">Desactivar</button></td>
        </tr>`,
      )
      .join('');
  };

  const load = async () => {
    const data = await window.apiFetch(`/companies/${companyId}/persons`);
    render(data?.items || []);
  };

  table.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-action="deactivate"]');
    if (!button) return;
    await window.apiFetch(`/person-company-relations/${button.dataset.relationId}/deactivate`, { method: 'POST' });
    await load();
  });

  load().catch(() => {
    table.innerHTML = '<tr><td colspan="5" class="ff-muted">No se pudieron cargar las relaciones.</td></tr>';
  });
})();
