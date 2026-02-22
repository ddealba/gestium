(function () {
  const companySelect = document.getElementById('admin-access-company-select');
  if (!companySelect) return;

  const tableBody = document.querySelector('#admin-access-table tbody');
  const pageMessage = document.getElementById('admin-access-message');
  const addForm = document.getElementById('admin-access-add-form');
  const userSelect = document.getElementById('admin-access-user-select');
  const levelSelect = document.getElementById('admin-access-level-select');
  const addSubmit = document.getElementById('admin-access-add-submit');
  const addMessage = document.getElementById('admin-access-add-message');

  const ACCESS_LEVELS = ['viewer', 'operator', 'manager', 'admin'];

  let companies = [];
  let users = [];
  let selectedCompanyId = null;

  const setMessage = (element, text, isError = false) => {
    if (!element) return;
    element.textContent = text;
    element.classList.toggle('is-error', isError);
    element.classList.toggle('is-success', !isError && Boolean(text));
  };

  const renderCompanies = () => {
    companySelect.innerHTML = '';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = companies.length ? 'Selecciona una empresa' : 'Sin empresas disponibles';
    companySelect.appendChild(placeholder);

    companies.forEach((company) => {
      const option = document.createElement('option');
      option.value = company.id;
      option.textContent = company.name || company.tax_id || company.id;
      companySelect.appendChild(option);
    });
  };

  const renderUsers = () => {
    userSelect.innerHTML = '';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = users.length ? 'Selecciona un usuario' : 'Sin usuarios disponibles';
    userSelect.appendChild(placeholder);

    users.forEach((user) => {
      const option = document.createElement('option');
      option.value = user.id;
      option.textContent = user.email || user.id;
      userSelect.appendChild(option);
    });
  };

  const makeLevelSelect = (selected) => {
    const select = document.createElement('select');
    select.className = 'ff-select';

    ACCESS_LEVELS.forEach((level) => {
      const option = document.createElement('option');
      option.value = level;
      option.textContent = level;
      if (level === selected) option.selected = true;
      select.appendChild(option);
    });

    return select;
  };

  const renderAccessRows = (items) => {
    tableBody.innerHTML = '';

    if (!items.length) {
      tableBody.innerHTML = '<tr><td colspan="3" class="ff-empty">No hay accesos para esta empresa.</td></tr>';
      return;
    }

    items.forEach((item) => {
      const row = document.createElement('tr');

      const emailCell = document.createElement('td');
      emailCell.textContent = item.email || '-';

      const levelCell = document.createElement('td');
      const levelDropdown = makeLevelSelect(item.access_level);
      levelCell.appendChild(levelDropdown);

      const actionsCell = document.createElement('td');
      const actionsWrap = document.createElement('div');
      actionsWrap.style.display = 'flex';
      actionsWrap.style.gap = '.5rem';
      actionsWrap.style.flexWrap = 'wrap';

      const saveButton = document.createElement('button');
      saveButton.type = 'button';
      saveButton.className = 'ff-btn ff-btn--ghost ff-btn--sm';
      saveButton.textContent = 'Guardar cambios';
      saveButton.dataset.action = 'save-access';
      saveButton.dataset.userId = item.user_id;

      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.className = 'ff-btn ff-btn--ghost ff-btn--sm';
      deleteButton.textContent = 'Eliminar';
      deleteButton.dataset.action = 'delete-access';
      deleteButton.dataset.userId = item.user_id;

      actionsWrap.append(saveButton, deleteButton);
      actionsCell.appendChild(actionsWrap);

      row.append(emailCell, levelCell, actionsCell);
      tableBody.appendChild(row);
    });
  };

  const loadAccessForCompany = async (companyId) => {
    if (!companyId) {
      selectedCompanyId = null;
      renderAccessRows([]);
      return;
    }

    selectedCompanyId = companyId;
    setMessage(pageMessage, 'Cargando accesos…');

    try {
      const response = await window.apiFetch(`/admin/companies/${companyId}/access`);
      renderAccessRows(response?.items || []);
      setMessage(pageMessage, '');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar los accesos.' });
      renderAccessRows([]);
      setMessage(pageMessage, 'No se pudieron cargar los accesos.', true);
    }
  };

  const loadInitialData = async () => {
    setMessage(pageMessage, 'Cargando empresas y usuarios…');

    try {
      const [companiesResponse, usersResponse] = await Promise.all([
        window.apiFetch('/admin/companies'),
        window.apiFetch('/admin/users'),
      ]);

      companies = companiesResponse?.items || [];
      users = usersResponse?.items || [];
      renderCompanies();
      renderUsers();
      setMessage(pageMessage, '');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar empresas o usuarios.' });
      setMessage(pageMessage, 'No se pudieron cargar empresas o usuarios.', true);
    }
  };

  const addAccess = async (event) => {
    event.preventDefault();
    setMessage(addMessage, '');

    const companyId = selectedCompanyId;
    const userId = userSelect.value;
    const accessLevel = levelSelect.value;

    if (!companyId) {
      setMessage(addMessage, 'Selecciona una empresa primero.', true);
      return;
    }

    if (!userId) {
      setMessage(addMessage, 'Selecciona un usuario.', true);
      return;
    }

    addSubmit.disabled = true;

    try {
      await window.apiFetch(`/admin/companies/${companyId}/access`, {
        method: 'POST',
        body: {
          user_id: userId,
          access_level: accessLevel,
        },
      });

      setMessage(addMessage, 'Acceso añadido correctamente.');
      await loadAccessForCompany(companyId);
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo añadir el acceso.' });
      setMessage(addMessage, 'No se pudo añadir el acceso.', true);
    } finally {
      addSubmit.disabled = false;
    }
  };

  tableBody?.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button || !selectedCompanyId) return;

    const { userId, action } = button.dataset;
    if (!userId) return;

    if (action === 'save-access') {
      const row = button.closest('tr');
      const levelDropdown = row?.querySelector('select');
      const accessLevel = levelDropdown?.value;

      if (!accessLevel) return;

      button.disabled = true;
      setMessage(pageMessage, 'Guardando cambios…');

      try {
        await window.apiFetch(`/admin/companies/${selectedCompanyId}/access/${userId}`, {
          method: 'PATCH',
          body: {
            access_level: accessLevel,
          },
        });

        setMessage(pageMessage, 'Cambios guardados correctamente.');
      } catch (error) {
        window.handleApiError(error, { defaultMessage: 'No se pudo actualizar el nivel de acceso.' });
        setMessage(pageMessage, 'No se pudo actualizar el nivel de acceso.', true);
      } finally {
        button.disabled = false;
      }

      return;
    }

    if (action === 'delete-access') {
      button.disabled = true;
      setMessage(pageMessage, 'Eliminando acceso…');

      try {
        await window.apiFetch(`/admin/companies/${selectedCompanyId}/access/${userId}`, {
          method: 'DELETE',
        });

        await loadAccessForCompany(selectedCompanyId);
        setMessage(pageMessage, 'Acceso eliminado.');
      } catch (error) {
        window.handleApiError(error, { defaultMessage: 'No se pudo eliminar el acceso.' });
        setMessage(pageMessage, 'No se pudo eliminar el acceso.', true);
      } finally {
        button.disabled = false;
      }
    }
  });

  companySelect.addEventListener('change', (event) => {
    const companyId = event.target.value;
    setMessage(addMessage, '');
    loadAccessForCompany(companyId);
  });

  addForm?.addEventListener('submit', addAccess);

  loadInitialData();
})();
