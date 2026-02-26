(function () {
  const form = document.getElementById('platform-tenant-new-form');
  if (!form) return;

  const message = document.getElementById('platform-tenant-new-message');
  const submitButton = document.getElementById('tenant-new-submit');

  const nameInput = document.getElementById('tenant-name');
  const planInput = document.getElementById('tenant-plan');
  const statusInput = document.getElementById('tenant-status');
  const logoUrlInput = document.getElementById('tenant-logo-url');
  const adminEmailInput = document.getElementById('tenant-admin-email');

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
    message.classList.toggle('is-success', !isError && Boolean(text));
  };

  const redirectNoAccess = () => {
    window.showToast('error', 'No tienes permisos de Super Admin');
    setTimeout(() => {
      window.location.href = '/app/companies';
    }, 800);
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setMessage('');

    const payload = {
      name: nameInput.value.trim(),
      plan: planInput.value,
      status: statusInput.value,
      logo_url: logoUrlInput.value.trim() || null,
      admin_email: adminEmailInput.value.trim() || null,
    };

    if (!payload.name) {
      setMessage('El nombre es obligatorio.', true);
      return;
    }

    submitButton.disabled = true;
    setMessage('Creando gestoría…');

    try {
      await window.apiFetch('/platform/tenants', {
        method: 'POST',
        body: payload,
      });
      window.showToast('success', 'Gestoría creada correctamente.');
      window.location.href = '/app/platform/tenants';
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo crear la gestoría.' });
      if (error?.status === 403) {
        redirectNoAccess();
        return;
      }
      setMessage('No se pudo crear la gestoría.', true);
    } finally {
      submitButton.disabled = false;
    }
  });
})();
