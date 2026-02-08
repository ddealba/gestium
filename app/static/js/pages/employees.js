import { apiFetch } from "/static/js/core/api.js";
import { requireAuth } from "/static/js/core/guard.js";

const tbody = document.getElementById("employeesTbody");
const form = document.getElementById("createEmployeeForm");
const root = document.getElementById("employeesPageRoot");
const companyId = root?.dataset?.companyId || window.__COMPANY_ID__;

function showApiError(error) {
  if (error?.status === 403 || error?.status === 404) {
    window.GestiumUI?.showToast?.("error", "No tienes permisos o no tienes acceso");
    return;
  }
  window.GestiumUI?.showToast?.("error", "Error");
}

function statusBadge(status) {
  const tone = status === "active" ? "success" : "warning";
  return `<span class="badge badge--${tone}">${status}</span>`;
}

function renderEmployees(employees) {
  if (!tbody) return;

  if (!employees.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted)">Sin empleados</td></tr>';
    return;
  }

  tbody.innerHTML = employees
    .map(
      (employee) => `
      <tr>
        <td>${employee.full_name}</td>
        <td>${employee.start_date || "-"}</td>
        <td>${employee.end_date || "-"}</td>
        <td>${statusBadge(employee.status)}</td>
        <td>
          ${employee.status === "active"
            ? `<div class="row" style="gap:8px;align-items:center;">
                <input class="input" type="date" data-end-date="${employee.id}" style="max-width:170px;">
                <button class="btn" type="button" data-terminate-employee="${employee.id}">Terminate</button>
              </div>`
            : "-"}
        </td>
      </tr>
    `,
    )
    .join("");
}

async function loadEmployees() {
  try {
    const data = await apiFetch(`/companies/${companyId}/employees`);
    renderEmployees(data?.employees || []);
  } catch (error) {
    showApiError(error);
  }
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);

  try {
    await apiFetch(`/companies/${companyId}/employees`, {
      method: "POST",
      body: JSON.stringify({
        full_name: String(formData.get("full_name") || "").trim(),
        start_date: String(formData.get("start_date") || "").trim(),
      }),
    });
    form.reset();
    window.GestiumUI?.showToast?.("success", "Empleado creado");
    await loadEmployees();
  } catch (error) {
    showApiError(error);
  }
});

tbody?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-terminate-employee]");
  if (!button) return;

  const employeeId = button.getAttribute("data-terminate-employee");
  const endDateInput = document.querySelector(`[data-end-date="${employeeId}"]`);
  const endDate = String(endDateInput?.value || "").trim();

  if (!endDate) {
    window.GestiumUI?.showToast?.("warning", "Selecciona end_date");
    return;
  }

  try {
    await apiFetch(`/companies/${companyId}/employees/${employeeId}/terminate`, {
      method: "POST",
      body: JSON.stringify({ end_date: endDate }),
    });
    window.GestiumUI?.showToast?.("success", "Empleado terminado");
    await loadEmployees();
  } catch (error) {
    showApiError(error);
  }
});

(async function init() {
  await requireAuth();
  await loadEmployees();
})();
