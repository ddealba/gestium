import { apiFetch } from "/static/js/core/api.js";
import { requireAuth } from "/static/js/core/guard.js";

const tbody = document.getElementById("companiesTbody");
const createForm = document.getElementById("createCompanyForm");
const refreshBtn = document.getElementById("refreshCompaniesBtn");

function statusBadge(status) {
  const tone = status === "active" ? "success" : "warning";
  return `<span class="badge badge--${tone}">${status}</span>`;
}

function showApiError(error) {
  if (error?.status === 403 || error?.status === 404) {
    window.GestiumUI?.showToast?.("error", "No tienes permisos o no tienes acceso");
    return;
  }
  window.GestiumUI?.showToast?.("error", "Error");
}

function renderCompanies(companies) {
  if (!tbody) return;

  if (!companies.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted)">Sin companies disponibles</td></tr>';
    return;
  }

  tbody.innerHTML = companies
    .map(
      (company) => `
      <tr>
        <td>${company.name}</td>
        <td>${company.tax_id}</td>
        <td>${statusBadge(company.status)}</td>
        <td>
          <div class="row" style="gap:8px;">
            <a class="btn" href="/app/companies/${company.id}/employees">Employees</a>
            <button class="btn" type="button" data-toggle-company="${company.id}" data-next-status="${company.status === "active" ? "deactivate" : "activate"}">
              ${company.status === "active" ? "Deactivate" : "Activate"}
            </button>
          </div>
        </td>
      </tr>
    `,
    )
    .join("");
}

async function loadCompanies() {
  try {
    const data = await apiFetch("/companies");
    renderCompanies(data?.companies || []);
  } catch (error) {
    showApiError(error);
  }
}

tbody?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-toggle-company]");
  if (!button) return;

  const companyId = button.getAttribute("data-toggle-company");
  const action = button.getAttribute("data-next-status");

  try {
    await apiFetch(`/companies/${companyId}/${action}`, { method: "POST" });
    window.GestiumUI?.showToast?.("success", "Estado actualizado");
    await loadCompanies();
  } catch (error) {
    showApiError(error);
  }
});

createForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(createForm);

  const name = String(formData.get("name") || "").trim();
  const taxId = String(formData.get("tax_id") || "").trim();

  try {
    await apiFetch("/companies", {
      method: "POST",
      body: JSON.stringify({ name, tax_id: taxId }),
    });
    createForm.reset();
    window.GestiumUI?.showToast?.("success", "Company creada");
    await loadCompanies();
  } catch (error) {
    showApiError(error);
  }
});

refreshBtn?.addEventListener("click", loadCompanies);

(async function init() {
  await requireAuth();
  await loadCompanies();
})();
