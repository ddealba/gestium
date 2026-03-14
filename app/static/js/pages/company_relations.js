(function () {
  const root = document.getElementById('company-relations-root');
  if (!root) return;
  const companyId = root.dataset.companyId;
  if (!companyId) return;

  const table = document.getElementById('company-relations-table');
  const form = document.getElementById('company-relation-form');
  const personIdInput = document.getElementById('company-relation-person-id');
  const relationTypeInput = document.getElementById('company-relation-type');
  const startInput = document.getElementById('company-relation-start');
  const modal = document.getElementById('company-relation-modal');

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
          <td>
            <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="edit" data-relation-id="${item.relation_id}" data-relation-type="${item.relation_type || 'employee'}">Editar</button>
            <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="deactivate" data-relation-id="${item.relation_id}">Desactivar</button>
          </td>
        </tr>`,
      )
      .join('');
  };

  const load = async () => {
    const data = await window.apiFetch(`/companies/${companyId}/persons`);
    render(data?.items || []);
  };

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      await window.apiFetch(`/persons/${personIdInput.value}/companies`, {
        method: 'POST',
        body: {
          company_id: companyId,
          relation_type: relationTypeInput.value,
          start_date: startInput.value,
          status: 'active',
        },
      });
      form.reset();
      modal?.classList.remove('is-open');
      modal?.setAttribute('aria-hidden', 'true');
      await load();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo vincular la persona a la empresa.' });
    }
  });

  table.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    if (button.dataset.action === 'deactivate') {
      await window.apiFetch(`/person-company-relations/${button.dataset.relationId}/deactivate`, { method: 'POST' });
      await load();
      return;
    }
    if (button.dataset.action === 'edit') {
      const relationType = window.prompt('Nuevo tipo de relación (owner|employee|other)', button.dataset.relationType || 'employee');
      if (!relationType) return;
      await window.apiFetch(`/person-company-relations/${button.dataset.relationId}`, {
        method: 'PATCH',
        body: { relation_type: relationType },
      });
      await load();
    }
  });

  load().catch(() => {
    table.innerHTML = '<tr><td colspan="5" class="ff-muted">No se pudieron cargar las relaciones.</td></tr>';
  });
})();
