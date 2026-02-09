const TOKEN_KEY = "gestium_access_token";

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function login(email, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = (response.headers.get("content-type") || "").includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw { status: response.status, data };
  }

  if (data?.access_token) {
    setToken(data.access_token);
  }

  return data;
}

export async function me() {
  const token = getToken();
  if (!token) {
    throw { status: 401, data: { message: "missing_token" } };
  }

  const response = await fetch("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = (response.headers.get("content-type") || "").includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw { status: response.status, data };
  }

  return data;
}

export function logout() {
  clearToken();
  window.location.href = "/app/login";
}
