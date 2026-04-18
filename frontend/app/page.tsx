import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-24">
      <h1 className="text-4xl font-bold mb-8 text-slate-900">RestroManager Hub</h1>
      <p className="text-lg text-slate-600 mb-12 text-center max-w-lg">
        Bine ai venit in sistemul de gestiune Vibe Coding. Selecteaza aplicatia in care vrei sa intri:
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl">
        <Link href="/customer" className="w-full">
          <Button variant="default" className="w-full h-24 text-xl">👨‍💻 Customer App</Button>
        </Link>
        <Link href="/waiter" className="w-full">
          <Button variant="secondary" className="w-full h-24 text-xl">🏃 Waiter App</Button>
        </Link>
        <Link href="/chef" className="w-full">
          <Button variant="destructive" className="w-full h-24 text-xl">👨‍🍳 Chef KDS</Button>
        </Link>
        <Link href="/manager" className="w-full">
          <Button variant="outline" className="w-full h-24 text-xl">👔 Manager Dashboard</Button>
        </Link>
      </div>
    </main>
  );
}
