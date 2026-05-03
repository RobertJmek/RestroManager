"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

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

function MenuCard({ item }: { item: MenuItem }) {
  return (
    <Card className="bg-slate-900 border-slate-800 text-slate-100 shadow-2xl overflow-hidden hover:border-violet-500/50 transition-all group">
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
            <span className="text-sm text-slate-500 italic">Scanează QR-ul mesei pentru a comanda</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function MenuPage() {
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API_URL}/menu`)
      .then(res => {
        if (!res.ok) throw new Error(`Eroare ${res.status}`);
        return res.json();
      })
      .then(data => {
        setMenu(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Menu fetch failed:", err);
        setError(err instanceof Error ? err.message : "Eroare necunoscută");
        setLoading(false);
      });
  }, []);

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

      <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 p-8 sm:p-12 mb-12 shadow-2xl border border-white/10">
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white tracking-tight mb-4">
          Restro<span className="text-violet-200">Manager</span>
        </h1>
        <p className="text-indigo-100 text-lg md:text-xl max-w-xl font-light">
          Meniul nostru. Scanează codul QR al mesei pentru a comanda.
        </p>
      </div>

      {/* Filter bar */}
      {!loading && !error && categories.length > 0 && (
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

      <div className="max-w-5xl mx-auto">
        {loading && (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <div className="text-slate-400 text-xl">Se încarcă meniul...</div>
          </div>
        )}
        {!loading && error && (
          <div className="text-center py-12">
            <div className="text-slate-400 text-xl">Meniul este indisponibil momentan.</div>
          </div>
        )}
        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-12">
            <div className="text-slate-400 text-xl">Niciun produs în această categorie.</div>
          </div>
        )}

        {/* Grouped by category (when "Toate" is selected) */}
        {!loading && !error && grouped && Object.entries(grouped).map(([cat, items]) => (
          items.length > 0 && (
            <div key={cat} className="mb-12">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <span>{getCategoryEmoji(cat)}</span> {cat}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
                {items.map(item => <MenuCard key={item.id} item={item} />)}
              </div>
            </div>
          )
        ))}

        {/* Flat list (when a category is selected) */}
        {!loading && !error && !grouped && filtered.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
            {filtered.map(item => <MenuCard key={item.id} item={item} />)}
          </div>
        )}
      </div>
    </div>
  );
}
