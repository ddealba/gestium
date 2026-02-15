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
    const payload = {
      email: String(formData.get('email') || '').trim(),
      password: String(formData.get('password') || ''),
    };

    const clientId = String(formData.get('client_id') || '').trim();
    if (clientId) {
      payload.client_id = clientId;
    }

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok || !data.access_token) {
        setMessage('No se pudo iniciar sesión. Revisa tus credenciales.', true);
        return;
      }

      localStorage.setItem('gestium_access_token', data.access_token);
      setMessage('Login correcto. Redirigiendo…');
      window.location.assign('/app/companies');
    } catch (error) {
      setMessage('Error de conexión con el servidor.', true);
    }
  });
})();
