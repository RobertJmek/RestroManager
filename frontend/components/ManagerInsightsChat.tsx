"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sparkles, Send } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface InsightMessage {
  role: "user" | "ai";
  content: string;
  insights?: string[];
}

interface ManagerInsightsChatProps {
  startDate: string;
  endDate: string;
}

const SUGGESTIONS = [
  "Cum au fost vânzările în această perioadă?",
  "Care e cel mai vândut produs?",
  "Ce ar trebui să promovez?",
];

export function ManagerInsightsChat({ startDate, endDate }: ManagerInsightsChatProps) {
  const [messages, setMessages] = useState<InsightMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Notă: când se schimbă perioada (startDate/endDate), părintele remontează
  // componenta printr-un `key` nou, deci starea (sesiune + mesaje) se resetează
  // singură — context curat de raport, fără efect care apelează setState.

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading]);

  const sendMessage = async (msg: string) => {
    if (!msg.trim() || isLoading) return;
    setInput("");
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: msg }]);

    try {
      const res = await apiRequest("/insights/chat", {
        method: "POST",
        body: JSON.stringify({
          message: msg,
          session_id: sessionId,
          start_date: startDate,
          end_date: endDate,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: data.response_text, insights: data.insights },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Nu am putut obține un răspuns. Încearcă din nou." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800 mt-10">
      <CardHeader>
        <CardTitle className="text-slate-400 text-sm uppercase flex items-center gap-2">
          <Sparkles size={16} className="text-green-400" /> Asistent AI Analiză
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="max-h-80 overflow-y-auto space-y-3 mb-4">
          {messages.length === 0 && (
            <p className="text-slate-500 text-sm">
              Întreabă-mă orice despre datele de vânzări din perioada selectată.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
              <div
                className={`inline-block px-3 py-2 rounded-lg text-sm max-w-[90%] ${
                  m.role === "user" ? "bg-green-600 text-white" : "bg-slate-800 text-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.insights && m.insights.length > 0 && (
                  <ul className="mt-2 list-disc list-inside text-slate-300 text-xs space-y-0.5">
                    {m.insights.map((ins, j) => (
                      <li key={j}>{ins}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}
          {isLoading && <p className="text-slate-500 text-sm">Se analizează...</p>}
        </div>

        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="px-3 py-1 rounded-full text-xs bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Scrie o întrebare despre vânzări..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:border-green-500 outline-none text-sm"
          />
          <Button type="submit" disabled={isLoading} className="bg-green-600 hover:bg-green-500">
            <Send size={16} />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
