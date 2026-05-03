"use client";

import { useEffect, useState } from "react";
import { isTokenValid, getStoredUser } from "@/lib/api";

export function useAuth(requiredRole: string) {
  const [mounted, setMounted] = useState(false);
  const [, forceRender] = useState(0);

  useEffect(() => {
    setMounted(true);

    const handler = () => {
      setMounted(true);
      forceRender(n => n + 1);
    };
    window.addEventListener("pageshow", handler);
    window.addEventListener("popstate", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("pageshow", handler);
      window.removeEventListener("popstate", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  // SSR + first client render before hydration: stable spinner state (no mismatch)
  if (!mounted) {
    return { isAuthorized: false, userRole: "", isChecking: true };
  }

  // After mount: synchronous read on every render (handles bfcache restore via listeners)
  let role: string | null = null;
  try {
    const token = localStorage.getItem("token");
    if (isTokenValid(token)) {
      role = getStoredUser().role;
    }
  } catch {
    role = null;
  }

  return {
    isAuthorized: role === requiredRole,
    userRole: role ?? "",
    isChecking: false,
  };
}
