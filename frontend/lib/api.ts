/**
 * RESTROMANAGER - API CONFIGURATION & UTILS
 * Gestionarea centralizată a cererilor către Backend
 */

// Se asigură că adresa URL nu are un slash la final pentru a evita concatenări de tip //
const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");

/**
 * Decodifică payload-ul unui token JWT pentru a accesa datele utilizatorului.
 */
export function decodeJwtPayload(token: string): any {
  if (!token || typeof token !== "string" || token === "undefined" || token === "null") {
    return null;
  }
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    // Adăugare padding base64 dacă lipsește
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch (error) {
    console.error("JWT Decode Error:", error);
    return null;
  }
}

/**
 * Verifică dacă token-ul este prezent și dacă nu a expirat.
 */
export function isTokenValid(token: string | null): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  if (!payload || !payload.exp) return false;
  // Adăugăm 30 secunde marjă de siguranță pentru latența rețelei
  return payload.exp * 1000 > Date.now() + 30_000;
}

/**
 * Funcția principală de cereri HTTP către Backend.
 * Gestionează automat Headers, Token-ul de autorizare și redirect la login dacă sesiunea expiră.
 */
export async function apiRequest(
  endpoint: string,
  options: RequestInit = {}
) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Verificăm dacă token-ul este valid înainte de a trimite cererea
  if (token && !isTokenValid(token)) {
    console.warn("Sesiune expirată. Redirecționare...");
    logout();
    return new Response(
      JSON.stringify({ detail: "Sesiune expirată. Te rugăm să te autentifici din nou." }), 
      { status: 401, headers: { "Content-Type": "application/json" } }
    );
  }

  // Curățăm endpoint-ul să înceapă mereu cu un singur slash
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Construim URL-ul final: BASE_URL (fără / la final) + cleanEndpoint (cu / la început)
  const fullUrl = `${BASE_URL}${cleanEndpoint}`;

  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      logout();
    }

    return response;
  } catch (error) {
    console.error("Network Fetch Error:", error);
    throw error;
  }
}

/**
 * Șterge datele de sesiune și redirecționează utilizatorul la pagina de Login.
 */
export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
    localStorage.removeItem("table_id");
    // Folosim window.location pentru a forța un refresh curat al stării aplicației
    window.location.href = "/login";
  }
}

/**
 * Extrage numele și rolul utilizatorului direct din token-ul salvat.
 */
export function getStoredUser(): { id: number | null; name: string | null; role: string | null } {
  if (typeof window === "undefined") return { id: null, name: null, role: null };
  const token = localStorage.getItem("token");
  if (!token) return { id: null, name: null, role: null };
  const payload = decodeJwtPayload(token);
  return {
    id: payload?.user_id ?? null,
    name: payload?.name ?? null,
    role: payload?.role ?? null,
  };
}