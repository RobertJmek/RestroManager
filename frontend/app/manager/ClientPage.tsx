"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import UserProfileMenu from "@/components/ui/UserProfileMenu";
import ClientRoleGuard from "@/components/ClientRoleGuard";
import { apiRequest } from "@/lib/api";
import { Pencil, Trash2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface MenuItem {
  id: number;
  name: string;
  description: string | null;
  category: string;
  price: number;
  image_url: string | null;
  ingredients: string | null;
  is_available: boolean;
  prep_time_minutes: number | null;
  dietary_tags: string | null;
}

interface Category {
  id: number;
  name: string;
  description: string | null;
}

const CATEGORY_EMOJIS: Record<string, string> = {
  "Băuturi": "🍹",
  "Drinks": "🍹",
  "Burgeri": "🍔",
  "Burgers": "🍔",
  "Pizza": "🍕",
  "Desert": "🍰",
  "Desserts": "🍰",
};

function getEmoji(category: string): string {
  return CATEGORY_EMOJIS[category] || "🍽️";
}

export default function ManagerPage() {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);

  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formPrice, setFormPrice] = useState("");
  const [formCategoryId, setFormCategoryId] = useState("");
  const [formIngredients, setFormIngredients] = useState("");
  const [formPrepTime, setFormPrepTime] = useState("");
  const [formDietary, setFormDietary] = useState("");
  const [isFormAvailable, setIsFormAvailable] = useState(true);

  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [compressionStats, setCompressionStats] = useState<{ original: number; optimized: number } | null>(null);

  const [toast, setToast] = useState<{ message: string; type: "success" | "error"; visible: boolean } | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error" = "success") => {
    setToast({ message, type, visible: true });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [menuRes, catRes] = await Promise.all([
        apiRequest("/menu"),
        apiRequest("/categories"),
      ]);
      if (!menuRes.ok) throw new Error("Eroare la încărcarea meniului");
      if (!catRes.ok) throw new Error("Eroare la încărcarea categoriilor");
      setMenuItems(await menuRes.json());
      setCategories(await catRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare necunoscută");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function resetForm() {
    setFormName("");
    setFormDescription("");
    setFormPrice("");
    setFormCategoryId("");
    setFormIngredients("");
    setFormPrepTime("");
    setFormDietary("");
    setIsFormAvailable(true);
    setPreviewImage(null);
    setImageUrl(null);
    setCompressionStats(null);
  }

  function handleAddNew() {
    setEditingItem(null);
    resetForm();
    setIsModalOpen(true);
  }

  function handleEdit(item: MenuItem) {
    setEditingItem(item);
    setFormName(item.name);
    setFormDescription(item.description || "");
    setFormPrice(item.price.toString());
    const cat = categories.find((c) => c.name === item.category);
    setFormCategoryId(cat ? cat.id.toString() : "");
    setFormIngredients(item.ingredients || "");
    setFormPrepTime(item.prep_time_minutes?.toString() || "");
    setFormDietary(item.dietary_tags || "");
    setIsFormAvailable(item.is_available);
    setPreviewImage(item.image_url);
    setImageUrl(item.image_url);
    setIsModalOpen(true);
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10_000_000) {
      showToast("Imaginea depășește limita de 10 MB", "error");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) {
      showToast("Format invalid. Acceptăm: JPG, PNG, WebP, GIF", "error");
      return;
    }
    setUploadingImage(true);
    setCompressionStats(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/menu/upload-image`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload eșuat");
      }
      const data = await res.json();
      setImageUrl(data.image_url);
      setPreviewImage(data.image_url);
      const originalSizeKB = (file.size / 1024).toFixed(1);
      const optimizedSizeKB = data.size_kb;
      const compressionPercent = Math.round((1 - optimizedSizeKB / (file.size / 1024)) * 100);
      setCompressionStats({ original: file.size, optimized: optimizedSizeKB * 1024 });
      showToast(`Imagine optimizată: ${originalSizeKB}KB → ${optimizedSizeKB}KB (${compressionPercent}% redus)`);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Eroare la încărcarea imaginii", "error");
    } finally {
      setUploadingImage(false);
    }
  }

  async function handleSave() {
    if (!formName.trim() || !formPrice || !formCategoryId) {
      showToast("Completează numele, prețul și categoria", "error");
      return;
    }
    const payload: Record<string, unknown> = {
      name: formName.trim(),
      description: formDescription.trim() || null,
      category_id: parseInt(formCategoryId),
      price: parseFloat(formPrice),
      image_url: imageUrl || null,
      ingredients: formIngredients.trim() || null,
      prep_time_minutes: formPrepTime ? parseInt(formPrepTime) : null,
      dietary_tags: formDietary.trim() || null,
    };
    if (editingItem) payload.is_available = isFormAvailable;
    setSaving(true);
    try {
      let res: Response;
      if (editingItem) {
        res = await apiRequest(`/menu/${editingItem.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        res = await apiRequest("/menu", { method: "POST", body: JSON.stringify(payload) });
      }
      if (!res.ok) {
        const err = await res.json();
        let message = "Salvare eșuată";
        if (typeof err.detail === "string") message = err.detail;
        else if (Array.isArray(err.detail) && err.detail.length > 0) message = err.detail.map((e: any) => e.msg || JSON.stringify(e)).join("; ");
        else if (err.detail) message = JSON.stringify(err.detail);
        throw new Error(message);
      }
      setIsModalOpen(false);
      resetForm();
      loadData();
      showToast(editingItem ? "Produs actualizat cu succes" : "Produs adăugat cu succes");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Eroare la salvare", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Ești sigur că vrei să ștergi acest produs?")) return;
    try {
      const res = await apiRequest(`/menu/${id}`, { method: "DELETE" });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Ștergere eșuată"); }
      loadData();
      showToast("Produs șters cu succes");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Eroare la ștergere", "error");
    }
  }

  async function handleToggleAvailability(item: MenuItem) {
    try {
      const res = await apiRequest(`/menu/${item.id}`, { method: "PUT", body: JSON.stringify({ is_available: !item.is_available }) });
      if (!res.ok) throw new Error("Actualizare eșuată");
      loadData();
    } catch (err) {
      showToast("Eroare la actualizarea disponibilității", "error");
    }
  }

  return (
    <ClientRoleGuard role="Manager" theme="dark" spinnerColor="border-green-500">
      <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-4xl font-black text-green-500 tracking-tight">MANAGER DASHBOARD</h1>
            <p className="text-slate-400">Monitorizare vânzări și administrare meniu</p>
          </div>
          <div className="flex items-center gap-6">
            <UserProfileMenu />
            <Button className="bg-green-600 hover:bg-green-500 font-bold" onClick={handleAddNew}>+ Adaugă Produs Nou</Button>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card className="bg-slate-900 border-slate-800"><CardHeader><CardTitle className="text-slate-400 text-sm uppercase">Încasări Zilnice</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-green-400">1,250.50 RON</p></CardContent></Card>
          <Card className="bg-slate-900 border-slate-800"><CardHeader><CardTitle className="text-slate-400 text-sm uppercase">Comenzi Totale</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-blue-400">24</p></CardContent></Card>
          <Card className="bg-slate-900 border-slate-800"><CardHeader><CardTitle className="text-slate-400 text-sm uppercase">Produse în Meniu</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-green-400">{menuItems.length}</p></CardContent></Card>
        </div>

        {loading && <div className="text-center py-12 text-slate-400 text-lg">Se încarcă meniul...</div>}

        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-xl p-6 text-center">
            <p className="text-red-400 text-lg mb-2">❌ {error}</p>
            <Button variant="outline" className="border-red-800 text-red-300 hover:bg-red-950" onClick={loadData}>Reîncearcă</Button>
          </div>
        )}

        {!loading && !error && menuItems.length === 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <p className="text-slate-500 text-lg mb-4">Meniul este gol.</p>
            <Button className="bg-green-600 hover:bg-green-500 font-bold" onClick={handleAddNew}>+ Adaugă Primul Produs</Button>
          </div>
        )}

        {!loading && !error && menuItems.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {menuItems.map((item) => (
              <Card key={item.id} className={`bg-slate-900 border-slate-800 hover:border-green-500/30 transition-all overflow-hidden ${!item.is_available ? "opacity-50" : ""}`}>
                <div className="h-44 bg-slate-800 flex items-center justify-center overflow-hidden">
                  {item.image_url ? <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" /> : <span className="text-7xl">{getEmoji(item.category)}</span>}
                </div>
                <CardContent className="p-4 pt-4 space-y-3">
                  <div className="flex justify-between items-start gap-2">
                    <h3 className="text-lg font-bold text-white leading-tight">{item.name}</h3>
                    <span className="text-green-400 font-bold whitespace-nowrap">{item.price.toFixed(2)} RON</span>
                  </div>
                  {item.description && <p className="text-slate-400 text-sm line-clamp-2">{item.description}</p>}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">{item.category}</span>
                    <button onClick={() => handleToggleAvailability(item)} className={`text-xs px-2 py-0.5 rounded-full font-medium transition-colors ${item.is_available ? "bg-green-900/50 text-green-300 hover:bg-green-900" : "bg-red-900/50 text-red-300 hover:bg-red-900"}`}>{item.is_available ? "Disponibil" : "Indisponibil"}</button>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <Button variant="outline" size="sm" className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white" onClick={() => handleEdit(item)}><Pencil size={14} className="mr-1.5" />Editează</Button>
                    <Button variant="outline" size="sm" className="border-red-900/50 text-red-400 hover:bg-red-950 hover:text-red-300" onClick={() => handleDelete(item.id)}><Trash2 size={14} /></Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Dialog open={isModalOpen} onOpenChange={(open) => { if (!open) { setIsModalOpen(false); resetForm(); } }}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="text-2xl font-bold text-green-400">{editingItem ? "Editează Produs" : "Adaugă Produs Nou"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div><label className="text-sm text-slate-400 mb-1.5 block">Nume Produs *</label><input type="text" value={formName} onChange={(e) => setFormName(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors" placeholder="Ex: Burger Wagyu" /></div>
              <div><label className="text-sm text-slate-400 mb-1.5 block">Descriere</label><textarea value={formDescription} onChange={(e) => setFormDescription(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors min-h-[80px] resize-y" placeholder="Descrierea produsului..." /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="text-sm text-slate-400 mb-1.5 block">Preț (RON) *</label><input type="number" step="0.01" min="0.01" value={formPrice} onChange={(e) => setFormPrice(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors" placeholder="0.00" /></div>
                <div><label className="text-sm text-slate-400 mb-1.5 block">Categorie *</label><select value={formCategoryId} onChange={(e) => setFormCategoryId(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-green-500 outline-none transition-colors"><option value="">Selectează...</option>{categories.map((cat) => (<option key={cat.id} value={cat.id}>{cat.name}</option>))}</select></div>
              </div>
              <div><label className="text-sm text-slate-400 mb-1.5 block">Imagine Produs</label><div className="flex gap-3 items-start"><div className="flex-1"><input type="file" ref={fileInputRef} accept="image/jpeg,image/png,image/webp,image/gif" onChange={handleFileChange} className="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-slate-800 file:text-green-400 file:font-medium hover:file:bg-slate-700 file:cursor-pointer file:transition-colors" />{uploadingImage && <p className="text-xs text-yellow-400 mt-1.5">Se încarcă și se optimizează imaginea...</p>}{compressionStats && <p className="text-xs text-green-400 mt-1.5">✓ Optimizat: {(compressionStats.original / 1024).toFixed(1)}KB → {(compressionStats.optimized / 1024).toFixed(1)}KB</p>}</div>{previewImage && <img src={previewImage} alt="Preview" className="w-16 h-16 rounded-lg object-cover border border-slate-700 shrink-0" />}</div></div>
              <div><label className="text-sm text-slate-400 mb-1.5 block">Ingrediente</label><input type="text" value={formIngredients} onChange={(e) => setFormIngredients(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors" placeholder="Ex: carne vită, cheddar, ceapă" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="text-sm text-slate-400 mb-1.5 block">Timp Preparare (min)</label><input type="number" min="0" value={formPrepTime} onChange={(e) => setFormPrepTime(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors" placeholder="15" /></div>
                <div><label className="text-sm text-slate-400 mb-1.5 block">Tag-uri Dietă</label><input type="text" value={formDietary} onChange={(e) => setFormDietary(e.target.value)} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-green-500 outline-none transition-colors" placeholder="Ex: vegetarian" /></div>
              </div>
              <div className="flex items-center gap-3"><span className="text-sm text-slate-400">Disponibil în meniu:</span><button type="button" onClick={() => setIsFormAvailable(!isFormAvailable)} className={`relative w-11 h-6 rounded-full transition-colors ${isFormAvailable ? "bg-green-600" : "bg-slate-600"}`}><span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${isFormAvailable ? "translate-x-5" : ""}`} /></button></div>
            </div>
            <DialogFooter>
              <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800" onClick={() => { setIsModalOpen(false); resetForm(); }}>Anulează</Button>
              <Button className="bg-green-600 hover:bg-green-500 font-bold" onClick={handleSave} disabled={saving}>{saving ? "Se salvează..." : editingItem ? "Salvează Modificări" : "Adaugă Produs"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {toast && <div className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 z-50 ${toast.type === "success" ? "bg-green-600" : "bg-red-600"} text-white font-medium`}>{toast.message}</div>}
      </div>
    </ClientRoleGuard>
  );
}
