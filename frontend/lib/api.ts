const API_URL = "http://localhost:8000/api";

export function decodeJwtPayload(token: string): Record<string, any> | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

export function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  if (!payload || !payload.exp) return false;
  // Adăugăm 30s marjă
  return payload.exp * 1000 > Date.now() + 30_000;
}

export async function apiRequest(
  endpoint: string,
  options: RequestInit = {}
) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Verificăm expirarea înainte de orice request
  if (token && !isTokenValid(token)) {
    logout();
    return new Response(null, { status: 401 });
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    logout();
  }

  return response;
}

export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("user_name");
    localStorage.removeItem("table_id");
    window.location.href = "/login";
  }
}

export function getStoredUser(): { role: string | null; name: string | null } {
  if (typeof window === "undefined") return { role: null, name: null };
  return {
    role: localStorage.getItem("user_role"),
    name: localStorage.getItem("user_name"),
  };
}
