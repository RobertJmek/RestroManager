"use client";

import React, { useState, useEffect } from 'react'; // Adăugat useEffect
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BellRing, ShoppingCart, CreditCard, Trash2 } from "lucide-react"; // Importăm iconițe adiționale

// Mock Data... (rămâne neschimbat)
const MOCK_MENU = [
  { id: 1, name: "Burger Wagyu Suprem", description: "Carne wagyu, trufe, cheddar maturat și chiflă neagră cu susan", price: 65, category: "Mains", img: "🍔" },
  { id: 2, name: "Pizza Quattro Formaggi", description: "Mozzarella, gorgonzola, parmezan, emmental, pe un blat subțire napoletan", price: 45, category: "Mains", img: "🍕" },
  { id: 3, name: "Cocktail Aperol Sunset", description: "Aperol, prosecco, apă minerală și felii de portocală roșie proaspătă", price: 25, category: "Drinks", img: "🍹" },
  { id: 4, name: "Lava Cake Artizanal", description: "Ciocolată belgiană fierbinte asortată cu înghețată de vanilie de Madagascar", price: 30, category: "Desserts", img: "🌋" }
];

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import UserProfileMenu from "../../components/ui/UserProfileMenu";

function CustomerContent() {
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [instructions, setInstructions] = useState("");
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [tableId, setTableId] = useState<number | null>(null);
  
  const searchParams = useSearchParams();
  const urlTableId = searchParams.get('table_id');

  // Starea pentru coșul de cumpărături
  const [cart, setCart] = useState<any[]>([]);
  const [isCartOpen, setIsCartOpen] = useState(false);

  // Autentificare Guest bazată pe URL
  useEffect(() => {
    async function authGuest() {
      if (!urlTableId) return;
      
      const tId = parseInt(urlTableId);
      setTableId(tId);

      try {
        const response = await fetch(`http://localhost:8000/api/auth/guest-login/${tId}`, {
          method: "POST"
        });
        const data = await response.json();
        if (response.ok) {
          localStorage.setItem("token", data.access_token);
          localStorage.setItem("user_role", "Guest");
          localStorage.setItem("table_id", tId.toString());
          console.log("Authenticated as Guest for table", tId);
        }
      } catch (err) {
        console.error("Guest auth failed", err);
      }
    }
    
    authGuest();
  }, [urlTableId]);

  // Inițializăm conexiunea WS pentru client
  useEffect(() => {
    // În realitate, ar trebui să trimitem token-ul și aici
    const ws = new WebSocket("ws://localhost:8000/ws/customer");
    setSocket(ws);
    return () => ws.close();
  }, []);

  // Funcție pentru Chemare Chelner
  const handleCallWaiter = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        action: "CALL_WAITER",
        table: tableId || 0
      }));
      alert("🔔 Chelnerul a fost solicitat la masa ta!");
    } else {
      alert("❌ Eroare de conexiune. Încearcă din nou.");
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
    alert(`✅ ${item.name} a fost adăugat în coș!`);
  };

  const removeFromCart = (idToRemove: string) => {
    setCart(cart.filter(item => item.id !== idToRemove));
  };

  const cartTotal = cart.reduce((total, item) => total + (item.price * item.quantity), 0);

  const handleCheckout = async () => {
    if (cart.length === 0) return;

    try {
      const token = localStorage.getItem("token");
      const orderPayload = {
        id: Math.floor(Math.random() * 1000),
        table_number: tableId,
        items: cart.map(item => ({ name: item.name, quantity: item.quantity, prep_time: 15 })),
        notes: cart.map(item => item.notes).filter(n => n).join(" | "),
        total: cartTotal
      };

      const response = await fetch("http://localhost:8000/api/orders", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(orderPayload),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`🔒 Redirecționare către Stripe pentru suma de ${cartTotal.toFixed(2)} RON...\n\n(AI Priority atribuit comenzii: ${result.ai_safety})`);
        
        setCart([]);
        setIsCartOpen(false);
        window.location.href = "/customer/success";
      } else {
        const errData = await response.json();
        alert(`❌ Eroare: ${errData.detail || "Nu s-a putut plasa comanda."}`);
      }
    } catch (error) {
      console.error("Eroare conexiune:", error);
      alert("❌ Nu ne-am putut conecta la server.");
    }
  };

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

      {/* Grid Catalog */}
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
        {MOCK_MENU.map((item) => (
          <Card key={item.id} className="bg-slate-900 border-slate-800 text-slate-100 shadow-2xl overflow-hidden hover:border-violet-500/50 transition-all group">
            <div className="flex flex-col sm:flex-row p-6 sm:p-8 h-full">
              <div className="text-7xl sm:text-8xl sm:mr-8 my-auto drop-shadow-2xl text-center mb-4 sm:mb-0 group-hover:scale-110 transition-transform duration-500">
                {item.img}
              </div>
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
                          className="w-full bg-slate-950 text-white rounded-xl p-5 min-h-[120px] border border-slate-700 focus:border-violet-500 outline-none"
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
                        {cartItem.notes && <p className="text-xs text-slate-400">Notă: {cartItem.notes}</p>}
                        <p className="text-sm text-indigo-300">{cartItem.price.toFixed(2)} RON</p>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => removeFromCart(cartItem.id)} className="text-red-400 hover:text-red-300 hover:bg-red-400/10">
                        <Trash2 size={18} />
                      </Button>
                    </div>
                  ))}
                  <div className="border-t border-slate-700 mt-2 pt-4 flex justify-between items-center">
                    <span className="text-lg font-medium text-slate-300">Total:</span>
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
                <CreditCard size={20} /> Checkout cu Stripe
              </Button>
            </DialogFooter>
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