"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Lock, Mail, Loader2, UtensilsCrossed } from "lucide-react";
import { isTokenValid, logout } from "../../lib/api";

const ROLE_REDIRECTS: Record<string, string> = {
  Manager: "/manager",
  Waiter: "/waiter",
  Chef: "/chef",
};

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true); // starts true while checking
  const [error, setError] = useState("");
  const router = useRouter();

  // Dacă utilizatorul e deja autentificat, îl redirecționăm direct
  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("user_role");

    if (token && role && ROLE_REDIRECTS[role]) {
      if (isTokenValid(token)) {
        window.location.href = ROLE_REDIRECTS[role];
        return;
      }
      // Token expirat — curățăm
      logout();
    }
    setLoading(false);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Autentificare eșuată");
      }

      const payload = decodeJwtPayload(data.access_token);
      if (!payload) throw new Error("Token invalid primit de la server.");

      const role: string = payload.role;
      const name: string = payload.name ?? email;

      if (!ROLE_REDIRECTS[role]) {
        throw new Error(`Rolul "${role}" nu are o pagină asociată.`);
      }

      // Salvăm sesiunea
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user_role", role);
      localStorage.setItem("user_name", name);

      // Redirecționăm cu navigare hard pentru a reseta starea aplicației
      window.location.href = ROLE_REDIRECTS[role];
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  // Ecran de încărcare în timp ce verificăm sesiunea existentă
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f172a] flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-tr from-orange-500 to-amber-400 rounded-2xl shadow-lg shadow-orange-500/20 mb-4">
            <UtensilsCrossed className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">RestroManager</h1>
          <p className="text-slate-400">Sistem de management HORECA</p>
        </div>

        {/* Card */}
        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700 p-8 rounded-3xl shadow-2xl">
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  id="login-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all"
                  placeholder="nume@restaurant.ro"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Parolă</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  id="login-password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm p-4 rounded-xl">
                {error}
              </div>
            )}

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-500 hover:to-orange-400 text-white font-semibold py-3 rounded-xl shadow-lg shadow-orange-500/25 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Autentificare"}
            </button>
          </form>
        </div>

        <p className="text-center mt-8 text-slate-500 text-sm">
          Acces restricționat pentru angajații restaurantului.
        </p>
      </div>
    </div>
  );
}
