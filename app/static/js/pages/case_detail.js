(function () {
  const root = document.getElementById('case-detail-root');
  if (!root) return;

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
  const documentUploadForm = document.getElementById('case-document-upload-form');
  const documentUploadMessage = document.getElementById('case-document-upload-message');
  const documentUploadButton = document.getElementById('case-document-upload-button');
  const extractionDocumentSelect = document.getElementById('extraction-document-select');
  const extractionLatestMessage = document.getElementById('extraction-latest-message');
  const extractionLatestJson = document.getElementById('extraction-latest-json');
  const extractionManualForm = document.getElementById('extraction-manual-form');
  const extractionManualMessage = document.getElementById('extraction-manual-message');

  let caseDocuments = [];

  const setMessage = (el, text, isError = false, isSuccess = false) => {
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('is-error', isError);
    el.classList.toggle('is-success', isSuccess);
  };

  const getToken = () => localStorage.getItem('gestium_access_token');

  const apiHeaders = () => {
    const token = getToken();
    if (!token) return null;
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  };

  const apiAuthHeaders = () => {
    const token = getToken();
    if (!token) return null;
    return { Authorization: `Bearer ${token}` };
  };

  const showToast = (text) => {
    let wrap = document.querySelector('.ff-toast-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'ff-toast-wrap';
      document.body.appendChild(wrap);
    }

    const toast = document.createElement('div');
    toast.className = 'ff-toast';
    toast.textContent = text;
    wrap.appendChild(toast);

    setTimeout(() => {
      toast.remove();
      if (!wrap.children.length) wrap.remove();
    }, 2600);
  };

  const showPermissionToastIfNeeded = (status) => {
    if (status === 403 || status === 404) {
      showToast('No tienes permisos o acceso');
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
      documentsBody.innerHTML = '<tr><td colspan="5" class="ff-empty">No hay documentos cargados.</td></tr>';
      return;
    }

    documents.forEach((document) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${document.original_filename || '-'}</td>
        <td>${document.doc_type || '-'}</td>
        <td><span class="ff-tag">${document.status || '-'}</span></td>
        <td>${formatDocDate(document.created_at)}</td>
        <td><a class="ff-btn ff-btn--ghost ff-btn--sm" href="/documents/${document.id}/download">Descargar</a></td>
      `;
      documentsBody.appendChild(row);
    });
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
    const headers = apiHeaders();
    if (!headers) {
      setMessage(detailMessage, 'Debes iniciar sesión para consultar el detalle.', true);
      return;
    }

    setMessage(detailMessage, 'Cargando detalle…');
    try {
      const response = await fetch(`/companies/${companyId}/cases/${caseId}`, { headers });
      const data = await response.json();
      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        setMessage(detailMessage, 'No se pudo cargar el detalle del case.', true);
        return;
      }

      renderDetail(data.case || {});
      setMessage(detailMessage, '');
    } catch (error) {
      setMessage(detailMessage, 'Error de red cargando el detalle.', true);
    }
  };

  const loadCaseEvents = async () => {
    const headers = apiHeaders();
    if (!headers) {
      setMessage(eventsMessage, 'Debes iniciar sesión para consultar eventos.', true);
      return;
    }

    setMessage(eventsMessage, 'Cargando eventos…');
    try {
      const response = await fetch(`/companies/${companyId}/cases/${caseId}/events`, { headers });
      const data = await response.json();
      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        setMessage(eventsMessage, 'No se pudieron cargar los eventos.', true);
        return;
      }

      renderEvents(data.events || []);
      setMessage(eventsMessage, '');
    } catch (error) {
      setMessage(eventsMessage, 'Error de red cargando eventos.', true);
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

    const headers = apiHeaders();
    if (!headers) {
      setMessage(extractionLatestMessage, 'Debes iniciar sesión para consultar extracciones.', true);
      return;
    }

    setMessage(extractionLatestMessage, 'Cargando extracción latest…');

    try {
      const response = await fetch(`/documents/${documentId}/extractions/latest`, { headers });
      if (response.status === 404) {
        clearLatestExtraction('No hay extracción latest para este documento.');
        return;
      }

      const data = await response.json();
      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        setMessage(extractionLatestMessage, 'No se pudo consultar la extracción latest.', true);
        return;
      }

      renderLatestExtraction(data.extraction?.extracted_json || {});
      setMessage(extractionLatestMessage, 'Última extracción cargada.', false, true);
    } catch (error) {
      setMessage(extractionLatestMessage, 'Error de red cargando extracción latest.', true);
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
    const headers = apiHeaders();
    if (!headers) {
      setManualExtractionEnabled(false);
      return;
    }

    try {
      const response = await fetch('/rbac/me/permissions', { headers });
      const data = await response.json();
      if (!response.ok) {
        setManualExtractionEnabled(false);
        return;
      }

      const canWrite = Array.isArray(data.permissions) && data.permissions.includes('document.extraction.write');
      setManualExtractionEnabled(canWrite);
      if (canWrite) {
        setMessage(extractionManualMessage, '');
      }
    } catch (error) {
      setManualExtractionEnabled(false);
    }
  };

  const loadCaseDocuments = async () => {
    const headers = apiHeaders();
    if (!headers) {
      setMessage(documentsMessage, 'Debes iniciar sesión para consultar documentos.', true);
      setUploadEnabled(false);
      return;
    }

    setMessage(documentsMessage, 'Cargando documentos…');
    try {
      const response = await fetch(`/companies/${companyId}/cases/${caseId}/documents`, { headers });
      const data = await response.json();
      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        renderDocuments([]);
        setMessage(documentsMessage, 'No se pudieron cargar los documentos.', true);
        if (response.status === 403) {
          setUploadEnabled(false);
        }
        return;
      }

      caseDocuments = data.documents || [];
      renderDocuments(caseDocuments);
      renderExtractionDocumentOptions(caseDocuments);
      setMessage(documentsMessage, '');
    } catch (error) {
      setMessage(documentsMessage, 'Error de red cargando documentos.', true);
    }
  };

  const loadUploadPermissions = async () => {
    const headers = apiHeaders();
    if (!headers) {
      setUploadEnabled(false);
      return;
    }

    try {
      const response = await fetch('/rbac/me/permissions', { headers });
      const data = await response.json();
      if (!response.ok) {
        setUploadEnabled(false);
        return;
      }

      const canUpload = Array.isArray(data.permissions) && data.permissions.includes('document.upload');
      setUploadEnabled(canUpload);
      if (!canUpload) {
        setMessage(documentUploadMessage, 'No tienes permisos para subir documentos.', true);
      }
    } catch (error) {
      setUploadEnabled(false);
    }
  };

  commentForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const headers = apiHeaders();

    if (!headers) {
      setMessage(commentMessage, 'Debes iniciar sesión para comentar.', true);
      return;
    }

    const comment = commentForm.elements.comment.value.trim();
    if (!comment) {
      setMessage(commentMessage, 'El comentario no puede estar vacío.', true);
      return;
    }

    setMessage(commentMessage, 'Guardando comentario…');

    try {
      const response = await fetch(`/companies/${companyId}/cases/${caseId}/events/comment`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ comment }),
      });

      if (!response.ok) {
        if (response.status === 403 || response.status === 404) {
          showToast('No tienes permisos para comentar este case.');
        }
        setMessage(commentMessage, 'No se pudo publicar el comentario.', true);
        return;
      }

      commentForm.reset();
      setMessage(commentMessage, 'Comentario añadido.', false, true);
      loadCaseEvents();
    } catch (error) {
      setMessage(commentMessage, 'Error de red al guardar comentario.', true);
    }
  });

  documentUploadForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const headers = apiAuthHeaders();
    if (!headers) {
      setMessage(documentUploadMessage, 'Debes iniciar sesión para subir documentos.', true);
      return;
    }

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
      const response = await fetch(`/companies/${companyId}/cases/${caseId}/documents`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        setMessage(documentUploadMessage, 'No se pudo subir el documento.', true);
        return;
      }

      documentUploadForm.reset();
      setMessage(documentUploadMessage, 'Documento subido correctamente.', false, true);
      await loadCaseDocuments();
    } catch (error) {
      setMessage(documentUploadMessage, 'Error de red al subir documento.', true);
    }
  });

  extractionDocumentSelect?.addEventListener('change', loadLatestExtraction);

  extractionManualForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    const documentId = selectedDocumentId();
    if (!documentId) {
      setMessage(extractionManualMessage, 'Selecciona primero un documento.', true);
      return;
    }

    const headers = apiHeaders();
    if (!headers) {
      setMessage(extractionManualMessage, 'Debes iniciar sesión para registrar extracción manual.', true);
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
      const response = await fetch(`/documents/${documentId}/extractions`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        showPermissionToastIfNeeded(response.status);
        setMessage(extractionManualMessage, data.message || 'No se pudo registrar la extracción.', true);
        return;
      }

      setMessage(extractionManualMessage, 'Extracción registrada correctamente.', false, true);
      extractionManualForm.reset();
      renderLatestExtraction(data.extraction?.extracted_json || {});
      setMessage(extractionLatestMessage, 'Última extracción cargada.', false, true);
    } catch (error) {
      setMessage(extractionManualMessage, 'Error de red registrando extracción.', true);
    }
  });

  loadCaseDetail();
  loadCaseEvents();
  loadCaseDocuments();
  loadUploadPermissions();
  loadExtractionWritePermissions();
})();
