"use client";

import { useState, useEffect, useRef } from "react";
import { User, LogOut, Settings, ChevronDown, Save, Loader2 } from "lucide-react";
import { logout, apiRequest, getStoredUser } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

interface UserProfileMenuProps {
  className?: string;
}

export default function UserProfileMenu({ className = "" }: UserProfileMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [user, setUser] = useState<{ role: string | null; name: string | null }>({ role: null, name: null });
  const menuRef = useRef<HTMLDivElement>(null);

  // State-uri pentru Modalul de Setări Cont
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [formData, setFormData] = useState({ name: "", phone: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState({ type: "", text: "" });

  useEffect(() => {
    const { role, name } = getStoredUser();
    
    if (!role || role === "Guest") {
      setUser({ role: null, name: null });
    } else {
      setUser({ role, name });
    }

    const handleClickOutside = (event: MouseEvent) => {
      // Evităm închiderea dropdown-ului dacă dăm click în interiorul modalului
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // --- Logica de Deschidere & Fetch ---
  const openSettings = async () => {
    setIsOpen(false); // Închidem dropdown-ul
    setIsSettingsOpen(true);
    setIsLoading(true);
    setSaveMessage({ type: "", text: "" });

    try {
      const res = await apiRequest("/users/me");
      if (res.ok) {
        const data = await res.json();
        setFormData({ name: data.name || "", phone: data.phone || "" });
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Logica de Salvare ---
  const saveSettings = async () => {
    setIsLoading(true);
    setSaveMessage({ type: "", text: "" });

    try {
      const res = await apiRequest("/users/me", {
        method: "PUT",
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        const data = await res.json();
        // Update live în UI (L2 fix: name comes from JWT, refreshed on next login)
        setUser(prev => ({ ...prev, name: data.name }));
        setSaveMessage({ type: "success", text: "Datele au fost salvate cu succes!" });
        
        // Închidem fereastra după o secundă
        setTimeout(() => setIsSettingsOpen(false), 1200);
      } else {
        const err = await res.json();
        setSaveMessage({ type: "error", text: err.detail || "Eroare la salvare. Încearcă din nou." });
      }
    } catch (error) {
      setSaveMessage({ type: "error", text: "A apărut o problemă de conexiune." });
    } finally {
      setIsLoading(false);
    }
  };

  if (!user.role) return null;

  return (
    <>
      <div className={`relative ${className}`} ref={menuRef}>
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="group flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 p-1.5 pr-3 rounded-full transition-all duration-300 backdrop-blur-md shadow-lg"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-pink-500 flex items-center justify-center text-white shadow-inner group-hover:scale-105 transition-transform">
            <User size={16} />
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-bold text-white leading-tight truncate max-w-[100px]">{user.name || user.role}</p>
            <p className="text-[9px] text-white/60 font-mono uppercase tracking-tighter">{user.role}</p>
          </div>
          <ChevronDown size={14} className={`text-white/40 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-56 bg-[#1a1c2e]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden origin-top-right animate-in fade-in zoom-in-95 duration-200 z-[100]">
            <div className="p-4 border-b border-white/5 bg-white/5">
              <p className="text-sm font-bold text-white truncate">{user.name || "Utilizator"}</p>
              <div className="flex items-center gap-1.5 mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                  <p className="text-[10px] text-white/40 uppercase font-mono tracking-widest">{user.role} Active</p>
              </div>
            </div>
            
            <div className="p-1.5 space-y-0.5">
              {/* Buton Setări */}
              <button 
                onClick={openSettings}
                className="w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 rounded-xl transition-all group"
              >
                <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center group-hover:bg-white/10">
                  <Settings size={14} />
                </div>
                <span>Setări Cont</span>
              </button>
              
              {/* Buton Logout */}
              <button 
                onClick={() => logout()}
                className="w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition-all group"
              >
                <div className="w-7 h-7 rounded-lg bg-red-500/5 flex items-center justify-center group-hover:bg-red-500/10">
                  <LogOut size={14} />
                </div>
                <span>Ieșire Sistem</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* --- FEREASTRA MODALĂ (DIALOG) --- */}
      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">Setări Cont</DialogTitle>
            <DialogDescription className="text-slate-400">
              Aici îți poți actualiza informațiile personale.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-5 py-4">
            <div className="flex flex-col gap-2">
              <label htmlFor="name" className="text-sm font-semibold text-slate-300">Nume Complet</label>
              <input 
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500 transition-shadow disabled:cursor-not-allowed disabled:opacity-50" 
                placeholder="Ex: Ion Popescu"
                disabled={isLoading}
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <label htmlFor="phone" className="text-sm font-semibold text-slate-300">Număr de Telefon</label>
              <input 
                id="phone"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500 transition-shadow disabled:cursor-not-allowed disabled:opacity-50" 
                placeholder="Ex: +40712345678"
                disabled={isLoading}
              />
            </div>

            {/* Mesaj Succes/Eroare */}
            {saveMessage.text && (
              <div className={`p-3 rounded-lg text-sm font-medium animate-in fade-in ${saveMessage.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                {saveMessage.text}
              </div>
            )}
          </div>

          <DialogFooter className="sm:justify-end gap-2">
            <button 
              onClick={() => setIsSettingsOpen(false)}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              disabled={isLoading}
            >
              Anulează
            </button>
            <button 
              onClick={saveSettings}
              disabled={isLoading || !formData.name || !formData.phone}
              className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-all shadow-lg shadow-violet-600/20 disabled:opacity-50 disabled:shadow-none"
            >
              {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isLoading ? 'Se salvează...' : 'Salvează'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
