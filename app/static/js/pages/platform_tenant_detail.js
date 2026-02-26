(function () {
  const tenantId = window.platformTenantDetailTenantId;
  if (!tenantId) return;

  const title = document.getElementById('platform-tenant-detail-title');
  const message = document.getElementById('platform-tenant-detail-message');
  const basic = document.getElementById('platform-tenant-detail-basic');
  const companiesRoot = document.getElementById('platform-tenant-detail-companies');
  const usersRoot = document.getElementById('platform-tenant-detail-users');

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
    message.classList.toggle('is-success', !isError && Boolean(text));
  };

  const renderSimpleList = (root, items, renderItem, emptyText) => {
    if (!root) return;
    if (!items.length) {
      root.innerHTML = `<p class="ff-empty">${emptyText}</p>`;
      return;
    }

    root.innerHTML = `<ul>${items.map(renderItem).join('')}</ul>`;
  };

  const load = async () => {
    setMessage('Cargando detalle…');
    try {
      const response = await window.apiFetch(`/platform/tenants/${tenantId}`);
      const tenant = response?.tenant;
      if (!tenant) throw new Error('tenant_not_found');

      title.textContent = `Detalle de gestoría · ${tenant.name || '-'}`;
      basic.innerHTML = `
        <p><b>ID:</b> <code>${tenant.id}</code></p>
        <p><b>Estado:</b> ${tenant.status || '-'}</p>
        <p><b>Plan:</b> ${tenant.plan || '-'}</p>
        <p><b>Fecha alta:</b> ${tenant.created_at || '-'}</p>
        <p><b>Métricas:</b> Empresas ${tenant.metrics?.companies || 0} · Usuarios ${tenant.metrics?.users || 0}</p>
      `;

      renderSimpleList(
        companiesRoot,
        tenant.companies || [],
        (company) => `<li><b>${company.name || '-'}</b> · ${company.tax_id || '-'} · ${company.status || '-'}</li>`,
        'No hay empresas disponibles para este tenant.'
      );

      renderSimpleList(
        usersRoot,
        tenant.users || [],
        (user) => `<li><b>${user.email || '-'}</b> · ${user.status || '-'}</li>`,
        'No hay usuarios disponibles para este tenant.'
      );

      setMessage('');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo cargar el detalle del tenant.' });
      setMessage('No se pudo cargar el detalle del tenant.', true);
    }
  };

  load();
})();
