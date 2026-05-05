"use client";

import React, { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ThankYouPage() {
  const router = useRouter();

  useEffect(() => {
    // Optionally redirect back to scan after 10 seconds
    const timer = setTimeout(() => {
      router.push("/");
    }, 10000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="bg-white p-10 rounded-3xl shadow-xl max-w-sm w-full flex flex-col items-center animate-in fade-in zoom-in duration-500">
        <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-6">
          <CheckCircle2 size={40} />
        </div>
        <h1 className="text-3xl font-black text-slate-800 mb-2">Mulțumim pentru vizită!</h1>
        <p className="text-slate-500 font-medium mb-8">
          Masa a fost închisă cu succes. Te așteptăm cu drag să revii!
        </p>
        <button 
          onClick={() => router.push("/")}
          className="w-full py-3 bg-slate-900 text-white rounded-xl font-bold shadow-md hover:bg-slate-800 transition-colors"
        >
          Înapoi Acasă
        </button>
      </div>
    </div>
  );
}
