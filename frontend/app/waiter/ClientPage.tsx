"use client"
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Bell, CheckCircle2 } from "lucide-react";
import UserProfileMenu from "../../components/ui/UserProfileMenu";
import ClientRoleGuard from "../../components/ClientRoleGuard";
import { apiRequest, getStoredUser } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type TableStatus = "free" | "occupied" | "waiting_for_food" | "bill_requested" | "ready";

type Table = {
  id: number;
  number: number;
  capacity: number;
  status: TableStatus;
  location: string | null;
  waiter_id: number | null;
  waiter_name: string | null;
};

const STATUS_CONFIG: Record<TableStatus, { label: string; classes: string }> = {
  free:               { label: "Liberă",           classes: "bg-slate-800 border-slate-600 text-slate-400" },
  occupied:           { label: "Ocupată",          classes: "bg-orange-950/40 border-orange-500 text-orange-400" },
  waiting_for_food:   { label: "Așteaptă mâncare", classes: "bg-yellow-950/40 border-yellow-500 text-yellow-400" },
  bill_requested:     { label: "Cere nota",        classes: "bg-purple-950/40 border-purple-500 text-purple-400" },
  ready:              { label: "Mâncare Gata!",    classes: "bg-green-950/40 border-green-500 text-green-400 animate-pulse" },
};

function WaiterContent() {
  const currentUser = getStoredUser() || { id: -1, role: "Waiter" };
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);
  const [activeOrder, setActiveOrder] = useState<any>(null);
  const [menuItems, setMenuItems] = useState<any[]>([]);
  const [isMenuMode, setIsMenuMode] = useState(false);
  const [cart, setCart] = useState<Record<string, any>>({});
  const [isSendingOrder, setIsSendingOrder] = useState(false);
  const [itemToAdd, setItemToAdd] = useState<any | null>(null);
  const [specialInstructions, setSpecialInstructions] = useState("");
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

  const fetchMenuItems = useCallback(async () => {
    try {
      const res = await apiRequest("/menu");
      if (res.ok) {
        const data = await res.json();
        setMenuItems(data);
      }
    } catch (err) {
      console.error("Eroare la fetch meniu:", err);
    }
  }, []);

  useEffect(() => {
    fetchTables();
    fetchMenuItems();
  }, [fetchTables, fetchMenuItems]);

  const confirmAddToCart = () => {
    if (!itemToAdd) return;
    const key = `${itemToAdd.id}-${specialInstructions}`;
    setCart(prev => ({
      ...prev,
      [key]: {
        ...itemToAdd,
        special_instructions: specialInstructions,
        quantity: (prev[key]?.quantity || 0) + 1,
        cartKey: key
      }
    }));
    setItemToAdd(null);
    setSpecialInstructions("");
  };

  const removeFromCart = (cartKey: string) => {
    setCart(prev => {
      const newCart = { ...prev };
      if (newCart[cartKey].quantity > 1) {
        newCart[cartKey].quantity -= 1;
      } else {
        delete newCart[cartKey];
      }
      return newCart;
    });
  };

  const cartTotal = Object.values(cart).reduce((sum: number, item: any) => sum + item.price * item.quantity, 0);

  const sendWaiterOrder = async () => {
    if (!selectedTable) return;
    setIsSendingOrder(true);
    const orderItems = Object.values(cart).map((i: any) => ({
      menu_item_id: i.id,
      quantity: i.quantity,
      special_instructions: i.special_instructions || null
    }));

    try {
      // Use the standard orders endpoint with table_id for waiter-initiated orders
      const res = await apiRequest(`/orders`, {
        method: "POST",
        body: JSON.stringify({
          items: orderItems,
          table_id: selectedTable.id  // Required for waiter-initiated orders
        })
      });
      if (res.ok) {
        const orderData = await res.json();
        setCart({});
        setIsMenuMode(false);
        // Refresh tables and update selectedTable to get new waiter_id and status
        await fetchTables();
        const updatedTable = tablesRef.current.find(t => t.id === selectedTable.id);
        if (updatedTable) {
          setSelectedTable(updatedTable);
        }
        // Set the newly created order as active
        setActiveOrder(orderData);
      } else {
        const error = await res.json();
        console.error("Eroare la crearea comenzii:", error);
        alert(`Eroare: ${error.detail || "Nu s-a putut crea comanda"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Eroare de rețea la crearea comenzii");
    } finally {
      setIsSendingOrder(false);
    }
  };

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

  const handleTableClick = async (table: Table) => {
    setSelectedTable(table);
    if (table.status === "free") {
      // For free tables, allow creating a new order
      setActiveOrder(null);
      setIsMenuMode(true);
      setCart({});
    } else {
      // For occupied/reserved tables, show existing order
      try {
        const res = await apiRequest(`/waiter/tables/${table.id}/active-order`);
        if (res.ok) {
          setActiveOrder(await res.json());
          setIsMenuMode(false);
          setCart({});
        } else {
          setActiveOrder(null);
        }
      } catch (err) {
        console.error("Eroare fetching order:", err);
      }
    }
  };

  const [wsOnline, setWsOnline] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket
  const connectWs = useCallback(() => {
    const token = localStorage.getItem("token");
    const wsUrl = (API_URL)
      .replace("https://", "wss://")
      .replace("http://", "ws://")
      .replace("/api", "");
    wsRef.current?.close();
    const socket = new WebSocket(`${wsUrl}/ws/waiter?token=${encodeURIComponent(token ?? "")}`);
    wsRef.current = socket;

    socket.onopen = () => setWsOnline(true);
    socket.onclose = () => setWsOnline(false);
    socket.onerror = () => setWsOnline(false);

    socket.onmessage = async (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        console.error("WS: payload invalid", e);
        return;
      }
      if (data.event === "FOOD_READY_FOR_PICKUP") {
         const user = getStoredUser();
         if (data.target_waiter_id && data.target_waiter_id !== user.id) {
             return; // Ignore completely if it's for someone else
         }
      }

      setNotifications(prev => [{ ...data, id: Date.now() }, ...prev]);

      if (data.event === "TABLE_OCCUPIED") {
        // Use ref to avoid stale closure — no need to add tables to deps
        const table = tablesRef.current.find(t => t.number === data.table);
        if (table) {
          await updateTableStatus(table.id, "occupied");
        } else {
          fetchTables();
        }
      } else if (data.event === "FOOD_READY" || data.event === "FOOD_READY_FOR_PICKUP") {
        const table = tablesRef.current.find(t => t.number === data.table);
        if (table) {
          await updateTableStatus(table.id, "ready");
        }
      } else if (data.event === "TABLE_CLAIMED") {
        fetchTables();
      }
    };
  }, [updateTableStatus, fetchTables]);

  useEffect(() => {
    connectWs();
    return () => wsRef.current?.close();
  }, [connectWs]);

  return (
    <div className="min-h-screen bg-slate-950 p-6 md:p-10 text-slate-100">
      <header className="flex justify-between items-center mb-10">
        <h1 className="text-3xl font-black text-blue-400 tracking-tight italic">WAITER DASHBOARD</h1>
        <div className="flex items-center gap-4">
          <UserProfileMenu />
          <button
            onClick={() => { if (!wsOnline) connectWs(); }}
            disabled={wsOnline}
            title={wsOnline ? "Conectat la server în timp real" : "Conexiune pierdută — click pentru reconectare"}
            className={`flex items-center gap-1 text-xs font-bold px-3 py-1 rounded-full border transition-colors ${wsOnline ? "bg-green-900/50 text-green-400 border-green-700 cursor-default" : "bg-red-900/50 text-red-400 border-red-700 hover:bg-red-800/60 cursor-pointer"}`}
          >
            {wsOnline ? "● SERVER ONLINE" : "● SERVER OFFLINE — Reconectează"}
          </button>
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
                    className={`h-36 rounded-2xl border-2 flex flex-col items-center justify-center transition-all shadow-sm cursor-pointer select-none relative ${cfg.classes} ${table.status !== "free" && !table.waiter_id ? "animate-pulse ring-4 ring-red-400" : ""}`}
                    onClick={() => handleTableClick(table)}
                    title={table.status !== "free" ? "Click pentru a vedea comanda" : ""}
                  >
                    <span className="text-xs font-bold uppercase">{table.location || "Masa"}</span>
                    <span className="text-4xl font-black text-white">{table.number}</span>
                    <span className="text-[10px] mt-1 font-bold uppercase">{cfg.label}</span>
                    
                    {table.status !== "free" && !table.waiter_id && (
                      <span className="absolute bottom-2 bg-red-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase shadow-md">
                        Necesită Preluare!
                      </span>
                    )}

                    {table.status !== "free" && table.waiter_id && (
                      <span className="absolute bottom-2 bg-slate-700/50 text-slate-300 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 border border-slate-600">
                        <span>👨‍🍳</span> {table.waiter_name}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Notificări Live */}
        <section className="bg-slate-900 rounded-3xl p-6 shadow-xl border border-slate-800 h-[600px] flex flex-col">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-slate-100">
            <Bell className="text-orange-500" /> Notificări Live
          </h2>
          <div className="space-y-4 overflow-y-auto flex-1 pr-2">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`p-4 rounded-xl border-l-4 shadow-sm ${
                  n.event === "URGENT_CALL" ? "bg-red-950/30 border-red-500" : 
                  n.event === "BILL_REQUESTED" ? "bg-purple-950/30 border-purple-500" :
                  "bg-blue-950/30 border-blue-500"
                }`}
              >
                <div className="flex justify-between items-start">
                  <p className="font-black text-sm uppercase tracking-wider text-slate-200">
                    {n.event === "URGENT_CALL" ? "⚠️ ASISTENȚĂ" : 
                     n.event === "BILL_REQUESTED" ? "💳 NOTĂ DE PLATĂ" : 
                     "🍳 BUCĂTĂRIE"}
                  </p>
                  <span className="text-[10px] text-slate-500 font-mono">ACUM</span>
                </div>
                <p className="text-sm mt-1 text-slate-300 font-medium">{n.message}</p>
                <p className="text-xs mt-2 font-bold text-slate-500">MASA #{n.table}</p>
              </div>
            ))}
            {notifications.length === 0 && (
              <div className="text-center py-20 text-slate-600 italic">Nicio notificare activă</div>
            )}
          </div>
        </section>
      </div>

      {selectedTable && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTable(null)}>
          <div className="bg-slate-900 rounded-3xl p-6 w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh] border border-slate-800" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6 shrink-0">
               <h2 className="text-2xl font-black text-white">{isMenuMode ? `Meniu Masă #${selectedTable.number}` : `Masă #${selectedTable.number}`}</h2>
               <button onClick={() => { setSelectedTable(null); setIsMenuMode(false); setCart({}); }} className="text-slate-500 hover:text-white text-xl font-bold">✕</button>
            </div>
            
            <div className="overflow-y-auto flex-1 min-h-0 pr-2">
            {isMenuMode ? (
              <div className="space-y-8 pb-32">
                {/* Group by category */}
                {Array.from(new Set(menuItems.map(i => i.category))).map(category => (
                  <div key={category as string}>
                    <h3 className="font-black text-slate-200 uppercase mb-4 text-sm tracking-wider border-b border-slate-700 pb-2">{category as string}</h3>
                    <div className="space-y-3">
                      {menuItems.filter(i => i.category === category).map(item => (
                        <div key={item.id} className="flex justify-between items-center bg-slate-800 p-3 rounded-xl border border-slate-700">
                          <div>
                            <p className="font-bold text-slate-100">{item.name}</p>
                            <p className="text-sm font-bold text-green-400">{item.price} Lei</p>
                          </div>
                          <button 
                            onClick={() => setItemToAdd(item)}
                            className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2 rounded-full transition-colors text-sm shrink-0"
                          >
                            Adaugă
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : selectedTable.status !== "free" && !selectedTable.waiter_id ? (
              <div className="py-8 flex flex-col items-center">
                <p className="text-slate-400 font-medium mb-6 text-center">Această masă are nevoie de un chelner asignat.</p>
                <button 
                  onClick={async () => {
                    await apiRequest(`/waiter/tables/${selectedTable.id}/claim`, { method: "PUT" });
                    fetchTables();
                    setSelectedTable({ ...selectedTable, waiter_id: currentUser.id, waiter_name: currentUser.name || "Tu" });
                  }}
                  className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-black text-lg shadow-lg transition-transform active:scale-95"
                >
                  PREIA MASA
                </button>
              </div>
            ) : (
              <>
                {selectedTable.waiter_id && selectedTable.waiter_id !== currentUser.id && (
                  <div className="bg-yellow-950/30 border border-yellow-600 p-3 rounded-xl mb-4">
                    <p className="text-yellow-300 font-bold text-center text-sm">Masă gestionată de {selectedTable.waiter_name}. Acces Read-Only.</p>
                  </div>
                )}
                {activeOrder ? (
                  <div className="mb-6 space-y-6 max-h-[60vh] overflow-y-auto pr-2">
                    {/* Grupa 1: În așteptare */}
                    {(activeOrder.items || []).filter((i: any) => i.status === 'pending').length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-black text-slate-500 uppercase mb-2 tracking-wider">În așteptare (Bucătărie)</h4>
                        <ul className="space-y-2">
                          {(activeOrder.items || []).filter((i: any) => i.status === 'pending').map((item: any) => (
                             <li key={item.id} className="flex flex-col bg-yellow-950/20 p-3 rounded-lg border border-yellow-800/50">
                                <div className="flex justify-between items-center">
                                  <div>
                                     <span className="font-bold text-slate-100">{item.name}</span>
                                     <span className="text-blue-400 font-bold ml-2">x{item.quantity}</span>
                                  </div>
                                  <span className="text-[10px] bg-yellow-900/50 text-yellow-400 px-2 py-1 rounded-full font-bold">În preparare ⏳</span>
                                </div>
                                {item.special_instructions && <p className="text-[10px] text-yellow-300 italic mt-1 font-medium bg-yellow-900/30 inline-block self-start px-2 py-0.5 rounded border border-yellow-800/50">⚠️ {item.special_instructions}</p>}
                             </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Grupa 2: De dus la masă */}
                    {(activeOrder.items || []).filter((i: any) => i.status === 'ready_for_pickup').length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-black text-blue-400 uppercase mb-2 tracking-wider">De dus la masă</h4>
                        <ul className="space-y-2">
                          {(activeOrder.items || []).filter((i: any) => i.status === 'ready_for_pickup').map((item: any) => (
                             <li key={item.id} className="flex flex-col bg-blue-950/20 p-3 rounded-lg border border-blue-800/50 shadow-sm">
                                <div className="flex justify-between items-center">
                                  <div>
                                     <span className="font-bold text-slate-100">{item.name}</span>
                                     <span className="text-blue-400 font-bold ml-2">x{item.quantity}</span>
                                  </div>
                                  {selectedTable.waiter_id === currentUser.id ? (
                                    <button 
                                       onClick={async () => {
                                          await apiRequest(`/orders/items/${item.id}/served`, { method: "PUT" });
                                          setActiveOrder({ ...activeOrder, items: activeOrder.items.map((i: any) => i.id === item.id ? { ...i, status: 'served' } : i) });
                                       }}
                                       className="bg-green-500 hover:bg-green-600 text-white text-[10px] px-3 py-1.5 rounded-full font-bold shadow-sm transition-transform active:scale-95"
                                    >
                                       Am servit 🍽️
                                    </button>
                                  ) : (
                                    <span className="text-[10px] bg-green-900/50 text-green-400 px-2 py-1 rounded-full font-bold">Gata de preluat</span>
                                  )}
                                </div>
                                {item.special_instructions && <p className="text-[10px] text-blue-300 italic mt-1 font-medium bg-blue-900/30 inline-block self-start px-2 py-0.5 rounded border border-blue-800/50">⚠️ {item.special_instructions}</p>}
                             </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Grupa 3: Servite */}
                    {(activeOrder.items || []).filter((i: any) => i.status === 'served').length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-black text-green-500 uppercase mb-2 tracking-wider">Servite pe masă</h4>
                        <ul className="space-y-2">
                          {(activeOrder.items || []).filter((i: any) => i.status === 'served').map((item: any) => (
                             <li key={item.id} className="flex flex-col bg-slate-800/50 p-3 rounded-lg border border-slate-700 opacity-60">
                                <div className="flex justify-between items-center">
                                  <div>
                                     <span className="font-bold text-slate-300">{item.name}</span>
                                     <span className="text-slate-500 font-bold ml-2">x{item.quantity}</span>
                                  </div>
                                  <span className="text-[10px] text-green-400 font-bold flex items-center"><CheckCircle2 className="w-3 h-3 mr-1" /> Servit</span>
                                </div>
                                {item.special_instructions && <p className="text-[10px] text-slate-400 italic mt-1 font-medium bg-slate-700/50 inline-block self-start px-2 py-0.5 rounded border border-slate-600">⚠️ {item.special_instructions}</p>}
                             </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-500 italic mb-6 text-center py-8">Nu există o comandă activă pentru această masă.</p>
                )}

                {selectedTable.waiter_id === currentUser.id && (
                  <div className="flex flex-col gap-3 mt-4">
                    <button 
                      onClick={() => setIsMenuMode(true)} 
                      className="w-full py-4 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-500 transition-colors shadow-lg active:scale-95 flex items-center justify-center gap-2"
                    >
                      <span>➕</span> Adaugă Produse Manual
                    </button>
                    <button 
                      onClick={async () => {
                        await apiRequest(`/tables/${selectedTable.id}/close`, {
                          method: "POST"
                        });
                        setTables(prev => prev.map(t => t.id === selectedTable.id ? { ...t, status: "free", waiter_id: null, waiter_name: null } : t));
                        setSelectedTable(null);
                      }} 
                      className="w-full py-4 rounded-xl bg-red-950/30 text-red-400 font-bold hover:bg-red-950/50 transition-colors border border-red-800"
                    >
                      Închide Masa
                    </button>
                  </div>
                )}
              </>
            )}
            </div>

            {/* Cart sticky bar outside the scroll area but inside the modal */}
            {isMenuMode && Object.keys(cart).length > 0 && (
              <div className="mt-6 pt-6 border-t border-slate-700 shrink-0">
                <div className="max-h-[30vh] overflow-y-auto mb-4 bg-slate-800 rounded-xl p-2 border border-slate-700">
                  <h4 className="text-xs font-black text-slate-400 uppercase mb-2 px-2">Comanda curentă</h4>
                  {Object.values(cart).map((cItem: any) => (
                    <div key={cItem.cartKey} className="flex justify-between items-center py-2 px-2 border-b border-slate-700 last:border-0">
                      <div className="flex-1">
                        <p className="font-bold text-sm text-white">{cItem.name} <span className="text-blue-400">x{cItem.quantity}</span></p>
                        {cItem.special_instructions && <p className="text-xs text-slate-400 italic flex items-center gap-1"><span>⚠️</span> Note: {cItem.special_instructions}</p>}
                      </div>
                      <button onClick={() => removeFromCart(cItem.cartKey)} className="text-red-400 font-bold text-xl px-2 shrink-0">&times;</button>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between items-end mb-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-xs">Total Comandă</span>
                  <span className="text-3xl font-black text-white">{cartTotal.toFixed(2)} Lei</span>
                </div>
                <button
                  onClick={sendWaiterOrder}
                  disabled={isSendingOrder}
                  className="w-full bg-orange-500 hover:bg-orange-400 text-white py-4 rounded-2xl font-black text-lg transition-transform active:scale-95 shadow-xl disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSendingOrder ? "Se trimite..." : "TRIMITE LA BUCĂTĂRIE"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Item Modal pentru instrucțiuni speciale */}
      {itemToAdd && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60] p-4" onClick={() => setItemToAdd(null)}>
          <div className="bg-slate-900 rounded-3xl p-6 w-full max-w-sm shadow-2xl flex flex-col border border-slate-800" onClick={e => e.stopPropagation()}>
            <h3 className="text-2xl font-black text-white mb-2">{itemToAdd.name}</h3>
            <p className="text-sm font-bold text-green-400 mb-6">{itemToAdd.price} Lei</p>
            <textarea
              placeholder="Mențiuni speciale (opțional)..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 min-h-[100px] mb-6 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={specialInstructions}
              onChange={e => setSpecialInstructions(e.target.value)}
            />
            <div className="flex gap-3">
              <button onClick={() => setItemToAdd(null)} className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold rounded-xl transition-colors">Anulează</button>
              <button onClick={confirmAddToCart} className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl shadow-lg transition-colors">Confirmă</button>
            </div>
          </div>
        </div>
      )}
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
