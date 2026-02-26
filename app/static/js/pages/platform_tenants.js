(function () {
  const grid = document.getElementById('platform-tenants-grid');
  if (!grid) return;

  const message = document.getElementById('platform-tenants-message');
  const qInput = document.getElementById('platform-tenants-q');
  const statusFilter = document.getElementById('platform-tenants-status');
  const applyButton = document.getElementById('platform-tenants-apply');
  const clearButton = document.getElementById('platform-tenants-clear');
  const prevButton = document.getElementById('platform-tenants-prev');
  const nextButton = document.getElementById('platform-tenants-next');

  const detailModal = document.getElementById('platform-tenant-detail-modal');
  const detailTitle = document.getElementById('tenant-detail-title');
  const detailContent = document.getElementById('tenant-detail-content');

  const state = { limit: 12, offset: 0, total: 0, items: [] };

  const statusVariant = (status) => {
    switch (status) {
      case 'active':
        return 'ff-tag--success';
      case 'suspended':
        return 'ff-tag--warn';
      case 'disabled':
        return 'ff-tag--danger';
      default:
        return 'ff-tag--blue';
    }
  };

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
    message.classList.toggle('is-success', !isError && Boolean(text));
  };

  const updatePaginationButtons = () => {
    prevButton.disabled = state.offset <= 0;
    nextButton.disabled = state.offset + state.limit >= state.total;
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    const q = qInput?.value?.trim();
    const status = statusFilter?.value || 'all';

    if (q) params.set('q', q);
    if (status !== 'all') params.set('status', status);

    params.set('limit', String(state.limit));
    params.set('offset', String(state.offset));
    return params.toString();
  };

  const redirectNoAccess = () => {
    window.showToast('error', 'No tienes permisos de Super Admin');
    setTimeout(() => {
      window.location.href = '/app/companies';
    }, 800);
  };

  const renderCards = (items) => {
    grid.innerHTML = '';

    if (!items.length) {
      grid.innerHTML = '<p class="ff-empty" style="grid-column: 1 / -1;">No hay gestorías para mostrar.</p>';
      return;
    }

    items.forEach((tenant) => {
      const card = document.createElement('article');
      const logo = tenant.logo_url
        ? `<img src="${tenant.logo_url}" alt="Logo ${tenant.name || 'tenant'}" class="ff-tenant-card__logo" loading="lazy" />`
        : `<div class="ff-tenant-card__logo ff-tenant-card__logo--placeholder"><i class="ph ph-buildings"></i></div>`;

      card.className = 'ff-tenant-card';
      card.innerHTML = `
        <div class="ff-tenant-card__top">
          ${logo}
          <div>
            <h3>${tenant.name || '-'}</h3>
            <span class="ff-tag ${statusVariant(tenant.status)}">${tenant.status || '-'}</span>
          </div>
        </div>

        <p class="ff-muted">Plan: <b>${tenant.plan || '-'}</b></p>

        <div class="ff-tenant-card__metrics">
          <span>Empresas: <b>${tenant.metrics?.companies || 0}</b></span>
          <span>Usuarios: <b>${tenant.metrics?.users || 0}</b></span>
        </div>

        <button type="button" class="ff-btn ff-btn--ghost" data-action="detail" data-tenant-id="${tenant.id}">
          Ver detalle / Administrar
        </button>
      `;

      grid.appendChild(card);
    });
  };

  const openDetailModal = (tenantId) => {
    const tenant = state.items.find((item) => item.id === tenantId);
    if (!tenant) return;

    detailTitle.textContent = `Detalle · ${tenant.name || 'Gestoría'}`;
    detailContent.innerHTML = `
      <p><b>Estado:</b> ${tenant.status || '-'}</p>
      <p><b>Plan:</b> ${tenant.plan || '-'}</p>
      <p><b>Empresas:</b> ${tenant.metrics?.companies || 0}</p>
      <p><b>Usuarios:</b> ${tenant.metrics?.users || 0}</p>
      <p><b>ID:</b> <code>${tenant.id}</code></p>
    `;
    detailModal.classList.add('is-open');
  };

  const loadTenants = async () => {
    setMessage('Cargando gestorías…');
    try {
      const response = await window.apiFetch(`/platform/tenants?${buildQuery()}`);
      state.items = response?.items || [];
      state.total = response?.total || 0;
      state.limit = response?.limit || state.limit;
      state.offset = response?.offset ?? state.offset;
      renderCards(state.items);
      updatePaginationButtons();
      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar las gestorías.' });
      if (error?.status === 403) {
        redirectNoAccess();
        return;
      }
      setMessage('No se pudieron cargar las gestorías.', true);
    }
  };

  applyButton?.addEventListener('click', () => {
    state.offset = 0;
    loadTenants();
  });

  clearButton?.addEventListener('click', () => {
    qInput.value = '';
    statusFilter.value = 'all';
    state.offset = 0;
    loadTenants();
  });

  prevButton?.addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadTenants();
  });

  nextButton?.addEventListener('click', () => {
    state.offset += state.limit;
    loadTenants();
  });

  grid.addEventListener('click', (event) => {
    const trigger = event.target.closest('button[data-action="detail"]');
    if (!trigger) return;
    openDetailModal(trigger.dataset.tenantId);
  });

  loadTenants();
})();
