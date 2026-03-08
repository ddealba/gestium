(function () {
  const root = document.getElementById('person-detail-root');
  if (!root) return;

  const personId = root.dataset.personId;
  const basic = document.getElementById('person-basic');
  const contact = document.getElementById('person-contact');
  const status = document.getElementById('person-status');
  const table = document.getElementById('person-relations-table');
  const formWrap = document.getElementById('person-relation-form-wrap');
  const form = document.getElementById('person-relation-form');
  const message = document.getElementById('person-relation-message');
  const documentsTable = document.getElementById('person-documents-table');

  const renderPerson = (person) => {
    basic.innerHTML = `<b>${person.full_name || '-'}</b> · ${person.document_number || '-'}`;
    contact.innerHTML = `${person.email || '-'} · ${person.phone || '-'}`;
    status.innerHTML = `<span class="ff-tag ${person.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${person.status || '-'}</span>`;
  };



  const renderDocuments = (items) => {
    if (!documentsTable) return;
    if (!items?.length) {
      documentsTable.innerHTML = '<tr><td colspan="5" class="ff-muted">Sin documentos registrados.</td></tr>';
      return;
    }

    documentsTable.innerHTML = items
      .map(
        (item) => `<tr>
          <td>${item.original_filename || '-'}</td>
          <td>${item.doc_type || '-'}</td>
          <td>${item.status || '-'}</td>
          <td>${item.created_at || '-'}</td>
          <td><a class="ff-btn ff-btn--ghost ff-btn--sm" href="/documents/${item.id}/download">Descargar</a></td>
        </tr>`,
      )
      .join('');
  };

  const renderRelations = (items) => {
    if (!items?.length) {
      table.innerHTML = '<tr><td colspan="6" class="ff-muted">Sin relaciones registradas.</td></tr>';
      return;
    }

    table.innerHTML = items
      .map(
        (item) => `<tr>
          <td>${item.company_name || item.company_id || '-'}</td>
          <td>${item.relation_type || '-'}</td>
          <td><span class="ff-tag ${item.status === 'active' ? 'ff-tag--success' : 'ff-tag--warn'}">${item.status || '-'}</span></td>
          <td>${item.start_date || '-'}</td>
          <td>${item.end_date || '-'}</td>
          <td>
            <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="deactivate" data-relation-id="${item.relation_id}">Desactivar</button>
          </td>
        </tr>`,
      )
      .join('');
  };

  const load = async () => {
    const personData = await window.apiFetch(`/persons/${personId}`);
    renderPerson(personData?.person || {});
    const relationsData = await window.apiFetch(`/persons/${personId}/companies`);
    renderRelations(relationsData?.items || []);
    const documentsData = await window.apiFetch(`/documents?person_id=${personId}&limit=50&offset=0`);
    renderDocuments(documentsData?.items || []);
  };

  document.getElementById('person-relation-add').addEventListener('click', () => {
    formWrap.style.display = 'block';
  });

  document.getElementById('person-relation-cancel').addEventListener('click', () => {
    form.reset();
    message.textContent = '';
    formWrap.style.display = 'none';
  });

  table.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-action="deactivate"]');
    if (!button) return;
    await window.apiFetch(`/person-company-relations/${button.dataset.relationId}/deactivate`, { method: 'POST' });
    await load();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      company_id: formData.get('company_id'),
      relation_type: formData.get('relation_type'),
      start_date: formData.get('start_date'),
      notes: formData.get('notes') || null,
    };

    try {
      await window.apiFetch(`/persons/${personId}/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      form.reset();
      message.textContent = 'Relación creada correctamente.';
      await load();
    } catch (error) {
      message.textContent = error?.message || 'No se pudo crear la relación.';
    }
  });

  load().catch(() => {
    basic.textContent = 'No se pudo cargar la persona.';
  });
})();
