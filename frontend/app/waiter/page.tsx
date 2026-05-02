"use client"
import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Bell, CheckCircle2, AlertTriangle } from "lucide-react";
import UserProfileMenu from "../../components/ui/UserProfileMenu";

// Structura pentru mese (Mock initial)
const INITIAL_TABLES = [
  { id: 1, status: 'free' },
  { id: 2, status: 'occupied' },
  { id: 3, status: 'free' },
  { id: 4, status: 'free' },
  { id: 5, status: 'occupied' },
  { id: 6, status: 'free' },
];

export default function WaiterPage() {
  const [tables, setTables] = useState(INITIAL_TABLES);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  // Route Guard: verifică rol + validitate token fără flash
  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("user_role");

    if (!token) {
      window.location.href = "/login";
    } else if (role !== "Waiter") {
      setIsAuthorized(false);
    } else {
      setIsAuthorized(true);
    }
  }, []);

  useEffect(() => {
    if (!isAuthorized) return;

    // Conexiune WebSocket pentru Chelner
    const socket = new WebSocket("ws://localhost:8000/ws/waiter");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // 1. Gestionăm Notificările (Issue 3.4)
      setNotifications(prev => [{...data, id: Date.now()}, ...prev]);

      // 2. Actualizăm Harta Meselor (Issue 3.3)
      if (data.event === "TABLE_OCCUPIED") {
        updateTableStatus(data.table, 'occupied');
      } else if (data.event === "FOOD_READY") {
        updateTableStatus(data.table, 'ready');
      }
    };

    return () => socket.close();
  }, [isAuthorized]);

  const updateTableStatus = (tableNumber: number, status: string) => {
    setTables(prev => prev.map(t => 
      t.id === tableNumber ? { ...t, status } : t
    ));
  };

  if (isAuthorized === null) {
    return <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500">Se verifică permisiunile...</div>;
  }

  if (isAuthorized === false) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-slate-800 p-8">
        <h1 className="text-4xl font-bold text-red-500 mb-4">Acces Interzis</h1>
        <p className="text-slate-500 mb-6 font-medium">Nu aveți permisiunea de a vizualiza panoul de Waiter. Sunteți autentificat ca {localStorage.getItem("user_role")}.</p>
        <button onClick={() => window.history.back()} className="bg-white border border-slate-300 text-slate-700 px-6 py-2 rounded-lg hover:bg-slate-100 transition-colors shadow-sm font-semibold">
          Înapoi la pagina anterioară
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10">
      <header className="flex justify-between items-center mb-10">
        <h1 className="text-3xl font-black text-blue-900 tracking-tight italic">WAITER DASHBOARD</h1>
        <div className="flex items-center gap-4">
            <UserProfileMenu />
            <span className="flex items-center gap-1 text-xs font-bold bg-green-100 text-green-700 px-3 py-1 rounded-full border border-green-200">● SERVER ONLINE</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* HARTA MESELOR (Issue 3.3) */}
        <section className="lg:col-span-2">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <CheckCircle2 className="text-blue-600" /> Harta Meselor
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            {tables.map((table) => (
              <div 
                key={table.id}
                className={`h-32 rounded-2xl border-2 flex flex-col items-center justify-center transition-all shadow-sm ${
                  table.status === 'occupied' ? 'bg-orange-100 border-orange-400 text-orange-700' :
                  table.status === 'ready' ? 'bg-green-100 border-green-500 text-green-700 animate-pulse' :
                  'bg-white border-slate-200 text-slate-400'
                }`}
              >
                <span className="text-xs font-bold uppercase">Masa</span>
                <span className="text-4xl font-black">{table.id}</span>
                <span className="text-[10px] mt-2 font-bold uppercase">
                    {table.status === 'free' ? 'Liberă' : table.status === 'ready' ? 'Mâncare Gata!' : 'Ocupată'}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* FEED NOTIFICĂRI (Issue 3.4) */}
        <section className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 h-[600px] flex flex-col">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Bell className="text-orange-500" /> Notificări Live
          </h2>
          <div className="space-y-4 overflow-y-auto flex-1 pr-2 custom-scrollbar">
            {notifications.map((n) => (
              <div key={n.id} className={`p-4 rounded-xl border-l-4 shadow-sm animate-in slide-in-from-right ${
                n.event === "URGENT_CALL" ? "bg-red-50 border-red-500" : "bg-blue-50 border-blue-500"
              }`}>
                <div className="flex justify-between items-start">
                    <p className="font-black text-sm uppercase tracking-wider">
                        {n.event === "URGENT_CALL" ? "⚠️ ASISTENȚĂ" : "🍳 BUCĂTĂRIE"}
                    </p>
                    <span className="text-[10px] text-slate-400 font-mono">ACUM</span>
                </div>
                <p className="text-sm mt-1 text-slate-700 font-medium">{n.message}</p>
                <p className="text-xs mt-2 font-bold text-slate-500">MASA #{n.table}</p>
              </div>
            ))}
            {notifications.length === 0 && (
              <div className="text-center py-20 opacity-20 italic">
                Nicio notificare activă
              </div>
            )}
          </div>
        </section>

      </div>
    </div>
  );
}