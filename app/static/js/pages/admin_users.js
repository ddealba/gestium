(function () {
  const table = document.getElementById('admin-users-table');
  if (!table) return;

  if (window.tenantContext?.requireTenantSelection?.()) return;

  const tbody = table.querySelector('tbody');
  const pageMessage = document.getElementById('admin-users-message');
  const refreshButton = document.getElementById('refresh-admin-users');

  const inviteForm = document.getElementById('invite-user-form');
  const inviteEmailInput = document.getElementById('invite-email');
  const inviteRolesSelect = document.getElementById('invite-roles');
  const inviteMessage = document.getElementById('invite-user-message');
  const inviteSubmit = document.getElementById('invite-submit');

  const editRolesModal = document.getElementById('edit-roles-modal');
  const closeModalButton = document.getElementById('close-edit-roles-modal');
  const editRolesUserEmail = document.getElementById('edit-roles-user-email');
  const editRolesChecklist = document.getElementById('edit-roles-checklist');
  const editRolesForm = document.getElementById('edit-roles-form');
  const editRolesMessage = document.getElementById('edit-roles-message');
  const saveRolesButton = document.getElementById('save-roles-button');

  let roles = [];
  let users = [];
  let activeEditUser = null;

  const setMessage = (element, text, isError = false) => {
    if (!element) return;
    element.textContent = text;
    element.classList.toggle('is-error', isError);
    element.classList.toggle('is-success', !isError && Boolean(text));
  };

  const roleNames = (user) => (user.roles || []).map((role) => role.name).join(', ');

  const statusVariant = (status) => {
    switch (status) {
      case 'active':
        return 'ff-tag--success';
      case 'invited':
        return 'ff-tag--blue';
      case 'disabled':
        return 'ff-tag--warn';
      default:
        return 'ff-tag--danger';
    }
  };

  const selectedValues = (selectElement) =>
    Array.from(selectElement?.selectedOptions || []).map((option) => option.value);

  const renderRoleOptions = () => {
    inviteRolesSelect.innerHTML = '';

    roles.forEach((role) => {
      const option = document.createElement('option');
      option.value = role.id;
      option.textContent = `${role.name} (${role.scope})`;
      inviteRolesSelect.appendChild(option);
    });
  };

  const renderUsers = () => {
    tbody.innerHTML = '';

    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="ff-empty">No hay usuarios para mostrar.</td></tr>';
      return;
    }

    users.forEach((user) => {
      const row = document.createElement('tr');
      const enableDisableLabel = user.status === 'disabled' ? 'Enable' : 'Disable';

      row.innerHTML = `
        <td>${user.email || '-'}</td>
        <td><span class="ff-tag ${statusVariant(user.status)}">${user.status || '-'}</span></td>
        <td>${roleNames(user) || '-'}</td>
        <td>
          <div style="display:flex; gap:.5rem; flex-wrap:wrap;">
            <button type="button" class="ff-btn ff-btn--ghost" data-action="toggle-status" data-user-id="${user.id}">${enableDisableLabel}</button>
            <button type="button" class="ff-btn ff-btn--ghost" data-action="edit-roles" data-user-id="${user.id}">Edit roles</button>
          </div>
        </td>
      `;

      tbody.appendChild(row);
    });
  };

  const loadRoles = async () => {
    const response = await window.apiFetch('/admin/roles');
    roles = response?.items || [];
    renderRoleOptions();
  };

  const loadUsers = async () => {
    const response = await window.apiFetch('/admin/users');
    users = response?.items || [];
    renderUsers();
  };

  const refreshAll = async () => {
    setMessage(pageMessage, 'Cargando usuarios…');

    try {
      await Promise.all([loadRoles(), loadUsers()]);
      setMessage(pageMessage, '');
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron cargar usuarios o roles.' });
      setMessage(pageMessage, 'No se pudieron cargar usuarios o roles.', true);
    }
  };

  const inviteUser = async (event) => {
    event.preventDefault();
    setMessage(inviteMessage, '');

    const email = inviteEmailInput.value.trim();
    const roleIds = selectedValues(inviteRolesSelect);

    if (!email) {
      setMessage(inviteMessage, 'El email es requerido.', true);
      return;
    }

    inviteSubmit.disabled = true;

    try {
      await window.apiFetch('/admin/users/invite', {
        method: 'POST',
        body: {
          email,
          role_ids: roleIds,
        },
      });

      inviteForm.reset();
      setMessage(inviteMessage, 'Invitación enviada correctamente.');
      await loadUsers();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo invitar al usuario.' });
      setMessage(inviteMessage, 'No se pudo invitar al usuario.', true);
    } finally {
      inviteSubmit.disabled = false;
    }
  };

  const closeEditRolesModal = () => {
    editRolesModal.classList.remove('is-open');
    editRolesModal.setAttribute('aria-hidden', 'true');
    activeEditUser = null;
    setMessage(editRolesMessage, '');
    editRolesChecklist.innerHTML = '';
    editRolesUserEmail.textContent = '';
  };

  const openEditRolesModal = (user) => {
    activeEditUser = user;
    editRolesUserEmail.textContent = user.email;
    editRolesChecklist.innerHTML = '';

    const currentRoleIds = new Set((user.roles || []).map((role) => role.id));

    roles.forEach((role) => {
      const label = document.createElement('label');
      label.style.display = 'flex';
      label.style.gap = '.5rem';
      label.style.alignItems = 'center';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = role.id;
      checkbox.checked = currentRoleIds.has(role.id);

      const text = document.createElement('span');
      text.textContent = `${role.name} (${role.scope})`;

      label.appendChild(checkbox);
      label.appendChild(text);
      editRolesChecklist.appendChild(label);
    });

    editRolesModal.classList.add('is-open');
    editRolesModal.setAttribute('aria-hidden', 'false');
  };

  const toggleUserStatus = async (user) => {
    const endpoint = user.status === 'disabled' ? 'enable' : 'disable';

    try {
      await window.apiFetch(`/admin/users/${user.id}/${endpoint}`, { method: 'POST' });
      await loadUsers();
      window.showToast('success', `Usuario ${endpoint === 'enable' ? 'habilitado' : 'deshabilitado'}.`);
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudo actualizar el estado del usuario.' });
    }
  };

  const saveRoles = async (event) => {
    event.preventDefault();
    if (!activeEditUser) return;

    const roleIds = Array.from(editRolesChecklist.querySelectorAll('input[type="checkbox"]:checked')).map(
      (item) => item.value,
    );

    saveRolesButton.disabled = true;

    try {
      await window.apiFetch(`/admin/users/${activeEditUser.id}/roles`, {
        method: 'PUT',
        body: { role_ids: roleIds },
      });

      setMessage(editRolesMessage, 'Roles actualizados correctamente.');
      await loadUsers();
      closeEditRolesModal();
    } catch (error) {
      window.handleApiError(error, { defaultMessage: 'No se pudieron actualizar los roles.' });
      setMessage(editRolesMessage, 'No se pudieron actualizar los roles.', true);
    } finally {
      saveRolesButton.disabled = false;
    }
  };

  table.addEventListener('click', async (event) => {
    const trigger = event.target.closest('button[data-action]');
    if (!trigger) return;

    const userId = trigger.dataset.userId;
    const user = users.find((item) => item.id === userId);
    if (!user) return;

    if (trigger.dataset.action === 'toggle-status') {
      await toggleUserStatus(user);
      return;
    }

    if (trigger.dataset.action === 'edit-roles') {
      openEditRolesModal(user);
    }
  });

  editRolesModal?.addEventListener('click', (event) => {
    if (event.target?.dataset?.closeModal === 'true') {
      closeEditRolesModal();
    }
  });

  closeModalButton?.addEventListener('click', closeEditRolesModal);
  refreshButton?.addEventListener('click', refreshAll);
  inviteForm?.addEventListener('submit', inviteUser);
  editRolesForm?.addEventListener('submit', saveRoles);

  refreshAll();
})();
