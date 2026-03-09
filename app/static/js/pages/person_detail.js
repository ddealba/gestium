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
  const casesTable = document.getElementById('person-cases-table');
  const requestsTable = document.getElementById('person-requests-table');
  const requestForm = document.getElementById('person-request-form');
  const requestMessage = document.getElementById('person-request-message');
  const portalUserStatus = document.getElementById('person-portal-user-status');
  const portalUserForm = document.getElementById('person-portal-user-form');
  const portalUserMessage = document.getElementById('person-portal-user-message');

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

  const renderCases = (items) => {
    if (!casesTable) return;
    if (!items?.length) {
      casesTable.innerHTML = '<tr><td colspan="4" class="ff-muted">Sin expedientes registrados.</td></tr>';
      return;
    }

    casesTable.innerHTML = items
      .map(
        (item) => `<tr>
          <td>${item.title || '-'}</td>
          <td>${item.type || '-'}</td>
          <td>${item.company_name || '-'}</td>
          <td>${item.status || '-'}</td>
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

  const renderRequests = (items) => {
    if (!requestsTable) return;
    if (!items?.length) {
      requestsTable.innerHTML = '<tr><td colspan="5" class="ff-muted">Sin solicitudes.</td></tr>';
      return;
    }

    requestsTable.innerHTML = items
      .map(
        (item) => `<tr>
          <td>${item.title || '-'}</td>
          <td>${item.request_type || '-'}</td>
          <td>${item.status || '-'}</td>
          <td>${item.due_date || '-'}</td>
          <td>
            <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="resolve-request" data-request-id="${item.id}">Resolver</button>
            <button class="ff-btn ff-btn--ghost ff-btn--sm" data-action="cancel-request" data-request-id="${item.id}">Cancelar</button>
          </td>
        </tr>`,
      )
      .join('');
  };

  const renderPortalUser = (portalUser) => {
    if (!portalUserStatus || !portalUserForm) return;
    if (!portalUser) {
      portalUserStatus.textContent = 'Esta persona todavía no tiene acceso al portal.';
      return;
    }
    portalUserStatus.textContent = `Portal habilitado: ${portalUser.email} (${portalUser.status}).`;
    portalUserForm.elements.email.value = portalUser.email || '';
  };

  const load = async () => {
    const personData = await window.apiFetch(`/persons/${personId}`);
    renderPerson(personData?.person || {});
    const relationsData = await window.apiFetch(`/persons/${personId}/companies`);
    renderRelations(relationsData?.items || []);
    const documentsData = await window.apiFetch(`/documents?person_id=${personId}&limit=50&offset=0`);
    renderDocuments(documentsData?.items || []);
    const casesData = await window.apiFetch(`/cases?person_id=${personId}&limit=50&offset=0`);
    renderCases(casesData?.cases || []);
    const requestsData = await window.apiFetch(`/persons/${personId}/requests`);
    renderRequests(requestsData?.items || []);
    const portalData = await window.apiFetch(`/persons/${personId}/portal-user`);
    renderPortalUser(portalData?.portal_user || null);
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

  requestsTable?.addEventListener('click', async (event) => {
    const resolveBtn = event.target.closest('button[data-action="resolve-request"]');
    if (resolveBtn) {
      await window.apiFetch(`/person-requests/${resolveBtn.dataset.requestId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: { source: 'backoffice_manual' }, status: 'resolved' }),
      });
      await load();
      return;
    }

    const cancelBtn = event.target.closest('button[data-action="cancel-request"]');
    if (cancelBtn) {
      await window.apiFetch(`/person-requests/${cancelBtn.dataset.requestId}/cancel`, { method: 'POST' });
      await load();
    }
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

  requestForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(requestForm);
    const payload = {
      request_type: formData.get('request_type'),
      title: formData.get('title'),
      description: formData.get('description') || null,
      due_date: formData.get('due_date') || null,
      resolution_type: formData.get('resolution_type'),
      case_id: formData.get('case_id') || null,
      company_id: formData.get('company_id') || null,
      employee_id: formData.get('employee_id') || null,
    };

    try {
      await window.apiFetch(`/persons/${personId}/requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      requestForm.reset();
      requestMessage.textContent = 'Solicitud creada.';
      await load();
    } catch (error) {
      requestMessage.textContent = error?.message || 'No se pudo crear la solicitud.';
    }
  });

  portalUserForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(portalUserForm);
    const payload = {
      email: formData.get('email'),
      password: formData.get('password'),
    };

    try {
      await window.apiFetch(`/persons/${personId}/portal-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      portalUserMessage.textContent = 'Acceso portal actualizado correctamente.';
      portalUserMessage.classList.remove('is-error');
      portalUserForm.elements.password.value = '';
      await load();
    } catch (error) {
      portalUserMessage.textContent = error?.message || 'No se pudo crear/actualizar el acceso portal.';
      portalUserMessage.classList.add('is-error');
    }
  });

  load().catch(() => {
    basic.textContent = 'No se pudo cargar la persona.';
  });
})();
