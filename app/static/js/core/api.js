import { clearToken, getToken } from "/static/js/core/auth.js";

function hasJsonBody(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json");
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  const requestInit = { ...options, headers };

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (requestInit.body && !(requestInit.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, requestInit);

  if (response.status === 401) {
    clearToken();
    window.location.href = "/app/login";
    throw { status: 401, data: { message: "unauthorized" } };
  }

  const data = hasJsonBody(response) ? await response.json() : null;

  if (!response.ok) {
    throw { status: response.status, data };
  }

  return data;
}
