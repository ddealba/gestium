(function () {
  const SUPER_ADMIN_KEY = 'is_super_admin';
  const TENANT_ID_KEY = 'admin_selected_tenant_id';
  const TENANT_NAME_KEY = 'admin_selected_tenant_name';

  const getPageId = () => document.body?.dataset?.page || '';

  const isPlatformPage = () => getPageId().startsWith('platform_');

  const hasTenantSelection = () => Boolean(sessionStorage.getItem(TENANT_ID_KEY));

  const getTenantName = () => sessionStorage.getItem(TENANT_NAME_KEY) || '';

  const isSuperAdmin = () => sessionStorage.getItem(SUPER_ADMIN_KEY) === 'true';

  const clearSelectedTenant = () => {
    sessionStorage.removeItem(TENANT_ID_KEY);
    sessionStorage.removeItem(TENANT_NAME_KEY);
  };

  const renderTenantContextBanner = () => {
    const banner = document.getElementById('tenant-context-banner');
    const tenantNameLabel = document.getElementById('tenant-context-name');
    if (!banner || !tenantNameLabel) return;

    const shouldShow = isSuperAdmin() && hasTenantSelection() && !isPlatformPage();
    banner.hidden = !shouldShow;
    if (!shouldShow) return;

    tenantNameLabel.textContent = getTenantName() || 'Tenant';
  };

  const redirectToTenantSelection = () => {
    window.location.href = '/app/platform/tenants';
  };

  const requireTenantSelection = () => {
    if (!isSuperAdmin() || isPlatformPage() || hasTenantSelection()) {
      return false;
    }

    window.showToast('error', 'Selecciona una gestoría para administrar');
    setTimeout(redirectToTenantSelection, 500);
    return true;
  };

  const bindExitButton = () => {
    const exitButton = document.getElementById('tenant-context-exit');
    if (!exitButton) return;

    exitButton.addEventListener('click', () => {
      clearSelectedTenant();
      redirectToTenantSelection();
    });
  };

  const bootstrapTenantContext = async () => {
    if (!window.auth?.me) {
      renderTenantContextBanner();
      return;
    }

    try {
      const me = await window.auth.me();
      sessionStorage.setItem(SUPER_ADMIN_KEY, String(Boolean(me?.is_super_admin)));
    } catch (error) {
      if (error?.status !== 401) {
        sessionStorage.setItem(SUPER_ADMIN_KEY, 'false');
      }
    }

    if (requireTenantSelection()) return;
    renderTenantContextBanner();
  };

  bindExitButton();
  bootstrapTenantContext();

  window.tenantContext = {
    SUPER_ADMIN_KEY,
    TENANT_ID_KEY,
    TENANT_NAME_KEY,
    clearSelectedTenant,
    hasTenantSelection,
    isSuperAdmin,
    renderTenantContextBanner,
    requireTenantSelection,
  };
})();
