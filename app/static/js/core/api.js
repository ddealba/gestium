(function () {
  const TOKEN_KEYS = ['gestium_access_token', 'access_token'];

  const pickTokenFromStorage = (storage) => {
    for (const key of TOKEN_KEYS) {
      const token = storage.getItem(key);
      if (token) return token;
    }
    return null;
  };

  const getToken = () => pickTokenFromStorage(sessionStorage);

  const setToken = (token) => {
    TOKEN_KEYS.forEach((key) => {
      if (key === TOKEN_KEYS[0]) {
        sessionStorage.setItem(key, token);
      } else {
        sessionStorage.removeItem(key);
      }
    });
  };

  const clearToken = () => {
    TOKEN_KEYS.forEach((key) => sessionStorage.removeItem(key));
  };

  const migrateTokenFromLocalStorage = () => {
    const legacyToken = pickTokenFromStorage(localStorage);
    if (!legacyToken) return;

    setToken(legacyToken);
    TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
  };

  const showToast = (type, text) => {
    let wrap = document.querySelector('.ff-toast-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'ff-toast-wrap';
      document.body.appendChild(wrap);
    }

    const toast = document.createElement('div');
    toast.className = 'ff-toast';
    if (type) toast.dataset.type = type;
    toast.textContent = text;
    wrap.appendChild(toast);

    setTimeout(() => {
      toast.remove();
      if (!wrap.children.length) wrap.remove();
    }, 2600);
  };

  const parseResponseData = async (response) => {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        return await response.json();
      } catch (error) {
        return null;
      }
    }

    try {
      const text = await response.text();
      return text || null;
    } catch (error) {
      return null;
    }
  };

  const apiFetch = async (path, { method = 'GET', headers = {}, body, formData } = {}) => {
    const requestHeaders = { ...headers };
    const token = getToken();
    const isSuperAdmin = sessionStorage.getItem('is_super_admin') === 'true';
    const selectedTenantId = sessionStorage.getItem('admin_selected_tenant_id');

    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }

    if (isSuperAdmin && selectedTenantId) {
      requestHeaders['X-Admin-Tenant'] = selectedTenantId;
    }

    const options = { method, headers: requestHeaders };

    if (formData) {
      options.body = formData;
      delete requestHeaders['Content-Type'];
      delete requestHeaders['content-type'];
    } else if (body !== undefined) {
      if (typeof body === 'object' && body !== null) {
        requestHeaders['Content-Type'] = requestHeaders['Content-Type'] || 'application/json';
        options.body = JSON.stringify(body);
      } else {
        options.body = body;
      }
    }

    const response = await fetch(path, options);
    const data = await parseResponseData(response);

    if (response.status === 401) {
      clearToken();
      window.location.href = '/app/login';
    }

    if (response.status >= 400) {
      const backendMessage = data?.error?.message || data?.message;
      const error = new Error(backendMessage || 'API error');
      error.status = response.status;
      error.data = data;
      error.noAccess = response.status === 403 || response.status === 404;
      error.message = backendMessage || error.message;
      throw error;
    }

    return data;
  };

  migrateTokenFromLocalStorage();

  window.getToken = getToken;
  window.setToken = setToken;
  window.clearToken = clearToken;
  window.migrateTokenFromLocalStorage = migrateTokenFromLocalStorage;
  window.apiFetch = apiFetch;
  window.showToast = window.showToast || showToast;
})();
