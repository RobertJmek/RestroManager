import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#0f172a] p-8 text-white">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-orange-400 to-amber-200">RestroManager Hub</h1>
        <p className="text-lg text-slate-400 max-w-lg mx-auto">
          Sistem integrat pentru restaurante moderne. Alege platforma corespunzătoare rolului tău.
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
        <Link href="/customer?table_id=1" className="w-full group">
          <Button variant="default" className="w-full h-32 text-xl bg-orange-600 hover:bg-orange-500 rounded-3xl flex flex-col gap-2 transition-all group-hover:scale-[1.02]">
            <span className="text-3xl">📱</span>
            <span>Meniu Digital (Masa 1)</span>
          </Button>
        </Link>
        <Link href="/login" className="w-full group">
          <Button variant="secondary" className="w-full h-32 text-xl bg-slate-800 hover:bg-slate-700 text-white border-slate-700 rounded-3xl flex flex-col gap-2 transition-all group-hover:scale-[1.02]">
            <span className="text-3xl">🔐</span>
            <span>Login Personal</span>
          </Button>
        </Link>
      </div>

      <div className="mt-12 text-slate-500 text-sm flex gap-6">
        <Link href="/waiter" className="hover:text-slate-300">Quick Waiter</Link>
        <Link href="/chef" className="hover:text-slate-300">Quick Chef</Link>
        <Link href="/manager" className="hover:text-slate-300">Quick Manager</Link>
      </div>
    </main>
  );
}
