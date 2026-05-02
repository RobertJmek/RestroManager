"use client"
import { useEffect, useState } from "react"
import UserProfileMenu from "../../components/ui/UserProfileMenu"
import { isTokenValid, logout } from "../../lib/api";

// Ajustăm tipul datelor pentru a include metadatele AI trimise de Backend
type Order = {
  id: number
  table_number: number
  items: { name: string; quantity: number }[]
  notes: string
  ai_metadata?: {
    urgency: "NORMAL" | "CRITICAL"
    cooking_strategy: string
  }
}

export default function ChefPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  // Route Guard: verifică rol + validitate token fără flash
  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("user_role");

    if (!isTokenValid(token)) {
      logout();
    } else if (role !== "Chef") {
      setIsAuthorized(false);
    } else {
      setIsAuthorized(true);
    }
  }, []);

  useEffect(() => {
    if (!isAuthorized) return;

    const token = localStorage.getItem("token");
    const ws = new WebSocket(`ws://localhost:8000/ws/chef?token=${encodeURIComponent(token ?? "")}`)
    setSocket(ws)

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data)

      if (payload.event === "NEW_ORDER") {
        // Mapăm datele primite de la API (payload.data și payload.ai_metadata)
        const newOrder: Order = {
          ...payload.data,
          ai_metadata: payload.ai_metadata
        }
        setOrders((prev) => [newOrder, ...prev]) // Punem comanda nouă prima
      }
    }

    return () => ws.close()
  }, [isAuthorized])

  // Funcție pentru a anunța chelnerul (Issue 3.4)
  const markAsReady = (orderId: number, tableNumber: number) => {
    if (socket) {
      socket.send(JSON.stringify({
        action: "ORDER_READY",
        table: tableNumber,
        order_id: orderId
      }))
      // Eliminăm comanda din lista bucătarului după ce e gata
      setOrders((prev) => prev.filter(o => o.id !== orderId))
    }
  }

  if (isAuthorized === null) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">Se verifică permisiunile...</div>;
  }

  if (isAuthorized === false) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-white p-8">
        <h1 className="text-4xl font-bold text-red-500 mb-4">Acces Interzis</h1>
        <p className="text-slate-400 mb-6">Nu aveți permisiunea de a vizualiza KDS (Kitchen Display System). Sunteți autentificat ca {localStorage.getItem("user_role")}.</p>
        <button onClick={() => window.history.back()} className="bg-slate-800 px-6 py-2 rounded-lg hover:bg-slate-700 transition-colors">
          Înapoi la pagina anterioară
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-8 text-white">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-black text-orange-500 tracking-tight">KITCHEN DISPLAY SYSTEM</h1>
        <div className="flex items-center gap-6">
          <UserProfileMenu />
          <div className="bg-slate-800 px-4 py-2 rounded-full text-sm border border-slate-700">
            Status: <span className="text-green-400">● LIVE</span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {orders.map((order) => (
          <div
            key={order.id}
            className={`relative overflow-hidden border-2 p-5 rounded-xl transition-all ${
              order.ai_metadata?.urgency === "CRITICAL" 
                ? "border-red-500 bg-red-950/20 animate-pulse" 
                : "border-slate-700 bg-slate-800"
            }`}
          >
            {/* AI Insight Badge */}
            <div className="mb-4 bg-slate-900/50 p-2 rounded border border-slate-700">
                <p className="text-[10px] uppercase font-bold text-slate-400">AI Cooking Insight:</p>
                <p className="text-xs text-blue-300 italic">{order.ai_metadata?.cooking_strategy || "Standard preparation"}</p>
            </div>

            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-black">MASA #{order.table_number}</h2>
              {order.ai_metadata?.urgency === "CRITICAL" && (
                <span className="bg-red-600 text-[10px] font-bold px-2 py-1 rounded shadow-lg">URGENT</span>
              )}
            </div>

            <ul className="space-y-3 mb-6">
              {order.items?.map((item, i) => (
                <li key={i} className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="font-medium text-lg">{item.name}</span>
                  <span className="text-orange-400 font-bold">x{item.quantity}</span>
                </li>
              ))}
            </ul>

            {order.notes && (
              <div className="bg-yellow-900/20 border border-yellow-700/50 p-3 rounded mb-6">
                <p className="text-sm text-yellow-200 uppercase font-bold text-[10px]">Note Client:</p>
                <p className="text-sm text-yellow-100 italic">{order.notes}</p>
              </div>
            )}

            <button 
              onClick={() => markAsReady(order.id, order.table_number)}
              className="w-full bg-green-600 hover:bg-green-500 text-white font-black py-4 rounded-lg transition-colors shadow-lg active:scale-95"
            >
              MARCHEAZĂ GATA
            </button>
          </div>
        ))}
      </div>

      {orders.length === 0 && (
        <div className="text-center py-20">
          <p className="text-slate-500 text-xl">Nu sunt comenzi active în acest moment.</p>
        </div>
      )}
    </div>
  )
}