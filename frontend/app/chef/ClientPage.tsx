"use client"
import { useEffect, useState, useCallback, useRef } from "react"
import UserProfileMenu from "../../components/ui/UserProfileMenu"
import ClientRoleGuard from "../../components/ClientRoleGuard";
import { apiRequest } from "@/lib/api";

type Order = {
  id: number
  table_number: number
  items: { id?: number; name: string; quantity: number; status?: string; special_instructions?: string }[]
  notes: string
}

function ChefContent() {
  const [orders, setOrders] = useState<Order[]>([])

  // Fetch comenzile active din DB la mount
  const fetchActiveOrders = useCallback(async () => {
    try {
      const res = await apiRequest("/chef/active-orders");
      if (res.ok) {
        const data: Order[] = await res.json();
        setOrders(data);
      }
    } catch (err) {
      console.error("Eroare la fetch comenzi active:", err);
    }
  }, []);

  useEffect(() => {
    fetchActiveOrders();
  }, [fetchActiveOrders]);

  const [wsOnline, setWsOnline] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  // WebSocket pentru comenzi noi în timp real
  const connectWs = useCallback(() => {
    const token = localStorage.getItem("token");
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api")
      .replace("https://", "wss://")
      .replace("http://", "ws://")
      .replace("/api", "");
    wsRef.current?.close();
    const ws = new WebSocket(`${wsUrl}/ws/chef?token=${encodeURIComponent(token ?? "")}`);
    wsRef.current = ws;
    ws.onopen = () => setWsOnline(true);
    ws.onclose = () => setWsOnline(false);
    ws.onerror = () => setWsOnline(false);
    ws.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (e) {
        console.error("WS: payload invalid", e);
        return;
      }
      if (payload.event === "NEW_ORDER") {
        const newOrder: Order = { notes: "", ...payload.data };
        // Append new items if order exists, else prepend new order
        setOrders((prev) => {
          const exists = prev.find((o) => o.id === newOrder.id);
          if (exists) {
            return prev.map(o => o.id === newOrder.id ? { ...o, items: [...o.items, ...newOrder.items] } : o);
          }
          return [newOrder, ...prev];
        });
      }
    };
  }, []);

  useEffect(() => {
    connectWs();
    return () => wsRef.current?.close();
  }, [connectWs]);

  // Marchează toată comanda gata prin API (backend face și update DB + broadcast WS la Waiter)
  const markAsReady = useCallback(async (orderId: number) => {
    try {
      const res = await apiRequest(`/orders/${orderId}/ready-for-pickup`, {
        method: "PUT",
      });
      if (res.ok) {
        setOrders((prev) => prev.filter((o) => o.id !== orderId));
      }
    } catch (err) {
      console.error("Eroare la markAsReady:", err);
    }
  }, []);

  const markItemAsReady = useCallback(async (orderId: number, itemId: number) => {
    try {
      const res = await apiRequest(`/orders/items/${itemId}/ready`, {
        method: "PUT",
      });
      if (res.ok) {
        setOrders((prev) => prev.map(o => {
          if (o.id !== orderId) return o;
          const newItems = o.items.map(item => item.id === itemId ? { ...item, status: "ready_for_pickup" } : item);
          return { ...o, items: newItems };
        }));
      }
    } catch (err) {
      console.error("Eroare la markItemAsReady:", err);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-white">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-black text-orange-500 tracking-tight">KITCHEN DISPLAY SYSTEM</h1>
        <div className="flex items-center gap-6">
          <UserProfileMenu />
          <button
            onClick={() => { if (!wsOnline) connectWs(); }}
            disabled={wsOnline}
            title={wsOnline ? "Conectat la server în timp real" : "Conexiune pierdută — click pentru reconectare"}
            className={`px-4 py-2 rounded-full text-sm border transition-colors ${wsOnline ? "bg-slate-800 border-slate-700 cursor-default" : "bg-red-900/50 border-red-700 hover:bg-red-800/60 cursor-pointer"}`}
          >
            Status: <span className={wsOnline ? "text-green-400" : "text-red-400"}>{wsOnline ? "● LIVE" : "● OFFLINE — Reconectează"}</span>
          </button>
        </div>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {orders.map((order) => (
          <div key={order.id} className="relative overflow-hidden border-2 border-slate-700 bg-slate-800 p-5 rounded-xl transition-all">
            <div className="flex justify-between items-start mb-4"><h2 className="text-2xl font-black">MASA #{order.table_number}</h2></div>
            <ul className="space-y-3 mb-6">{order.items?.map((item, i) => (
              <li key={i} className={`flex flex-col border-b border-slate-700/50 pb-2 ${item.status === 'ready_for_pickup' ? 'opacity-50' : ''}`}>
                <div className="flex justify-between items-center">
                  <div>
                    <span className={`font-medium text-lg ${item.status === 'ready_for_pickup' ? 'line-through' : ''}`}>{item.name}</span>
                    <span className="text-orange-400 font-bold ml-2">x{item.quantity}</span>
                  </div>
                  {item.id && item.status !== 'ready_for_pickup' && (
                    <button onClick={() => markItemAsReady(order.id, item.id!)} className="bg-orange-600 hover:bg-orange-500 text-white text-xs px-3 py-1 rounded">Gata</button>
                  )}
                </div>
                {item.special_instructions && (
                  <div className="text-red-400 text-sm font-bold mt-1 bg-red-950/30 px-2 py-1 rounded-md border border-red-900/50 self-start flex items-center gap-1">
                    <span>⚠️</span> {item.special_instructions}
                  </div>
                )}
              </li>
            ))}</ul>
            {/* order.notes eliminat din afișaj conform Epic 6, sau dacă backend mai trimite ceva vechi, îl lăsăm ascuns */}
            <button onClick={() => markAsReady(order.id)} className="w-full bg-green-600 hover:bg-green-500 text-white font-black py-4 rounded-lg transition-colors shadow-lg active:scale-95">MARCHEAZĂ GATA</button>
          </div>
        ))}
      </div>
      {orders.length === 0 && <div className="text-center py-20"><p className="text-slate-500 text-xl">Nu sunt comenzi active în acest moment.</p></div>}
    </div>
  )
}

export default function ChefPage() {
  return (
    <ClientRoleGuard role="Chef" theme="dark" spinnerColor="border-orange-500">
      <ChefContent />
    </ClientRoleGuard>
  );
}
