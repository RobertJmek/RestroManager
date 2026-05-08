"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BellRing, ShoppingCart, CreditCard, Trash2 } from "lucide-react";

const CATEGORY_EMOJIS: Record<string, string> = {
  "Băuturi": "🍹", "Drinks": "🍹",
  "Burgeri": "🍔", "Burgers": "🍔",
  "Pizza": "🍕",
  "Desert": "🍰", "Desserts": "🍰",
  "Mains": "🍽️", "Main Course": "🍽️",
};

function getCategoryEmoji(category: string): string {
  return CATEGORY_EMOJIS[category] || "🍽️";
}

interface MenuItem {
  id: number;
  name: string;
  description: string | null;
  price: number;
  category: string;
  image_url: string | null;
  is_available: boolean;
}

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import UserProfileMenu from "../../components/ui/UserProfileMenu";

function CustomerContent() {
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [instructions, setInstructions] = useState("");
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [tableId, setTableId] = useState<number | null>(null);
  const [guestToken, setGuestToken] = useState<string | null>(null);

  const searchParams = useSearchParams();
  const urlTableId = searchParams.get('table_id');

  const [cart, setCart] = useState<any[]>([]);
  const [isCartOpen, setIsCartOpen] = useState(false);

  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState(true);
  const [menuError, setMenuError] = useState<string | null>(null);
  
  const [isBillDialogOpen, setIsBillDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Autentificare Guest bazată pe URL
  useEffect(() => {
    if (!urlTableId) {
      setMenuLoading(false);
      setMenuError("Lipsește parametrul table_id din URL");
      return;
    }

    const tId = parseInt(urlTableId);
    setTableId(tId);

    async function authGuest() {

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/auth/guest-login/${tId}`, {
          method: "POST"
        });
        const data = await response.json();
        if (response.ok) {
          // Store guest session under separate keys so we don't clobber an existing staff session
          localStorage.setItem("guest_token", data.access_token);
          localStorage.setItem("guest_table_id", tId.toString());
          setGuestToken(data.access_token);
          console.log("Authenticated as Guest for table", tId);
        } else {
          setMenuLoading(false);
          setMenuError("Autentificare eșuată");
        }
      } catch (err) {
        console.error("Guest auth failed", err);
        setMenuLoading(false);
        setMenuError("Eroare de autentificare");
      }
    }

    authGuest();
  }, [urlTableId]);

  // Inițializăm conexiunea WS pentru client după autentificare
  useEffect(() => {
    if (!guestToken) return;
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace("https://", "wss://").replace("http://", "ws://").replace("/api", "");
    const ws = new WebSocket(`${wsUrl}/ws/guest?token=${encodeURIComponent(guestToken)}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "SESSION_CLOSED" && String(data.table) === urlTableId) {
           localStorage.removeItem("guest_token");
           localStorage.removeItem("guest_table_id");
           window.location.href = "/customer/thank-you";
        }
      } catch (err) {
        console.error("Eroare parsare mesaj WS:", err);
      }
    };
    setSocket(ws);
    return () => ws.close();
  }, [guestToken]);

  // Fetch menu from API
  useEffect(() => {
    if (!guestToken) return;
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    setMenuLoading(true);
    setMenuError(null);
    // BUG FIX: endpoint-ul e GET /api/menu/ (cu trailing slash)
    fetch(`${API_URL}/menu/`, {
      headers: { Authorization: `Bearer ${guestToken}` },
    })
      .then(res => {
        if (!res.ok) throw new Error(`Eroare ${res.status}`);
        return res.json();
      })
      .then(data => {
        setMenu(data);
        setMenuLoading(false);
      })
      .catch(err => {
        console.error("Menu fetch failed:", err);
        setMenuError(err instanceof Error ? err.message : "Eroare necunoscută");
        setMenuLoading(false);
      });
  }, [guestToken]);

  // Funcție pentru Chemare Chelner
  const handleCallWaiter = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        action: "CALL_WAITER",
        table: tableId || 0
      }));
      showToast("🔔 Chelnerul a fost solicitat la masa ta!");
    } else {
      showToast("❌ Eroare de conexiune. Încearcă din nou.", "error");
    }
  };

  const handleAddToCart = (item: any) => {
    const newItem = {
      id: Math.random().toString(36).substr(2, 9),
      productId: item.id,
      name: item.name,
      price: item.price,
      quantity: 1,
      notes: instructions
    };

    setCart([...cart, newItem]);
    setInstructions("");
    setSelectedItem(null);
    showToast(`✅ ${item.name} a fost adăugat în coș!`);
  };

  const removeFromCart = (idToRemove: string) => {
    setCart(cart.filter(item => item.id !== idToRemove));
  };

  const cartTotal = cart.reduce((total, item) => total + (item.price * item.quantity), 0);

  const handleCheckout = async () => {
    if (cart.length === 0) return;
    if (!guestToken) {
      showToast("❌ Sesiunea de oaspete nu este inițializată. Te rugăm să reîncărci pagina.", "error");
      return;
    }

    try {
      const token = guestToken;
      // BUG FIX: eliminat câmpul `id` din payload — nu e definit în backend schema
      // și genera un câmp random care putea cauza confuzii
      const orderPayload = {
        table_number: tableId,
        items: cart.map(item => ({ 
          menu_item_id: item.productId, 
          name: item.name, 
          quantity: item.quantity, 
          prep_time: 15,
          special_instructions: item.notes || null 
        })),
        total: cartTotal
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(orderPayload),
      });

      if (response.ok) {
        const result = await response.json();
        showToast(`✅ Comanda a fost plasată! Total: ${cartTotal.toFixed(2)} RON`);
        console.log("AI Priority:", result.ai_safety, "Order ID:", result.order_id);

        setCart([]);
        setIsCartOpen(false);
        // BUG FIX: păstrăm table_id în URL pentru ca pagina success să poată naviga înapoi
        window.location.replace(`/customer/success?table_id=${tableId}`);
      } else {
        const errData = await response.json();
        showToast(`❌ Eroare: ${errData.detail || "Nu s-a putut plasa comanda."}`, "error");
      }
    } catch (error) {
      console.error("Eroare conexiune:", error);
      showToast("❌ Nu ne-am putut conecta la server.", "error");
    }
  };

  const handleRequestBill = async (method: "cash" | "card") => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await fetch(`${API_URL}/tables/${tableId}/request-bill`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${guestToken}`
        },
        body: JSON.stringify({ payment_method: method })
      });
      if (res.ok) {
        showToast("✅ Am chemat chelnerul cu nota de plată!");
        setIsBillDialogOpen(false);
      } else {
        showToast("❌ Eroare la cererea notei.", "error");
      }
    } catch (err) {
      showToast("❌ Eroare conexiune.", "error");
    }
  };

  const availableItems = menu.filter(i => i.is_available);
  const categories = Array.from(new Set(availableItems.map(i => i.category))).sort();
  const filtered = selectedCategory
    ? availableItems.filter(i => i.category === selectedCategory)
    : availableItems;
  const grouped = selectedCategory
    ? null
    : categories.reduce<Record<string, MenuItem[]>>((acc, cat) => {
        acc[cat] = filtered.filter(i => i.category === cat);
        return acc;
      }, {});

  return (
    <div className="min-h-screen bg-slate-950 p-4 sm:p-8 font-sans text-slate-100">

      {/* Premium Header */}
      <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 p-8 sm:p-12 mb-12 shadow-2xl border border-white/10 relative">
        {/* Profile Overlay */}
        <div className="absolute top-6 right-6 z-20">
          <UserProfileMenu />
        </div>

        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white tracking-tight mb-4 relative z-10">
          Restro<span className="text-violet-200">Manager</span>
        </h1>
        <p className="text-indigo-100 text-lg md:text-xl max-w-xl relative z-10 font-light">
          Meniul tău digital interactiv. Răsfoiește preparatele și plasează comanda instant.
        </p>
      </div>

      {/* Filter bar */}
      {!menuLoading && !menuError && categories.length > 0 && (
        <div className="max-w-5xl mx-auto mb-10 flex flex-wrap gap-2 justify-center">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
              selectedCategory === null
                ? "bg-violet-600 text-white shadow-lg"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
            }`}
          >
            Toate
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                selectedCategory === cat
                  ? "bg-violet-600 text-white shadow-lg"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
              }`}
            >
              {getCategoryEmoji(cat)} {cat}
            </button>
          ))}
        </div>
      )}

      {/* Grid Catalog */}
      <div className="max-w-5xl mx-auto">
        {menuLoading && (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <div className="text-slate-400 text-xl">Se încarcă meniul...</div>
          </div>
        )}
        {!menuLoading && menuError && (
          <div className="text-center py-12">
            <div className="text-slate-400 text-xl mb-4">{menuError}</div>
            {!urlTableId && (
              <a href="/menu" className="text-violet-400 hover:text-violet-300 underline text-lg">
                Vezi meniul public
              </a>
            )}
          </div>
        )}
        {!menuLoading && !menuError && filtered.length === 0 && (
          <div className="text-center py-12">
            <div className="text-slate-400 text-xl">Niciun produs în această categorie.</div>
          </div>
        )}

        {/* Grouped by category */}
        {!menuLoading && !menuError && grouped && Object.entries(grouped).map(([cat, items]) => (
          items.length > 0 && (
            <div key={cat} className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <span>{getCategoryEmoji(cat)}</span> {cat}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
                {items.map((item) => (
                  <Card key={item.id} className="bg-slate-900 border-slate-800 text-slate-100 shadow-2xl overflow-hidden hover:border-violet-500/50 transition-all group">
                    <div className="flex flex-col sm:flex-row p-6 sm:p-8 h-full">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-24 h-24 sm:w-32 sm:h-32 sm:mr-8 mx-auto sm:mx-0 self-start rounded-xl object-cover shadow-2xl mb-4 sm:mb-0 shrink-0 group-hover:scale-110 transition-transform duration-500"
                        />
                      ) : (
                        <div className="text-7xl sm:text-8xl sm:mr-8 mx-auto sm:mx-0 self-start drop-shadow-2xl text-center mb-4 sm:mb-0 shrink-0 group-hover:scale-110 transition-transform duration-500">
                          {getCategoryEmoji(item.category)}
                        </div>
                      )}
                      <div className="flex flex-col flex-1">
                        <CardTitle className="text-2xl sm:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 mb-3">
                          {item.name}
                        </CardTitle>
                        <CardDescription className="text-slate-400 text-sm sm:text-base mb-6 leading-relaxed flex-grow">
                          {item.description}
                        </CardDescription>
                        <div className="flex items-center justify-between mt-auto pt-4 border-t border-slate-800">
                          <span className="text-2xl font-black text-violet-400">{item.price.toFixed(2)} <span className="text-sm font-medium text-slate-500">RON</span></span>

                          <Dialog>
                            <DialogTrigger render={<Button variant="secondary" className="bg-violet-600 hover:bg-violet-500 text-white rounded-full px-8 py-6 text-md font-semibold transition-all hover:-translate-y-1" />}>
                              Comandă
                            </DialogTrigger>
                            <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[450px]">
                              <DialogHeader>
                                <DialogTitle className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-indigo-400">{item.name}</DialogTitle>
                              </DialogHeader>
                              <div className="grid gap-4 py-6">
                                <textarea
                                  placeholder="Note speciale (alergii, preferințe)..."
                                  className="w-full bg-slate-950 text-white rounded-xl p-5 min-h-[120px] border border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 outline-none"
                                  value={instructions}
                                  onChange={(e) => setInstructions(e.target.value)}
                                />
                              </div>
                              <DialogFooter>
                                <Button className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 py-7 text-lg font-bold rounded-full" onClick={() => handleAddToCart(item)}>
                                  🛒 Adaugă în coș
                                </Button>
                              </DialogFooter>
                            </DialogContent>
                          </Dialog>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )
        ))}

        {/* Flat list when category selected */}
        {!menuLoading && !menuError && !grouped && filtered.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
            {filtered.map((item) => (
              <Card key={item.id} className="bg-slate-900 border-slate-800 text-slate-100 shadow-2xl overflow-hidden hover:border-violet-500/50 transition-all group">
                <div className="flex flex-col sm:flex-row p-6 sm:p-8 h-full">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="w-24 h-24 sm:w-32 sm:h-32 sm:mr-8 mx-auto sm:mx-0 self-start rounded-xl object-cover shadow-2xl mb-4 sm:mb-0 shrink-0 group-hover:scale-110 transition-transform duration-500"
                    />
                  ) : (
                    <div className="text-7xl sm:text-8xl sm:mr-8 mx-auto sm:mx-0 self-start drop-shadow-2xl text-center mb-4 sm:mb-0 shrink-0 group-hover:scale-110 transition-transform duration-500">
                      {getCategoryEmoji(item.category)}
                    </div>
                  )}
                  <div className="flex flex-col flex-1">
                    <CardTitle className="text-2xl sm:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 mb-3">
                      {item.name}
                    </CardTitle>
                    <CardDescription className="text-slate-400 text-sm sm:text-base mb-6 leading-relaxed flex-grow">
                      {item.description}
                    </CardDescription>
                    <div className="flex items-center justify-between mt-auto pt-4 border-t border-slate-800">
                      <span className="text-2xl font-black text-violet-400">{item.price.toFixed(2)} <span className="text-sm font-medium text-slate-500">RON</span></span>

                      <Dialog>
                        <DialogTrigger render={<Button variant="secondary" className="bg-violet-600 hover:bg-violet-500 text-white rounded-full px-8 py-6 text-md font-semibold transition-all hover:-translate-y-1" />}>
                          Comandă
                        </DialogTrigger>
                        <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[450px]">
                          <DialogHeader>
                            <DialogTitle className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-indigo-400">{item.name}</DialogTitle>
                          </DialogHeader>
                          <div className="grid gap-4 py-6">
                            <textarea
                              placeholder="Mențiuni speciale (opțional)..."
                              className="w-full bg-slate-950 text-white rounded-xl p-5 min-h-[120px] border border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 outline-none"
                              value={instructions}
                              onChange={(e) => setInstructions(e.target.value)}
                            />
                          </div>
                          <DialogFooter>
                            <Button className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 py-7 text-lg font-bold rounded-full" onClick={() => handleAddToCart(item)}>
                              🛒 Adaugă în coș
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* BUTON PLUTITOR: Cheamă Chelnerul (Issue 2.4) */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-4">

        {/* BUTON COȘ CUMPĂRĂTURI */}
        <Dialog open={isCartOpen} onOpenChange={setIsCartOpen}>
          <DialogTrigger render={<Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full w-16 h-16 shadow-2xl flex flex-col items-center justify-center p-0 transition-transform hover:scale-110 active:scale-90 border-2 border-indigo-400 relative" />}>
            <ShoppingCart size={24} />
            {cart.length > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center border-2 border-slate-950">
                {cart.length}
              </span>
            )}
            <span className="text-[10px] font-bold mt-1 uppercase leading-none">Coș</span>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold flex items-center gap-2">
                <ShoppingCart className="text-indigo-400" /> Coșul tău
              </DialogTitle>
            </DialogHeader>
            <div className="py-4 max-h-[400px] overflow-y-auto">
              {cart.length === 0 ? (
                <p className="text-slate-400 text-center py-8">Coșul este gol.</p>
              ) : (
                <div className="flex flex-col gap-4">
                  {cart.map((cartItem) => (
                    <div key={cartItem.id} className="flex justify-between items-center bg-slate-800 p-3 rounded-lg border border-slate-700">
                      <div>
                        <p className="font-bold text-white">{cartItem.name}</p>
                        {cartItem.notes && <p className="text-xs text-slate-400 italic">Notă: {cartItem.notes}</p>}
                        <p className="text-sm text-indigo-300">{cartItem.price.toFixed(2)} RON</p>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => removeFromCart(cartItem.id)} className="text-red-400 hover:text-red-300 hover:bg-red-400/10">
                        <Trash2 size={18} />
                      </Button>
                    </div>
                  ))}
                  <div className="border-t border-slate-700 mt-2 pt-4 flex justify-between items-center">
                    <span className="text-lg font-medium text-slate-200">Total:</span>
                    <span className="text-2xl font-black text-white">{cartTotal.toFixed(2)} RON</span>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 py-6 text-lg font-bold rounded-xl flex items-center gap-2"
                onClick={handleCheckout}
                disabled={cart.length === 0}
              >
                <ShoppingCart size={20} /> Trimite Comanda
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* BUTON CERE NOTA */}
        <Button
          onClick={() => setIsBillDialogOpen(true)}
          className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-full w-16 h-16 shadow-2xl flex flex-col items-center justify-center p-0 transition-transform hover:scale-110 active:scale-90 border-2 border-emerald-400"
        >
          <CreditCard size={24} />
          <span className="text-[10px] font-bold mt-1 uppercase leading-none">Notă</span>
        </Button>
        <Dialog open={isBillDialogOpen} onOpenChange={setIsBillDialogOpen}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold flex items-center gap-2">
                💳 Cum dorești să plătești?
              </DialogTitle>
            </DialogHeader>
            <div className="py-6 flex flex-col gap-4">
              <Button onClick={() => handleRequestBill("cash")} className="w-full bg-green-600 hover:bg-green-500 py-8 text-lg font-bold rounded-xl flex items-center justify-center gap-3">
                <span className="text-2xl">💵</span> Cash (Numerar)
              </Button>
              <Button onClick={() => handleRequestBill("card")} className="w-full bg-blue-600 hover:bg-blue-500 py-8 text-lg font-bold rounded-xl flex items-center justify-center gap-3">
                <span className="text-2xl">💳</span> Card (POS)
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* BUTON CHELNER */}
        <Button
          onClick={handleCallWaiter}
          className="bg-red-600 hover:bg-red-500 text-white rounded-full w-16 h-16 shadow-2xl flex flex-col items-center justify-center p-0 transition-transform hover:scale-110 active:scale-90 border-2 border-red-400"
        >
          <BellRing size={24} />
          <span className="text-[10px] font-bold mt-1 uppercase leading-none">Ajutor</span>
        </Button>
      </div>

      {toast && (
        <div className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
          toast.type === "success" ? "bg-green-600" : "bg-red-600"
        } text-white font-medium`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default function CustomerPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Se încarcă meniul...</div>}>
      <CustomerContent />
    </Suspense>
  );
}
