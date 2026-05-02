"use client"
import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import UserProfileMenu from "../../components/ui/UserProfileMenu";
import { isTokenValid, logout } from "../../lib/api";

export default function ManagerPage() {
  const [dailyTotal, setDailyTotal] = useState(0);
  const [orderCount, setOrderCount] = useState(0);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  // Route Guard: verifică rol + validitate token fără flash
  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("user_role");

    if (!isTokenValid(token)) {
      logout();
    } else if (role !== "Manager") {
      setIsAuthorized(false);
    } else {
      setIsAuthorized(true);
    }
  }, []);

  // Simulăm preluarea raportului zilnic din Backend
  useEffect(() => {
    if (isAuthorized) {
      setDailyTotal(1250.50); // Valoare mock pentru prezentare
      setOrderCount(24);
    }
  }, [isAuthorized]);

  if (isAuthorized === null) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Se verifică permisiunile...</div>;
  }

  if (isAuthorized === false) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white p-8">
        <h1 className="text-4xl font-bold text-red-500 mb-4">Acces Interzis</h1>
        <p className="text-slate-400 mb-6">Nu aveți permisiunea de a vizualiza panoul de Manager. Sunteți autentificat ca {localStorage.getItem("user_role")}.</p>
        <button onClick={() => window.history.back()} className="bg-slate-800 px-6 py-2 rounded-lg hover:bg-slate-700 transition-colors">
          Înapoi la pagina anterioară
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-4xl font-black text-green-500 tracking-tight">MANAGER DASHBOARD</h1>
          <p className="text-slate-400">Monitorizare vânzări și administrare sistem</p>
        </div>
        <div className="flex items-center gap-6">
          <UserProfileMenu />
          <Button className="bg-green-600 hover:bg-green-500 font-bold">
            + Adaugă Produs Nou
          </Button>
        </div>
      </header>

      {/* Secțiunea de Rapoarte (Issue 3.5) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-400 text-sm uppercase">Încasări Zilnice</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-400">{dailyTotal} RON</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-400 text-sm uppercase">Comenzi Totale</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-400">{orderCount}</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-400 text-sm uppercase">Status Server</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <p className="text-xl font-medium">Online</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secțiunea CRUD - Placeholder pentru Etapa de Gestiune */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center border-dashed">
        <h2 className="text-xl font-semibold mb-2">Gestiune Meniu & Inventar</h2>
        <p className="text-slate-500 mb-6">Aici vei putea modifica prețurile, descrierile și disponibilitatea produselor în timp real.</p>
        <div className="flex justify-center gap-4">
          <button className="text-sm text-slate-300 hover:text-white underline">Vezi Inventar</button>
          <button className="text-sm text-slate-300 hover:text-white underline">Editează Categorii</button>
        </div>
      </div>
    </div>
  );
}