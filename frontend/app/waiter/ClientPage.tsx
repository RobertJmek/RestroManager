"use client"
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Bell, CheckCircle2 } from "lucide-react";
import UserProfileMenu from "../../components/ui/UserProfileMenu";
import ClientRoleGuard from "../../components/ClientRoleGuard";
import { apiRequest } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type TableStatus = "free" | "occupied" | "waiting_for_food" | "bill_requested" | "ready";

type Table = {
  id: number;
  number: number;
  capacity: number;
  status: TableStatus;
  location: string | null;
};

const STATUS_CONFIG: Record<TableStatus, { label: string; classes: string }> = {
  free:               { label: "Liberă",           classes: "bg-white border-slate-200 text-slate-400" },
  occupied:           { label: "Ocupată",          classes: "bg-orange-100 border-orange-400 text-orange-700" },
  waiting_for_food:   { label: "Așteaptă mâncare", classes: "bg-yellow-100 border-yellow-400 text-yellow-700" },
  bill_requested:     { label: "Cere nota",        classes: "bg-purple-100 border-purple-400 text-purple-700" },
  ready:              { label: "Mâncare Gata!",    classes: "bg-green-100 border-green-500 text-green-700 animate-pulse" },
};

function WaiterContent() {
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<any[]>([]);
  // Ref to always have the latest tables in the WS handler without re-creating the socket
  const tablesRef = useRef<Table[]>([]);

  // Fetch mese reale din DB
  const fetchTables = useCallback(async () => {
    try {
      const res = await apiRequest("/waiter/tables");
      if (res.ok) {
        const data = await res.json();
        setTables(data);
        tablesRef.current = data;
      }
    } catch (err) {
      console.error("Eroare la fetch mese:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  // Actualizează statusul mesei în DB și local
  const updateTableStatus = useCallback(async (tableId: number, newStatus: TableStatus) => {
    try {
      await apiRequest(`/waiter/tables/${tableId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      setTables(prev => {
        const updated = prev.map(t => t.id === tableId ? { ...t, status: newStatus } : t);
        tablesRef.current = updated;
        return updated;
      });
    } catch (err) {
      console.error("Eroare la update status masă:", err);
    }
  }, []);

  // WebSocket
  useEffect(() => {
    const token = localStorage.getItem("token");
    const wsUrl = (API_URL)
      .replace("https://", "wss://")
      .replace("http://", "ws://")
      .replace("/api", "");
    const socket = new WebSocket(`${wsUrl}/ws/waiter?token=${encodeURIComponent(token ?? "")}`);

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      setNotifications(prev => [{ ...data, id: Date.now() }, ...prev]);

      if (data.event === "TABLE_OCCUPIED") {
        // Use ref to avoid stale closure — no need to add tables to deps
        const table = tablesRef.current.find(t => t.number === data.table);
        if (table) {
          await updateTableStatus(table.id, "occupied");
        } else {
          fetchTables();
        }
      } else if (data.event === "FOOD_READY") {
        const table = tablesRef.current.find(t => t.number === data.table);
        if (table) {
          await updateTableStatus(table.id, "ready");
        }
      }
    };

    return () => socket.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateTableStatus, fetchTables]);

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10">
      <header className="flex justify-between items-center mb-10">
        <h1 className="text-3xl font-black text-blue-900 tracking-tight italic">WAITER DASHBOARD</h1>
        <div className="flex items-center gap-4">
          <UserProfileMenu />
          <span className="flex items-center gap-1 text-xs font-bold bg-green-100 text-green-700 px-3 py-1 rounded-full border border-green-200">
            ● SERVER ONLINE
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Harta meselor */}
        <section className="lg:col-span-2">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <CheckCircle2 className="text-blue-600" /> Harta Meselor
          </h2>

          {loading ? (
            <div className="flex items-center justify-center h-48 text-slate-400">
              <div className="w-6 h-6 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mr-3" />
              Se încarcă mesele...
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
              {tables.map((table) => {
                const cfg = STATUS_CONFIG[table.status] ?? STATUS_CONFIG.free;
                return (
                  <div
                    key={table.id}
                    className={`h-36 rounded-2xl border-2 flex flex-col items-center justify-center transition-all shadow-sm cursor-pointer select-none ${cfg.classes}`}
                    onClick={() => {
                      if (table.status !== "free") {
                        updateTableStatus(table.id, "free");
                      }
                    }}
                    title={table.status !== "free" ? "Click pentru a elibera masa" : ""}
                  >
                    <span className="text-xs font-bold uppercase">{table.location || "Masa"}</span>
                    <span className="text-4xl font-black">{table.number}</span>
                    <span className="text-[10px] mt-1 font-bold uppercase">{cfg.label}</span>
                    {table.status !== "free" && (
                      <span className="text-[9px] mt-1 opacity-60">click → eliberează</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Notificări Live */}
        <section className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 h-[600px] flex flex-col">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Bell className="text-orange-500" /> Notificări Live
          </h2>
          <div className="space-y-4 overflow-y-auto flex-1 pr-2">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`p-4 rounded-xl border-l-4 shadow-sm ${
                  n.event === "URGENT_CALL" ? "bg-red-50 border-red-500" : "bg-blue-50 border-blue-500"
                }`}
              >
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
              <div className="text-center py-20 opacity-20 italic">Nicio notificare activă</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function WaiterPage() {
  return (
    <ClientRoleGuard role="Waiter" theme="light" spinnerColor="border-blue-500">
      <WaiterContent />
    </ClientRoleGuard>
  );
}
