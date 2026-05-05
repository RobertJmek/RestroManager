"use client"
import React, { useEffect, useState } from 'react';
import { Bell, CheckCircle2, AlertTriangle } from "lucide-react";
import UserProfileMenu from "../../components/ui/UserProfileMenu";
import ClientRoleGuard from "../../components/ClientRoleGuard";

const INITIAL_TABLES = [
  { id: 1, status: 'free' },
  { id: 2, status: 'occupied' },
  { id: 3, status: 'free' },
  { id: 4, status: 'free' },
  { id: 5, status: 'occupied' },
  { id: 6, status: 'free' },
];

function WaiterContent() {
  const [tables, setTables] = useState(INITIAL_TABLES);
  const [notifications, setNotifications] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace("https://", "wss://").replace("http://", "ws://").replace("/api", "");
    const socket = new WebSocket(`${wsUrl}/ws/waiter?token=${encodeURIComponent(token ?? "")}`);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setNotifications(prev => [{ ...data, id: Date.now() }, ...prev]);
      if (data.event === "TABLE_OCCUPIED") updateTableStatus(data.table, 'occupied');
      else if (data.event === "FOOD_READY") updateTableStatus(data.table, 'ready');
    };
    return () => socket.close();
  }, []);

  const updateTableStatus = (tableNumber: number, status: string) => {
    setTables(prev => prev.map(t => t.id === tableNumber ? { ...t, status } : t));
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 md:p-10 text-slate-100">
      <header className="flex justify-between items-center mb-10">
        <h1 className="text-3xl font-black text-blue-400 tracking-tight italic">WAITER DASHBOARD</h1>
        <div className="flex items-center gap-4">
          <UserProfileMenu />
          <span className="flex items-center gap-1 text-xs font-bold bg-green-900/50 text-green-400 px-3 py-1 rounded-full border border-green-700">● SERVER ONLINE</span>
        </div>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-white"><CheckCircle2 className="text-blue-400" /> Harta Meselor</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            {tables.map((table) => (
              <div key={table.id} className={`h-32 rounded-2xl border-2 flex flex-col items-center justify-center transition-all ${table.status === 'occupied' ? 'bg-orange-900/40 border-orange-500 text-orange-300' : table.status === 'ready' ? 'bg-green-900/40 border-green-500 text-green-300 animate-pulse' : 'bg-slate-900 border-slate-700 text-slate-400'}`}>
                <span className="text-xs font-bold uppercase">Masa</span><span className="text-4xl font-black">{table.id}</span>
                <span className="text-[10px] mt-2 font-bold uppercase">{table.status === 'free' ? 'Liberă' : table.status === 'ready' ? 'Mâncare Gata!' : 'Ocupată'}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="bg-slate-900 rounded-3xl p-6 border border-slate-800 h-[600px] flex flex-col">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-white"><Bell className="text-orange-400" /> Notificări Live</h2>
          <div className="space-y-4 overflow-y-auto flex-1 pr-2">
            {notifications.map((n) => (
              <div key={n.id} className={`p-4 rounded-xl border-l-4 animate-in slide-in-from-right ${n.event === "URGENT_CALL" ? "bg-red-900/30 border-red-500" : "bg-blue-900/30 border-blue-500"}`}>
                <div className="flex justify-between items-start"><p className="font-black text-sm uppercase tracking-wider text-white">{n.event === "URGENT_CALL" ? "⚠️ ASISTENȚĂ" : "🍳 BUCĂTĂRIE"}</p><span className="text-[10px] text-slate-400 font-mono">ACUM</span></div>
                <p className="text-sm mt-1 text-slate-300 font-medium">{n.message}</p><p className="text-xs mt-2 font-bold text-slate-500">MASA #{n.table}</p>
              </div>
            ))}
            {notifications.length === 0 && <div className="text-center py-20 text-slate-600 italic">Nicio notificare activă</div>}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function WaiterPage() {
  return (
    <ClientRoleGuard role="Waiter" theme="dark" spinnerColor="border-blue-500">
      <WaiterContent />
    </ClientRoleGuard>
  );
}
