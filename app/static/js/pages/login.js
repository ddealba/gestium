import { login } from "/static/js/core/auth.js";

const form = document.getElementById("loginForm");
const errorNode = document.getElementById("loginError");

function showError(message) {
  if (errorNode) {
    errorNode.textContent = message;
  }
  window.GestiumUI?.showToast?.("error", message);
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "");

  try {
    await login(email, password);
    window.location.href = "/app/companies";
  } catch (_error) {
    showError("No se pudo iniciar sesión. Revisa tus credenciales.");
  }
});
