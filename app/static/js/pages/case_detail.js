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

  const setMessage = (el, text, isError = false, isSuccess = false) => {
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
        setMessage(eventsMessage, 'No se pudieron cargar los eventos.', true);
        return;
      }

      renderEvents(data.events || []);
      setMessage(eventsMessage, '');
    } catch (error) {
      setMessage(eventsMessage, 'Error de red cargando eventos.', true);
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

  loadCaseDetail();
  loadCaseEvents();
})();
