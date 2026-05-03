"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import UserProfileMenu from "@/components/ui/UserProfileMenu";
import RoleGuard from "@/components/RoleGuard";

const DAILY_TOTAL = 1250.5;
const ORDER_COUNT = 24;

export default function ManagerPage() {
  return (
    <RoleGuard role="Manager" theme="dark" spinnerColor="border-green-500">
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
            <p className="text-3xl font-bold text-green-400">{DAILY_TOTAL} RON</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-400 text-sm uppercase">Comenzi Totale</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-400">{ORDER_COUNT}</p>
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
    </RoleGuard>
  );
}