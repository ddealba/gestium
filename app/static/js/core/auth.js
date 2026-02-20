(function () {
  const login = async (email, password, clientId) => {
    const payload = { email, password };
    if (clientId) {
      payload.client_id = clientId;
    }

    const data = await window.apiFetch('/auth/login', {
      method: 'POST',
      body: payload,
    });

    if (data?.access_token) {
      window.setToken(data.access_token);
    }

    return data;
  };

  const me = () => window.apiFetch('/auth/me');

  const logout = () => {
    window.clearToken();
    window.location.href = '/app/login';
  };

  window.auth = {
    login,
    me,
    logout,
  };
})();
