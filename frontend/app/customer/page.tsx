"use client";

import React, { useState } from 'react';
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

// Mock Data - Baza de date statica temporara
const MOCK_MENU = [
  { id: 1, name: "Burger Wagyu Suprem", description: "Carne wagyu, trufe, cheddar maturat și chiflă neagră cu susan", price: 65, category: "Mains", img: "🍔" },
  { id: 2, name: "Pizza Quattro Formaggi", description: "Mozzarella, gorgonzola, parmezan, emmental, pe un blat subțire napoletan", price: 45, category: "Mains", img: "🍕" },
  { id: 3, name: "Cocktail Aperol Sunset", description: "Aperol, prosecco, apă minerală și felii de portocală roșie proaspătă", price: 25, category: "Drinks", img: "🍹" },
  { id: 4, name: "Lava Cake Artizanal", description: "Ciocolată belgiană fierbinte asortată cu înghețată de vanilie de Madagascar", price: 30, category: "Desserts", img: "🌋" }
];

export default function CustomerPage() {
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [instructions, setInstructions] = useState("");

  const handleAddToCart = (item: any) => {
    // Aici in Etapa 4 vom trimite efectiv catre cos si Endpoint-ul de comanda
    alert(`✅ Succes! Ai trimis in simulare Cos: ${item.name}\nNota bucatar: ${instructions || 'Fara mentiuni'}`);
    setInstructions("");
  };

  return (
    <div className="min-h-screen bg-slate-950 p-4 sm:p-8 font-sans text-slate-100">
      
      {/* Premium Header Container WOW */}
      <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 p-8 sm:p-12 mb-12 shadow-2xl shadow-indigo-500/20 transform transition-all duration-500 hover:scale-[1.01] border border-white/10 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-white opacity-5 blur-3xl"></div>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white tracking-tight mb-4 relative z-10">
          Restro<span className="text-violet-200">Manager</span>
        </h1>
        <p className="text-indigo-100 text-lg md:text-xl max-w-xl relative z-10 font-light">
          Meniul tău digital interactiv. Răsfoiește preparatele, personalizează-le și plasează comanda din 2 atingeri.
        </p>
      </div>

      {/* Grid Catalog Interactiv */}
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
        {MOCK_MENU.map((item) => (
          <Card key={item.id} className="bg-slate-900 border-slate-800 text-slate-100 shadow-2xl overflow-hidden hover:border-violet-500/50 hover:shadow-violet-900/20 transition-all duration-300 group">
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
                      <Button variant="secondary" className="bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-900/50 rounded-full px-8 py-6 text-md font-semibold transition-all hover:-translate-y-1" onClick={() => setSelectedItem(item)}>
                        Comandă
                      </Button>
                    </DialogTrigger>
                    
                    {/* Modal-ul de Instructiuni Speciale (Issue 2.1) */}
                    <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[450px] shadow-2xl shadow-black">
                      <DialogHeader>
                        <DialogTitle className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-indigo-400">{item.name}</DialogTitle>
                        <DialogDescription className="text-slate-400 text-md mt-2">
                          Personalizează-ți comada. Ai vreo alergie sau preferințe de preparare? (Ex: Rare, fără sos).
                        </DialogDescription>
                      </DialogHeader>
                      
                      <div className="grid gap-4 py-6">
                        <textarea 
                          placeholder="Tastează aici instrucțiunile tale ascunse..."
                          className="w-full bg-slate-950 text-white rounded-xl p-5 min-h-[120px] border border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none transition-all resize-none shadow-inner"
                          value={instructions}
                          onChange={(e) => setInstructions(e.target.value)}
                        />
                      </div>
                      
                      <DialogFooter>
                        <Button className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-full py-7 text-lg font-bold shadow-xl shadow-violet-900/40 border-0" onClick={() => handleAddToCart(item)}>
                          🛒 Adaugă pt. {item.price} RON
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
  );
}
