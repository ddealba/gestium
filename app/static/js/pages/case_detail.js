(function () {
  const root = document.getElementById('case-detail-root');
  if (!root) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const companyId = root.dataset.companyId;
  const caseId = root.dataset.caseId;

  const detailContainer = document.getElementById('case-detail-content');
  const eventsList = document.getElementById('case-events-list');
  const detailMessage = document.getElementById('case-detail-message');
  const eventsMessage = document.getElementById('case-events-message');
  const commentForm = document.getElementById('case-comment-form');
  const commentMessage = document.getElementById('case-comment-message');
  const documentsMessage = document.getElementById('case-documents-message');
  const documentsBody = document.getElementById('case-documents-body');
  const documentsQInput = document.getElementById('case-documents-q');
  const documentsStatusFilter = document.getElementById('case-documents-status');
  const documentsTypeInput = document.getElementById('case-documents-doc-type');
  const documentsExtractionFilter = document.getElementById('case-documents-extraction');
  const documentsOrderFilter = document.getElementById('case-documents-order');
  const documentsApplyButton = document.getElementById('case-documents-apply');
  const documentsClearButton = document.getElementById('case-documents-clear');
  const documentsPrevButton = document.getElementById('case-documents-prev');
  const documentsNextButton = document.getElementById('case-documents-next');
  const documentUploadForm = document.getElementById('case-document-upload-form');
  const documentUploadMessage = document.getElementById('case-document-upload-message');
  const documentUploadButton = document.getElementById('case-document-upload-button');
  const extractionDocumentSelect = document.getElementById('extraction-document-select');
  const extractionLatestMessage = document.getElementById('extraction-latest-message');
  const extractionLatestJson = document.getElementById('extraction-latest-json');
  const extractionManualForm = document.getElementById('extraction-manual-form');
  const extractionManualMessage = document.getElementById('extraction-manual-message');
  let canWriteDocuments = false;

  let caseDocuments = [];
  const documentsState = { limit: 20, offset: 0, total: 0 };

  const setMessage = (el, text, isError = false, isSuccess = false) => {
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('is-error', isError);
    el.classList.toggle('is-success', isSuccess);
  };

  const handleError = (error, fallbackMessage, el, options = {}) => {
    window.handleApiError(error, { defaultMessage: fallbackMessage, ...options });
    if (el) {
      setMessage(el, fallbackMessage, true);
    }
  };

  const renderDetail = (item) => {
    detailContainer.innerHTML = `
      <p><strong>ID:</strong> ${item.id}</p>
      <p><strong>Título:</strong> ${item.title || '-'}</p>
      <p><strong>Tipo:</strong> ${item.type || '-'}</p>
      <p><strong>Estado:</strong> <span class="ff-tag">${item.status || '-'}</span></p>
      <p><strong>Descripción:</strong> ${item.description || '-'}</p>
      <p><strong>Vencimiento:</strong> ${item.due_date || '-'}</p>
    `;
  };

  const renderEvents = (events) => {
    eventsList.innerHTML = '';

    if (!events.length) {
      eventsList.innerHTML = '<li class="ff-empty">No hay eventos todavía.</li>';
      return;
    }

    events.forEach((event) => {
      const item = document.createElement('li');
      const content = event.payload?.comment || JSON.stringify(event.payload || {});
      item.className = 'ff-timeline__item';
      item.innerHTML = `
        <div class="ff-timeline__meta">
          <span>${new Date(event.created_at).toLocaleString()}</span>
          <span class="ff-tag ff-tag--blue">${event.event_type}</span>
        </div>
        <div>${content}</div>
      `;
      eventsList.appendChild(item);
    });
  };

  const formatDocDate = (value) => {
    if (!value) return '-';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
  };

  const renderDocuments = (documents) => {
    if (!documentsBody) return;
    documentsBody.innerHTML = '';

    if (!documents.length) {
      documentsBody.innerHTML = '<tr><td colspan="6" class="ff-empty">No hay documentos cargados.</td></tr>';
      return;
    }

    documents.forEach((document) => {
      const row = document.createElement('tr');
      const extractionText = document.has_extraction ? '✔' : 'Pending';
      const writeActions = canWriteDocuments
        ? `
            <button type="button" class="ff-btn ff-btn--ghost ff-btn--sm" data-action="processed" data-document-id="${document.id}">Marcar procesado</button>
            <button type="button" class="ff-btn ff-btn--ghost ff-btn--sm" data-action="archived" data-document-id="${document.id}">Archivar</button>
          `
        : '';
      row.innerHTML = `
        <td>${document.original_filename || '-'}</td>
        <td>${document.doc_type || '-'}</td>
        <td><span class="ff-tag">${document.status || '-'}</span></td>
        <td><span class="ff-tag">${extractionText}</span></td>
        <td>${formatDocDate(document.created_at)}</td>
        <td>
          <div class="ff-filters__actions">
            <a class="ff-btn ff-btn--ghost ff-btn--sm" href="/documents/${document.id}/download">Descargar</a>
            ${writeActions}
          </div>
        </td>
      `;
      documentsBody.appendChild(row);
    });
  };

  const updateDocumentStatus = async (documentId, status) => {
    try {
      const data = await window.apiFetch(`/documents/${documentId}/status`, {
        method: 'PATCH',
        body: { status },
      });
      const updated = data?.document;
      if (updated) {
        caseDocuments = caseDocuments.map((item) => (item.id === documentId ? { ...item, ...updated } : item));
        renderDocuments(caseDocuments);
      }
      setMessage(documentsMessage, 'Estado actualizado correctamente.', false, true);
    } catch (error) {
      handleError(error, 'No se pudo actualizar el estado del documento.', documentsMessage);
    }
  };

  const setUploadEnabled = (enabled) => {
    if (!documentUploadForm) return;
    Array.from(documentUploadForm.elements).forEach((el) => {
      el.disabled = !enabled;
    });
    if (documentUploadButton) {
      documentUploadButton.disabled = !enabled;
    }
  };

  const loadCaseDetail = async () => {
    setMessage(detailMessage, 'Cargando detalle…');
    try {
      const data = await window.apiFetch(`/companies/${companyId}/cases/${caseId}`);
      renderDetail(data?.case || {});
      setMessage(detailMessage, '');
    } catch (error) {
      handleError(error, 'No se pudo cargar el detalle del case.', detailMessage);
    }
  };

  const loadCaseEvents = async () => {
    setMessage(eventsMessage, 'Cargando eventos…');
    try {
      const data = await window.apiFetch(`/companies/${companyId}/cases/${caseId}/events`);
      renderEvents(data?.events || []);
      setMessage(eventsMessage, '');
    } catch (error) {
      handleError(error, 'No se pudieron cargar los eventos.', eventsMessage);
    }
  };

  const renderLatestExtraction = (payload) => {
    if (!extractionLatestJson) return;
    extractionLatestJson.textContent = JSON.stringify(payload || {}, null, 2);
  };

  const clearLatestExtraction = (message = 'Selecciona un documento para consultar su extracción latest.') => {
    setMessage(extractionLatestMessage, '');
    if (extractionLatestJson) extractionLatestJson.textContent = message;
  };

  const selectedDocumentId = () => extractionDocumentSelect?.value || '';

  const renderExtractionDocumentOptions = (documents) => {
    if (!extractionDocumentSelect) return;
    const currentValue = extractionDocumentSelect.value;
    extractionDocumentSelect.innerHTML = '<option value="">Selecciona un documento…</option>';

    documents.forEach((document) => {
      const option = document.createElement('option');
      option.value = document.id;
      option.textContent = document.original_filename || document.id;
      extractionDocumentSelect.appendChild(option);
    });

    if (documents.some((document) => document.id === currentValue)) {
      extractionDocumentSelect.value = currentValue;
      return;
    }

    clearLatestExtraction();
  };

  const loadLatestExtraction = async () => {
    const documentId = selectedDocumentId();
    if (!documentId) {
      clearLatestExtraction();
      return;
    }

    setMessage(extractionLatestMessage, 'Cargando extracción latest…');

    try {
      const data = await window.apiFetch(`/documents/${documentId}/extractions/latest`);
      renderLatestExtraction(data?.extraction?.extracted_json || {});
      setMessage(extractionLatestMessage, 'Última extracción cargada.', false, true);
    } catch (error) {
      handleError(error, 'No se pudo consultar la extracción latest.', extractionLatestMessage);
    }
  };

  const setManualExtractionEnabled = (enabled) => {
    if (!extractionManualForm) return;
    extractionManualForm.hidden = !enabled;
    Array.from(extractionManualForm.elements).forEach((el) => {
      el.disabled = !enabled;
    });

    if (!enabled) {
      setMessage(extractionManualMessage, 'No tienes permisos para registrar extracción manual.', true);
    }
  };

  const loadExtractionWritePermissions = async () => {
    try {
      const data = await window.apiFetch('/rbac/me/permissions');
      const canWrite = Array.isArray(data?.permissions) && data.permissions.includes('document.extraction.write');
      setManualExtractionEnabled(canWrite);
      if (canWrite) {
        setMessage(extractionManualMessage, '');
      }
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los permisos.' });
      setManualExtractionEnabled(false);
    }
  };


  const updateDocumentPaginationButtons = () => {
    if (documentsPrevButton) documentsPrevButton.disabled = documentsState.offset <= 0;
    if (documentsNextButton) documentsNextButton.disabled = documentsState.offset + documentsState.limit >= documentsState.total;
  };

  const buildDocumentsQuery = () => {
    const params = new URLSearchParams();
    const q = documentsQInput?.value?.trim();
    const status = documentsStatusFilter?.value || 'all';
    const docType = documentsTypeInput?.value?.trim();
    const extraction = documentsExtractionFilter?.value || 'all';
    const [sort, order] = (documentsOrderFilter?.value || 'created_at:desc').split(':');

    if (q) params.set('q', q);
    if (status !== 'all') params.set('status', status);
    if (docType) params.set('doc_type', docType);
    if (extraction === 'with') params.set('has_extraction', 'true');
    if (extraction === 'without') params.set('has_extraction', 'false');
    params.set('sort', sort);
    params.set('order', order);
    params.set('limit', String(documentsState.limit));
    params.set('offset', String(documentsState.offset));
    return params.toString();
  };

  const loadCaseDocuments = async () => {
    setMessage(documentsMessage, 'Cargando documentos…');
    try {
      const data = await window.apiFetch(`/companies/${companyId}/cases/${caseId}/documents?${buildDocumentsQuery()}`);
      caseDocuments = data?.items || [];
      documentsState.total = data?.total || 0;
      documentsState.limit = data?.limit || documentsState.limit;
      documentsState.offset = data?.offset ?? documentsState.offset;
      renderDocuments(caseDocuments);
      renderExtractionDocumentOptions(caseDocuments);
      updateDocumentPaginationButtons();
      setMessage(documentsMessage, '');
    } catch (error) {
      renderDocuments([]);
      handleError(error, 'No se pudieron cargar los documentos.', documentsMessage);
      if (error?.noAccess) {
        setUploadEnabled(false);
      }
    }
  };

  const loadUploadPermissions = async () => {
    try {
      const data = await window.apiFetch('/rbac/me/permissions');
      const canUpload = Array.isArray(data?.permissions) && data.permissions.includes('document.upload');
      canWriteDocuments = Array.isArray(data?.permissions) && data.permissions.includes('document.write');
      setUploadEnabled(canUpload);
      if (!canUpload) {
        setMessage(documentUploadMessage, 'No tienes permisos para subir documentos.', true);
      }
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los permisos.' });
      setUploadEnabled(false);
    }
  };

  commentForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const comment = commentForm.elements.comment.value.trim();
    if (!comment) {
      setMessage(commentMessage, 'El comentario no puede estar vacío.', true);
      return;
    }

    setMessage(commentMessage, 'Guardando comentario…');

    try {
      await window.apiFetch(`/companies/${companyId}/cases/${caseId}/events/comment`, {
        method: 'POST',
        body: { comment },
      });

      commentForm.reset();
      setMessage(commentMessage, 'Comentario añadido.', false, true);
      loadCaseEvents();
    } catch (error) {
      handleError(error, 'No se pudo publicar el comentario.', commentMessage);
    }
  });

  documentUploadForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const fileInput = documentUploadForm.elements.file;
    const file = fileInput?.files?.[0];

    if (!file) {
      setMessage(documentUploadMessage, 'Selecciona un archivo para subir.', true);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const docType = documentUploadForm.elements.doc_type?.value;
    if (docType) {
      formData.append('doc_type', docType);
    }

    setMessage(documentUploadMessage, 'Subiendo documento…');

    try {
      await window.apiFetch(`/companies/${companyId}/cases/${caseId}/documents`, {
        method: 'POST',
        formData,
      });

      documentUploadForm.reset();
      setMessage(documentUploadMessage, 'Documento subido correctamente.', false, true);
      await loadCaseDocuments();
    } catch (error) {
      handleError(error, 'No se pudo subir el documento.', documentUploadMessage);
    }
  });

  extractionDocumentSelect?.addEventListener('change', loadLatestExtraction);


  documentsApplyButton?.addEventListener('click', () => {
    documentsState.offset = 0;
    loadCaseDocuments();
  });

  documentsClearButton?.addEventListener('click', () => {
    if (documentsQInput) documentsQInput.value = '';
    if (documentsStatusFilter) documentsStatusFilter.value = 'all';
    if (documentsTypeInput) documentsTypeInput.value = '';
    if (documentsExtractionFilter) documentsExtractionFilter.value = 'all';
    if (documentsOrderFilter) documentsOrderFilter.value = 'created_at:desc';
    documentsState.offset = 0;
    loadCaseDocuments();
  });

  documentsPrevButton?.addEventListener('click', () => {
    documentsState.offset = Math.max(0, documentsState.offset - documentsState.limit);
    loadCaseDocuments();
  });

  documentsNextButton?.addEventListener('click', () => {
    documentsState.offset += documentsState.limit;
    loadCaseDocuments();
  });

  documentsBody?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action][data-document-id]');
    if (!button) return;
    const documentId = button.dataset.documentId;
    const status = button.dataset.action;
    if (!documentId || !status) return;
    updateDocumentStatus(documentId, status);
  });


  extractionManualForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const documentId = selectedDocumentId();
    if (!documentId) {
      setMessage(extractionManualMessage, 'Selecciona primero un documento.', true);
      return;
    }

    const rawJson = extractionManualForm.elements.raw_json.value.trim();
    if (!rawJson) {
      setMessage(extractionManualMessage, 'Debes pegar un JSON válido.', true);
      return;
    }

    let payload;
    try {
      payload = JSON.parse(rawJson);
    } catch (error) {
      setMessage(extractionManualMessage, 'El contenido no es JSON válido.', true);
      return;
    }

    setMessage(extractionManualMessage, 'Registrando extracción…');

    try {
      const data = await window.apiFetch(`/documents/${documentId}/extractions`, {
        method: 'POST',
        body: payload,
      });

      setMessage(extractionManualMessage, 'Extracción registrada correctamente.', false, true);
      extractionManualForm.reset();
      renderLatestExtraction(data?.extraction?.extracted_json || {});
      setMessage(extractionLatestMessage, 'Última extracción cargada.', false, true);
    } catch (error) {
      handleError(error, 'No se pudo registrar la extracción.', extractionManualMessage);
    }
  });

  loadCaseDetail();
  loadCaseEvents();
  loadCaseDocuments();
  loadUploadPermissions();
  loadExtractionWritePermissions();
})();
