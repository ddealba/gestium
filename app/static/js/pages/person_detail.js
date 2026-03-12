(function () {
  const root = document.getElementById('person-detail-root');
  if (!root) return;

  const personId = root.dataset.personId;
  const basic = document.getElementById('person-basic');
  const contact = document.getElementById('person-contact');
  const status = document.getElementById('person-status');
  const relationsTable = document.getElementById('person-relations-table');
  const employeeBlock = document.getElementById('person-employee-block');
  const documentsTable = document.getElementById('person-documents-table');
  const casesTable = document.getElementById('person-cases-table');
  const requestsTable = document.getElementById('person-requests-table');
  const auditTable = document.getElementById('person-audit-table');
  const portalStatus = document.getElementById('person-portal-user-status');
  const completionTitle = document.getElementById('person-completion-title');
  const completionProgress = document.getElementById('person-completion-progress');
  const completionFlags = document.getElementById('person-completion-flags');
  const headerName = document.getElementById('person-header-name');

  const escapeHtml = (value) => {
    if (value == null) return '';
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  };

  const statusTag = (value) => {
    const normalized = value || '-';
    const tone = ['active', 'done', 'resolved'].includes(normalized)
      ? 'ff-tag--success'
      : ['cancelled', 'rejected', 'expired'].includes(normalized)
        ? 'ff-tag--danger'
        : 'ff-tag--warn';
    return `<span class="ff-tag ${tone}">${escapeHtml(normalized)}</span>`;
  };

  const renderPerson = (person) => {
    headerName.textContent = person.full_name || 'Detalle de persona';
    basic.innerHTML = `<dl class="ff-person-detail__data">
      <dt>Nombre</dt><dd>${escapeHtml(person.full_name || '-')}</dd>
      <dt>Documento</dt><dd>${escapeHtml(person.document_number || '-')}</dd>
      <dt>Dirección</dt><dd>${escapeHtml(person.address_line1 || '-')}</dd>
    </dl>`;
    contact.innerHTML = `<dl class="ff-person-detail__data">
      <dt>Email</dt><dd>${escapeHtml(person.email || '-')}</dd>
      <dt>Teléfono</dt><dd>${escapeHtml(person.phone || '-')}</dd>
      <dt>Ciudad</dt><dd>${escapeHtml(person.city || '-')}</dd>
    </dl>`;
    status.innerHTML = statusTag(person.status);
  };

  const renderCompleteness = (completeness) => {
    const pct = Number(completeness?.completion_pct || 0);
    completionProgress.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    completionTitle.textContent = `Completitud: ${pct}%`;
    const checks = completeness?.checks || {};
    const labels = {
      basic_info: 'Datos básicos completos',
      identification: 'Identificación',
      contact_info: 'Contacto',
      address_info: 'Dirección',
      portal_access: 'Acceso portal',
      required_documents: 'Documentación requerida',
    };
    const flags = Object.keys(labels).map((key) => [labels[key], checks[key]]);
    completionFlags.innerHTML = flags
      .map(([label, ok]) => `<div><strong>${escapeHtml(label)}:</strong> ${ok ? '<span class=\"ff-tag ff-tag--success\">Sí</span>' : '<span class=\"ff-tag ff-tag--warn\">No</span>'}</div>`)
      .concat((completeness?.missing_fields || []).length ? [`<div><strong>Campos faltantes:</strong> ${(completeness.missing_fields || []).map((item) => `<span class=\"ff-tag ff-tag--warn\">${escapeHtml(item)}</span>`).join(' ')}</div>`] : [])
      .concat((completeness?.missing_documents || []).length ? [`<div><strong>Documentos faltantes:</strong> ${(completeness.missing_documents || []).map((item) => `<span class=\"ff-tag ff-tag--warn\">${escapeHtml(item)}</span>`).join(' ')}</div>`] : [])
      .join('');
  };

  const renderRelations = (items) => {
    if (!items?.length) {
      relationsTable.innerHTML = '<tr><td colspan="5" class="ff-muted">Sin relaciones registradas.</td></tr>';
      return;
    }
    relationsTable.innerHTML = items.map((item) => `<tr>
      <td><a href="/app/companies">${escapeHtml(item.company_name || item.company_id || '-')}</a></td>
      <td>${escapeHtml(item.relation_type || '-')}</td>
      <td>${statusTag(item.status)}</td>
      <td>${escapeHtml(item.start_date || '-')}</td>
      <td>${escapeHtml(item.end_date || '-')}</td>
    </tr>`).join('');
  };

  const renderEmployee = (employee) => {
    if (!employee) {
      employeeBlock.innerHTML = '<p class="ff-muted">No hay empleado vinculado a esta persona.</p>';
      return;
    }
    employeeBlock.innerHTML = `<dl class="ff-person-detail__data">
      <dt>Empresa</dt><dd>${escapeHtml(employee.company_name || '-')}</dd>
      <dt>Estado laboral</dt><dd>${escapeHtml(employee.employment_status || '-')}</dd>
      <dt>Fecha alta</dt><dd>${escapeHtml(employee.start_date || '-')}</dd>
      <dt>Fecha baja</dt><dd>${escapeHtml(employee.end_date || '-')}</dd>
    </dl>
    ${employee.detail_url ? `<a class="ff-btn ff-btn--ghost ff-btn--sm" href="/app${escapeHtml(employee.detail_url)}">Ir a empleado</a>` : ''}`;
  };

  const renderCases = (items) => {
    if (!items?.length) {
      casesTable.innerHTML = '<tr><td colspan="6" class="ff-muted">Sin expedientes registrados.</td></tr>';
      return;
    }
    casesTable.innerHTML = items.map((item) => `<tr>
      <td>${escapeHtml(item.title || '-')}</td>
      <td>${escapeHtml(item.type || '-')}</td>
      <td>${escapeHtml(item.company_name || '-')}</td>
      <td>${statusTag(item.status)}</td>
      <td>${escapeHtml(item.due_date || '-')}</td>
      <td>${item.detail_url ? `<a class="ff-btn ff-btn--ghost ff-btn--sm" href="${escapeHtml(item.detail_url)}">Ver</a>` : '-'}</td>
    </tr>`).join('');
  };

  const renderDocuments = (items) => {
    if (!items?.length) {
      documentsTable.innerHTML = '<tr><td colspan="5" class="ff-muted">Sin documentos registrados.</td></tr>';
      return;
    }
    documentsTable.innerHTML = items.map((item) => `<tr>
      <td>${escapeHtml(item.name || '-')}</td>
      <td>${escapeHtml(item.type || '-')}</td>
      <td>${statusTag(item.status)}</td>
      <td>${(item.contexts || []).map((ctx) => `<span class="ff-tag ff-tag--blue">${escapeHtml(ctx)}</span>`).join(' ') || '-'}</td>
      <td>${item.download_url ? `<a class="ff-btn ff-btn--ghost ff-btn--sm" href="${escapeHtml(item.download_url)}">Descargar</a>` : '-'}</td>
    </tr>`).join('');
  };

  const renderRequests = (items) => {
    if (!items?.length) {
      requestsTable.innerHTML = '<tr><td colspan="6" class="ff-muted">Sin solicitudes.</td></tr>';
      return;
    }
    const lastAction = (item) => item.resolved_at || item.reviewed_at || item.submitted_at || '-';
    const actions = (item) => {
      if (['resolved', 'cancelled'].includes(item.status)) return '-';
      return `
        <div class="ff-filters__actions" style="gap:6px;">
          <button class="ff-btn ff-btn--ghost ff-btn--sm" type="button" data-request-action="review" data-request-id="${escapeHtml(item.id)}">En revisión</button>
          <button class="ff-btn ff-btn--primary ff-btn--sm" type="button" data-request-action="resolve" data-request-id="${escapeHtml(item.id)}">Resolver</button>
          <button class="ff-btn ff-btn--soft ff-btn--sm" type="button" data-request-action="reject" data-request-id="${escapeHtml(item.id)}">Rechazar</button>
          <button class="ff-btn ff-btn--soft ff-btn--sm" type="button" data-request-action="cancel" data-request-id="${escapeHtml(item.id)}">Cancelar</button>
        </div>`;
    };
    requestsTable.innerHTML = items.map((item) => `<tr>
      <td>${escapeHtml(item.title || '-')}</td>
      <td>${escapeHtml(item.type || '-')}</td>
      <td>${statusTag(item.status)}</td>
      <td>${escapeHtml(item.due_date || '-')}</td>
      <td>${escapeHtml(lastAction(item))}</td>
      <td>${actions(item)}</td>
    </tr>`).join('');
  };

  const renderPortal = (portalAccess) => {
    if (!portalAccess) {
      portalStatus.innerHTML = 'Usuario portal: <span class="ff-tag ff-tag--warn">No</span>';
      return;
    }
    portalStatus.innerHTML = `Usuario portal: <span class="ff-tag ff-tag--success">Sí</span> · ${escapeHtml(portalAccess.email || '-')} · ${statusTag(portalAccess.status)}`;
  };

  const renderAudit = (items) => {
    if (!items?.length) {
      auditTable.innerHTML = '<tr><td colspan="3" class="ff-muted">Sin actividad reciente.</td></tr>';
      return;
    }
    auditTable.innerHTML = items.map((item) => `<tr>
      <td>${escapeHtml(item.created_at || '-')}</td>
      <td>${escapeHtml(item.action || '-')}</td>
      <td>${escapeHtml(item.entity_type || '-')} · ${escapeHtml(item.entity_id || '-')}</td>
    </tr>`).join('');
  };

  const load = async () => {
    const data = await window.apiFetch(`/persons/${personId}/overview`);
    renderPerson(data?.person || {});
    renderCompleteness(data?.completeness || {});
    renderRelations(data?.companies || []);
    renderEmployee(data?.employee || null);
    renderCases(data?.cases || []);
    renderDocuments(data?.documents || []);
    renderRequests(data?.requests || []);
    renderPortal(data?.portal_access || null);
    renderAudit(data?.audit || []);
  };


  requestsTable?.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-request-action]');
    if (!button) return;
    const requestId = button.dataset.requestId;
    const action = button.dataset.requestAction;
    try {
      if (action === 'review') {
        await window.apiFetch(`/person-requests/${requestId}/submit-review`, { method: 'POST', body: { review_notes: 'Revisión iniciada desde vista persona' } });
      } else if (action === 'resolve') {
        await window.apiFetch(`/person-requests/${requestId}/resolve`, { method: 'POST', body: { review_notes: 'Resuelta desde vista persona' } });
      } else if (action === 'reject') {
        const reason = window.prompt('Motivo del rechazo');
        if (!reason) return;
        await window.apiFetch(`/person-requests/${requestId}/reject`, { method: 'POST', body: { rejection_reason: reason } });
      } else if (action === 'cancel') {
        await window.apiFetch(`/person-requests/${requestId}/cancel`, { method: 'POST' });
      }
      await load();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo ejecutar la acción en la solicitud.' });
    }
  });

  document.getElementById('portal-create-action')?.addEventListener('click', async () => {
    const email = window.prompt('Email de acceso portal');
    if (!email) return;
    const password = window.prompt('Password inicial (mínimo 8 caracteres)');
    if (!password) return;
    try {
      await window.apiFetch(`/persons/${personId}/portal-user`, {
        method: 'POST',
        body: { email, password },
      });
      window.showToast('success', 'Acceso portal actualizado');
      await load();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo actualizar acceso portal.' });
    }
  });

  document.getElementById('portal-disable-action')?.addEventListener('click', async () => {
    try {
      await window.apiFetch(`/persons/${personId}/portal-user/disable`, { method: 'POST' });
      window.showToast('success', 'Acceso portal desactivado');
      await load();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo desactivar acceso portal.' });
    }
  });

  document.getElementById('generate-requests-action')?.addEventListener('click', async () => {
    try {
      const result = await window.apiFetch(`/persons/${personId}/generate-requests`, { method: 'POST' });
      window.showToast('success', `Solicitudes generadas: ${result.created || 0}`);
      await load();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron generar solicitudes pendientes.' });
    }
  });

  load().catch((error) => {
    window.handleApiError(error, { defaultMessage: 'No se pudo cargar la vista 360 de persona.' });
    basic.textContent = 'No se pudo cargar la persona.';
  });
})();
