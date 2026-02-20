(function () {
  const form = document.getElementById('login-form');
  if (!form) return;

  const message = document.getElementById('login-message');

  const setMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle('is-error', isError);
    message.classList.toggle('is-success', !isError && Boolean(text));
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setMessage('Validando credenciales…');

    const formData = new FormData(form);
    const email = String(formData.get('email') || '').trim();
    const password = String(formData.get('password') || '');
    const clientId = String(formData.get('client_id') || '').trim();

    try {
      const data = await window.auth.login(email, password, clientId || null);
      if (!data?.access_token) {
        setMessage(data?.message || 'No se pudo iniciar sesión. Revisa tus credenciales.', true);
        return;
      }

      setMessage('Login correcto. Redirigiendo…');
      window.location.href = '/app/companies';
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo iniciar sesión.' });
      setMessage(window.extractErrorMessage(error) || 'No se pudo iniciar sesión.', true);
    }
  });
})();
