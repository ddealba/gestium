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

      renderDocuments(data.documents || []);
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

  loadCaseDetail();
  loadCaseEvents();
  loadCaseDocuments();
  loadUploadPermissions();
})();
