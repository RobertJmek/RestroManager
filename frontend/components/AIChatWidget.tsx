"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, Send, Sparkles } from "lucide-react";

interface ChatMessage {
  role: "user" | "ai";
  content: string;
  suggestedDishes?: Array<{
    item_id: number;
    name: string;
    reasoning: string;
    price: number;
  }>;
}

interface AIChatWidgetProps {
  onAddToCart: (item: { id: number; name: string; price: number }) => void;
}

export function AIChatWidget({ onAddToCart }: AIChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  const getToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem("guest_token") || localStorage.getItem("token");
    }
    return null;
  };

  const startChat = async () => {
    setIsOpen(true);
    if (messages.length === 0) {
      await sendMessage("Hi! I'm looking for something to eat.");
    }
  };

  const sendMessage = async (msg: string) => {
    const token = getToken();
    if (!msg.trim() || !token) return;

    // Clear input and show user message immediately
    setInput("");
    setIsLoading(true);
    setMessages(prev => [...prev, { role: "user", content: msg }]);

    try {
      const response = await fetch(`${API_URL}/recommendations/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: msg, session_id: sessionId })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setSessionId(data.session_id);

      setMessages(prev => [...prev, {
        role: "ai",
        content: data.response_text,
        suggestedDishes: data.suggested_dishes
      }]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        role: "ai",
        content: "Sorry, I'm having trouble connecting. Please try again!"
      }]);
    } finally {
      setIsLoading(false);
      setInput("");
    }
  };

  const handleAddToCart = (dish: { item_id: number; name: string; price: number }) => {
    onAddToCart({ id: dish.item_id, name: dish.name, price: dish.price });
  };

  if (!isOpen) {
    return (
      <Button
        onClick={startChat}
        className="fixed top-6 right-6 rounded-full shadow-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 z-40"
        size="lg"
      >
        <Sparkles className="mr-2 h-4 w-4" />
        Let AI recommend me something
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-6 right-6 w-96 shadow-xl z-50 bg-slate-900 border-slate-700">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm flex items-center text-white">
          <Sparkles className="mr-2 h-4 w-4 text-yellow-400" />
          AI Food Assistant
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white hover:bg-slate-800">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-80 overflow-y-auto space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-lg p-3 ${
                msg.role === "user"
                  ? "bg-violet-600 text-white"
                  : "bg-slate-800 text-slate-100"
              }`}>
                <p className="text-sm">{msg.content}</p>

                {msg.suggestedDishes && msg.suggestedDishes.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {msg.suggestedDishes.map(dish => (
                      <div key={dish.item_id} className="bg-slate-700 rounded p-2">
                        <div className="flex justify-between items-start">
                          <span className="font-medium text-sm text-white">{dish.name}</span>
                          <span className="text-sm text-violet-300">{dish.price.toFixed(2)} RON</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{dish.reasoning}</p>
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 w-full text-xs border-violet-500 text-violet-300 hover:bg-violet-600 hover:text-white"
                          onClick={() => handleAddToCart(dish)}
                        >
                          Add to Cart
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 rounded-lg p-3">
                <span className="text-sm text-slate-400">AI is thinking...</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell me what you're craving..."
            onKeyDown={(e) => {
              // Guard against IME composition (e.g., Korean/Chinese/Japanese input)
              const nativeEvent = e.nativeEvent as KeyboardEvent;
              if (e.key === "Enter" && !(nativeEvent as any).isComposing) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
          />
          <Button size="icon" onClick={() => sendMessage(input)} disabled={isLoading} className="bg-violet-600 hover:bg-violet-500">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
