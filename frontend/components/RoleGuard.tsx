"use client";

import { ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";

type Theme = "dark" | "light";

interface RoleGuardProps {
  role: "Manager" | "Waiter" | "Chef";
  theme?: Theme;
  spinnerColor?: string;
  children: ReactNode;
}

const THEMES = {
  dark: {
    bg: "bg-slate-950",
    text: "text-white",
    muted: "text-slate-400",
    btn: "bg-slate-800 hover:bg-slate-700 text-white",
  },
  light: {
    bg: "bg-slate-50",
    text: "text-slate-800",
    muted: "text-slate-500",
    btn: "bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 shadow-sm",
  },
} as const;

export default function RoleGuard({
  role,
  theme = "dark",
  spinnerColor = "border-green-500",
  children,
}: RoleGuardProps) {
  const { isAuthorized, userRole, isChecking } = useAuth(role);
  const t = THEMES[theme];

  if (isChecking) {
    return (
      <div className={`min-h-screen ${t.bg} flex flex-col items-center justify-center ${t.text}`}>
        <div className={`w-8 h-8 border-4 ${spinnerColor} border-t-transparent rounded-full animate-spin mb-4`} />
        <p className={`${t.muted} font-medium`}>Se verifică permisiunile...</p>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className={`min-h-screen ${t.bg} flex flex-col items-center justify-center ${t.text} p-8`}>
        <h1 className="text-4xl font-bold text-red-500 mb-4">Acces Interzis</h1>
        <p className={`${t.muted} mb-6 font-medium`}>
          Nu aveți permisiunea de a vizualiza această pagină. Sunteți autentificat ca {userRole || "anonim"}.
        </p>
        <button
          onClick={() => { window.location.href = "/"; }}
          className={`${t.btn} px-6 py-2 rounded-lg transition-colors font-semibold`}
        >
          Întoarce-te la pagina principală
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
