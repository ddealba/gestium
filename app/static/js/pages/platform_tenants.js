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

  const confirmModal = document.getElementById('platform-tenant-status-confirm-modal');
  const confirmContent = document.getElementById('platform-tenant-status-confirm-content');
  const confirmButton = document.getElementById('platform-tenant-status-confirm-submit');
  const cancelButton = document.getElementById('platform-tenant-status-confirm-cancel');

  const state = { limit: 12, offset: 0, total: 0, items: [], pendingAction: null };

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

  const closeConfirmModal = () => {
    if (!confirmModal) return;
    confirmModal.classList.remove('is-open');
    document.body.style.overflow = '';
    state.pendingAction = null;
  };

  const openConfirmModal = (tenant, nextStatus, actionLabel) => {
    if (!confirmModal) return;
    state.pendingAction = { tenantId: tenant.id, nextStatus };
    confirmContent.textContent = `¿Confirmas ${actionLabel.toLowerCase()} la gestoría "${tenant.name}"?`;
    confirmModal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  };

  const actionForTenant = (tenant) => {
    if (tenant.status === 'active') return { label: 'Suspender', nextStatus: 'suspended' };
    if (tenant.status === 'suspended') return { label: 'Activar', nextStatus: 'active' };
    return { label: 'Desactivar', nextStatus: 'disabled' };
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
      const action = actionForTenant(tenant);

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

        <div class="ff-filters__actions">
          <a href="/app/platform/tenants/${tenant.id}" class="ff-btn ff-btn--ghost">Ver detalle</a>
          <button type="button" class="ff-btn ff-btn--primary" data-action="select-tenant" data-tenant-id="${tenant.id}" data-tenant-name="${tenant.name || ''}">
            Administrar tenant
          </button>
          <button type="button" class="ff-btn ff-btn--primary" data-action="status-change" data-tenant-id="${tenant.id}" data-next-status="${action.nextStatus}" data-action-label="${action.label}">
            ${action.label}
          </button>
        </div>
      `;

      grid.appendChild(card);
    });
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

  const submitStatusChange = async () => {
    if (!state.pendingAction) return;
    const { tenantId, nextStatus } = state.pendingAction;
    try {
      confirmButton.disabled = true;
      await window.apiFetch(`/platform/tenants/${tenantId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus }),
      });
      closeConfirmModal();
      window.showToast('success', 'Estado actualizado correctamente.');
      await loadTenants();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo actualizar el estado del tenant.' });
    } finally {
      confirmButton.disabled = false;
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
    const selectTrigger = event.target.closest('button[data-action="select-tenant"]');
    if (selectTrigger) {
      sessionStorage.setItem('admin_selected_tenant_id', selectTrigger.dataset.tenantId || '');
      sessionStorage.setItem('admin_selected_tenant_name', selectTrigger.dataset.tenantName || 'Tenant');
      window.location.href = '/app/companies';
      return;
    }

    const trigger = event.target.closest('button[data-action="status-change"]');
    if (!trigger) return;
    const tenant = state.items.find((item) => item.id === trigger.dataset.tenantId);
    if (!tenant) return;
    openConfirmModal(tenant, trigger.dataset.nextStatus, trigger.dataset.actionLabel || 'Cambiar estado');
  });

  confirmButton?.addEventListener('click', submitStatusChange);
  cancelButton?.addEventListener('click', closeConfirmModal);

  loadTenants();
})();
