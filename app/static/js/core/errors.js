(function () {
  const extractErrorMessage = (err) => {
    const message = err?.data?.error?.message || err?.data?.message || (typeof err === 'string' ? err : null);
    return message || 'Error inesperado';
  };

  const handleApiError = (err, { defaultMessage = null, onNoAccess = null } = {}) => {
    if (err?.status === 401) {
      return;
    }

    if (err?.noAccess === true) {
      window.showToast('error', 'No tienes acceso');
      if (typeof onNoAccess === 'function') {
        onNoAccess();
      }
      return;
    }

    switch (err?.status) {
      case 400:
        window.showToast('error', extractErrorMessage(err) || defaultMessage || 'Solicitud inválida');
        return;
      case 413:
        window.showToast('error', 'Archivo demasiado grande');
        return;
      case 404:
      case 403:
        window.showToast('error', 'No tienes acceso');
        return;
      default:
        if (typeof err?.status === 'number' && err.status >= 500) {
          window.showToast('error', 'Error interno. Inténtalo más tarde.');
          return;
        }
        window.showToast('error', defaultMessage || extractErrorMessage(err) || 'Error');
    }
  };

  const withErrorHandling = (asyncFn, options) => async (...args) => {
    try {
      return await asyncFn(...args);
    } catch (err) {
      handleApiError(err, options);
      return null;
    }
  };

  window.extractErrorMessage = extractErrorMessage;
  window.handleApiError = handleApiError;
  window.withErrorHandling = withErrorHandling;
})();
