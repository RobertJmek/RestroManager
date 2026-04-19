"use client";

import React, { useState, useEffect } from 'react'; // Adăugat useEffect
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BellRing } from "lucide-react"; // Importă un icon pentru buton

// Mock Data... (rămâne neschimbat)
const MOCK_MENU = [
  { id: 1, name: "Burger Wagyu Suprem", description: "Carne wagyu, trufe, cheddar maturat și chiflă neagră cu susan", price: 65, category: "Mains", img: "🍔" },
  { id: 2, name: "Pizza Quattro Formaggi", description: "Mozzarella, gorgonzola, parmezan, emmental, pe un blat subțire napoletan", price: 45, category: "Mains", img: "🍕" },
  { id: 3, name: "Cocktail Aperol Sunset", description: "Aperol, prosecco, apă minerală și felii de portocală roșie proaspătă", price: 25, category: "Drinks", img: "🍹" },
  { id: 4, name: "Lava Cake Artizanal", description: "Ciocolată belgiană fierbinte asortată cu înghețată de vanilie de Madagascar", price: 30, category: "Desserts", img: "🌋" }
];

export default function CustomerPage() {
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [instructions, setInstructions] = useState("");
  const [socket, setSocket] = useState<WebSocket | null>(null);

  // Inițializăm conexiunea WS pentru client (Issue 3.1)
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/customer");
    setSocket(ws);
    return () => ws.close();
  }, []);

  // Funcție pentru Chemare Chelner (Issue 2.4)
  const handleCallWaiter = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        action: "CALL_WAITER",
        table: 2 // Masa simulată
      }));
      alert("🔔 Chelnerul a fost solicitat la masa ta!");
    } else {
      alert("❌ Eroare de conexiune. Încearcă din nou.");
    }
  };

  const handleAddToCart = async (item: any) => {
    try {
      const orderPayload = {
        id: Math.floor(Math.random() * 1000),
        table_number: 2,
        items: [{ name: item.name, quantity: 1, prep_time: 15 }],
        notes: instructions
      };

      const response = await fetch("http://localhost:8000/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderPayload),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`🚀 Comandă trimisă! AI Priority: ${result.ai_safety}`);
      } else {
        alert("❌ Eroare la trimiterea comenzii.");
      }
    } catch (error) {
      console.error("Eroare conexiune:", error);
    }
    setInstructions("");
    setSelectedItem(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 p-4 sm:p-8 font-sans text-slate-100">
      
      {/* Premium Header */}
      <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 p-8 sm:p-12 mb-12 shadow-2xl border border-white/10 relative overflow-hidden">
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
                  <span className="text-2xl font-black text-violet-400">{item.price} <span className="text-sm font-medium text-slate-500">RON</span></span>
                  
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="secondary" className="bg-violet-600 hover:bg-violet-500 text-white rounded-full px-8 py-6 text-md font-semibold transition-all hover:-translate-y-1">
                        Comandă
                      </Button>
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
      <div className="fixed bottom-6 right-6 z-50">
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