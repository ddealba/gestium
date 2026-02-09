import { clearToken, me } from "/static/js/core/auth.js";

export async function requireAuth() {
  try {
    return await me();
  } catch (_error) {
    clearToken();
    window.location.href = "/app/login";
    throw _error;
  }
}
