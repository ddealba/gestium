(function () {
  const form = document.getElementById('person-form');
  const message = document.getElementById('person-form-message');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      first_name: (formData.get('first_name') || '').toString().trim(),
      last_name: (formData.get('last_name') || '').toString().trim(),
      document_number: (formData.get('document_number') || '').toString().trim(),
      email: (formData.get('email') || '').toString().trim() || null,
      phone: (formData.get('phone') || '').toString().trim() || null,
    };

    try {
      const response = await window.apiFetch('/persons', {
        method: 'POST',
        body: payload,
      });
      message.textContent = 'Persona creada correctamente.';
      message.classList.remove('is-error');
      window.location.href = `/app/persons/${response?.person?.id}`;
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo crear la persona.' });
      message.textContent = error?.message || 'No se pudo crear la persona.';
      message.classList.add('is-error');
    }
  });
})();
