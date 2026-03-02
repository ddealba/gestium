(function () {
  const SUPER_ADMIN_KEY = 'is_super_admin';
  const TENANT_ID_KEY = 'admin_selected_tenant_id';
  const TENANT_NAME_KEY = 'admin_selected_tenant_name';

  const getPageId = () => document.body?.dataset?.page || '';

  const isPlatformPage = () => getPageId().startsWith('platform_');

  const hasTenantSelection = () => Boolean(sessionStorage.getItem(TENANT_ID_KEY));

  const getTenantName = () => sessionStorage.getItem(TENANT_NAME_KEY) || '';

  const isSuperAdmin = () => sessionStorage.getItem(SUPER_ADMIN_KEY) === 'true';

  const shouldShowTenantMenu = () => !isSuperAdmin() || (hasTenantSelection() && !isPlatformPage());

  const shouldShowPlatformMenu = () => isSuperAdmin() && (!hasTenantSelection() || isPlatformPage());

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

  const renderSidebarByContext = () => {
    const navItems = document.querySelectorAll('.ff-nav [data-nav-scope]');
    navItems.forEach((item) => {
      const scope = item.dataset.navScope;
      let visible = true;

      if (scope === 'tenant') {
        visible = shouldShowTenantMenu();
      } else if (scope === 'platform') {
        visible = shouldShowPlatformMenu();
      } else if (scope === 'platform_optional') {
        visible = shouldShowPlatformMenu();
      }

      item.hidden = !visible;
    });

    const navGroups = document.querySelectorAll('.ff-nav__group');
    navGroups.forEach((group) => {
      const visibleChildren = group.querySelectorAll('.ff-nav__subitem:not([hidden])');
      group.hidden = visibleChildren.length === 0;
    });
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
    renderSidebarByContext();
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
    renderSidebarByContext,
    renderTenantContextBanner,
    requireTenantSelection,
  };
})();
