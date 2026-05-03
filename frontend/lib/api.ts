const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function decodeJwtPayload(token: string): any {
  if (!token || typeof token !== "string" || token === "undefined" || token === "null") {
    return null;
  }
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    // Add padding if missing
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch (error) {
    console.error("JWT Decode Error:", error);
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
    return new Response(JSON.stringify({ detail: "Token expirat. Te rugăm să te autentifici din nou." }), { status: 401, headers: { "Content-Type": "application/json" } });
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
    localStorage.removeItem("table_id");
    setTimeout(() => {
      window.location.href = "/login";
    }, 0);
  }
}

/**
 * Retrieve user name and role from the stored JWT payload (L2 fix).
 * No longer reading from separate localStorage keys.
 */
export function getStoredUser(): { name: string | null; role: string | null } {
  if (typeof window === "undefined") return { name: null, role: null };
  const token = localStorage.getItem("token");
  if (!token) return { name: null, role: null };
  const payload = decodeJwtPayload(token);
  return {
    name: payload?.name ?? null,
    role: payload?.role ?? null,
  };
}
