'use client';

import React from 'react';
import { Button } from "@/components/ui/button";
import { CheckCircle2, ArrowLeft } from "lucide-react";
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

function SuccessContent() {
  const searchParams = useSearchParams();
  const tableId = searchParams.get('table_id') || '1';

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-100 font-sans">
      <div className="max-w-md w-full bg-slate-900 border border-emerald-500/30 rounded-3xl p-8 shadow-2xl flex flex-col items-center text-center relative overflow-hidden">
        
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-emerald-400 to-teal-500" />
        
        <div className="w-24 h-24 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6">
          <CheckCircle2 className="w-16 h-16 text-emerald-500" />
        </div>
        
        <h1 className="text-3xl font-extrabold text-white mb-2">Comandă Trimisă!</h1>
        <p className="text-slate-400 mb-8 leading-relaxed">
          Comanda ta a fost trimisă direct pe ecranul KDS al bucătarului și va fi adusă la masă în cel mai scurt timp.
        </p>
        
        <div className="bg-slate-950 rounded-xl p-4 w-full mb-8 border border-slate-800">
          <p className="text-sm font-medium text-slate-300">Stare comandă: <span className="text-emerald-400 font-bold ml-1">În pregătire 👨‍🍳</span></p>
        </div>

        <Link href={`/customer?table_id=${tableId}`} className="w-full">
          <Button className="w-full bg-slate-800 hover:bg-slate-700 text-white rounded-xl py-6 font-semibold flex items-center justify-center gap-2">
            <ArrowLeft size={18} /> Înapoi la Meniu
          </Button>
        </Link>
      </div>
    </div>
  );
}

export default function SuccessPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Se încarcă...</div>}>
      <SuccessContent />
    </React.Suspense>
  );
}