# Plan: Chat-Based AI Recommendation Agent (DeepSeek V4 Flash)

Implement a single conversational AI agent that helps customers find dishes through natural chat. Uses **DeepSeek V4 Flash** with strict safety guards to only answer food/menu related questions.

---

## Scope: Recommendation Agent ONLY

- **NO Safety Agent**
- **NO KDS Optimizer**
- **ONLY Chat-Based Menu Recommendation**

## Why DeepSeek V4 Flash?

| Feature | Benefit |
|---------|---------|
| Speed | <500ms response time |
| Cost | ~$0.01 per 1K conversations (10x cheaper than competitors) |
| Context | 64K context window |
| API | OpenAI-compatible for easy integration |

---

## Safety Guard (CRITICAL)

The agent MUST refuse non-food questions with:
> "I'm your food assistant and can only help with menu recommendations and dining advice. Is there something from our menu you'd like to know about?"

**Allowed topics:**
- Menu items and descriptions
- Food recommendations
- Dietary preferences (vegan, gluten-free, allergies)
- Drink pairings
- Ingredients and allergens
- Restaurant services

**Blocked topics:**
- Politics, news, general knowledge
- Coding, homework help
- Medical diagnosis (beyond basic allergen info)
- Personal/career advice
- Any non-food topics

---

## Files to Create/Modify (7 files)

| File | Action | Purpose |
|------|--------|---------|
| `backend/requirements.txt` | Add `openai` | DeepSeek API client (OpenAI-compatible) |
| `backend/core/config.py` | Add `DEEPSEEK_API_KEY` | Configuration |
| `backend/core/ai.py` | Add `run_chat_recommendation_agent()` | Core agent logic |
| `backend/api/recommendations.py` | Create new file | Chat API endpoint |
| `backend/api/__init__.py` | Add router | Wire up endpoint |
| `frontend/components/AIChatWidget.tsx` | Create new file | Chat UI |
| `frontend/app/customer/page.tsx` | Add `<AIChatWidget />` | Integrate widget |

---

## Implementation

### 1. Dependencies

Add to `backend/requirements.txt`:
```
openai==1.54.0
```

### 2. Configuration

Add to `backend/core/config.py`:
```python
# AI Recommendation Agent (DeepSeek)
DEEPSEEK_API_KEY: str | None = None
DEEPSEEK_MODEL: str = "deepseek-v4-flash"
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
USE_AI_RECOMMENDATIONS: bool = True
```

Update `.env_example`:
```env
# DeepSeek API for AI Recommendations
# Get your API key at: https://platform.deepseek.com/
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 3. AI Module

Add to `backend/core/ai.py`:

```python
"""
AI Recommendation Agent - Chat-based dish recommendations
Uses DeepSeek V4 Flash with safety guards
"""

import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from core.config import settings

_deepseek_client = None
_chat_sessions: Dict[str, List[Dict]] = {}

def get_deepseek_client():
    """Initialize DeepSeek client lazily (OpenAI-compatible API)"""
    global _deepseek_client
    if _deepseek_client is None and settings.DEEPSEEK_API_KEY:
        _deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
    return _deepseek_client

async def run_chat_recommendation_agent(
    message: str,
    session_id: str,
    menu_items: List[Dict],
    past_orders: List = None
) -> Dict[str, Any]:
    """
    Chat-based AI agent that recommends dishes to customers.
    Uses DeepSeek V4 with strict safety guards.

    SAFETY: Only answers food/menu related questions.
    """
    if not settings.USE_AI_RECOMMENDATIONS or not settings.DEEPSEEK_API_KEY:
        return _fallback_chat_response(message, menu_items, session_id)

    # Build menu context
    menu_text = json.dumps([{
        "id": i["id"],
        "name": i["name"],
        "description": i.get("description", ""),
        "price": i.get("price"),
        "dietary_tags": i.get("dietary_tags", "")
    } for i in menu_items[:30]], indent=2)

    # System prompt with SAFETY GUARD
    system_prompt = f"""You are a restaurant AI assistant helping customers find dishes they'll love.

TODAY'S MENU:
{menu_text}

================================================================================
STRICT SAFETY GUARD - YOU MUST FOLLOW THESE RULES:
================================================================================

1. ONLY answer questions about:
   - Menu items and food descriptions
   - Dish recommendations based on preferences
   - Dietary advice (vegan, gluten-free, allergies)
   - Ingredients and allergens
   - Drink pairings with menu items
   - Restaurant services

2. If asked about ANYTHING ELSE (politics, coding, homework, general knowledge,
   medical diagnosis, personal advice, news, weather, etc.), you MUST respond
   EXACTLY with this message and NOTHING else:
   "I'm your food assistant and can only help with menu recommendations and dining advice. Is there something from our menu you'd like to know about?"

3. NEVER provide:
   - Medical advice beyond basic allergen information
   - Code or technical help
   - Opinions on non-food topics
   - Personal or career advice
   - General knowledge answers

4. Stay helpful but firmly within food/dining scope.

================================================================================
CONVERSATION STYLE:
================================================================================
- Be warm, conversational, and friendly (not robotic)
- Ask 1-2 clarifying questions before making recommendations
- When recommending, suggest 2-3 specific dishes with clear reasoning
- Include dish prices and brief descriptions
- Guide customers toward placing an order

Respond in this JSON format:
{{"response_text": "Your conversational reply", "suggested_dishes": [{{"item_id": 1, "name": "Dish Name", "reasoning": "Why this matches", "price": 15.99}}], "follow_up_question": "Ask something to continue the conversation or null"}}"""

    try:
        client = get_deepseek_client()
        if not client:
            return _fallback_chat_response(message, menu_items, session_id)

        # Call DeepSeek API (OpenAI-compatible)
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.4,
            max_tokens=800
        )

        # Try to parse JSON response, fallback if model doesn't return valid JSON
        try:
            response_text = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: treat as plain text response
            result = {
                "response_text": response.choices[0].message.content,
                "suggested_dishes": [],
                "follow_up_question": None
            }

        # Update chat history
        chat_history = _chat_sessions.get(session_id, [])
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": result.get("response_text", "")})
        _chat_sessions[session_id] = chat_history[-10:]  # Keep last 10 messages

        return {
            "response_text": result.get("response_text", ""),
            "suggested_dishes": result.get("suggested_dishes", []),
            "follow_up_question": result.get("follow_up_question"),
            "session_id": session_id,
            "agent": settings.DEEPSEEK_MODEL
        }

    except Exception as e:
        print(f"Recommendation Agent error: {e}")
        return _fallback_chat_response(message, menu_items, session_id)

def clear_chat_session(session_id: str):
    """Clear chat history for a session"""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]

def _fallback_chat_response(message: str, menu_items: List[Dict], session_id: str) -> Dict:
    """Fallback when AI unavailable"""
    keywords = message.lower().split()
    matched = []
    
    for item in menu_items[:5]:
        score = sum(1 for kw in keywords if kw in item.get("name", "").lower())
        if score > 0:
            matched.append({
                "item_id": item["id"], "name": item["name"],
                "reasoning": f"Matches your request", "price": item.get("price"),
                "confidence": 0.7
            })
    
    if not matched:
        matched = [{"item_id": item["id"], "name": item["name"],
                   "reasoning": "Popular choice", "price": item.get("price"), "confidence": 0.6}
                  for item in menu_items[:3]]
    
    return {
        "response_text": "Here are some dishes you might like:",
        "suggested_dishes": matched[:3],
        "session_id": session_id,
        "agent": "fallback"
    }

def clear_chat_session(session_id: str):
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
```

### 4. Recommendations API

Create `backend/api/recommendations.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel
from uuid import uuid4

from db.session import get_session
from models.menu_item import MenuItem
from api.auth import get_current_user_optional
from core.ai import run_chat_recommendation_agent, clear_chat_session

router = APIRouter(prefix="/recommendations")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ClearRequest(BaseModel):
    session_id: str

@router.post("/chat")
async def chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user_optional)
):
    """Chat with AI for dish recommendations"""
    session_id = request.session_id or str(uuid4())
    
    menu_items = session.exec(
        select(MenuItem).where(MenuItem.is_available == True)
    ).all()
    
    response = await run_chat_recommendation_agent(
        message=request.message,
        session_id=session_id,
        menu_items=[{
            "id": item.id, "name": item.name,
            "description": item.description,
            "price": item.price,
            "dietary_tags": item.dietary_tags
        } for item in menu_items]
    )
    
    return response

@router.post("/chat/clear")
async def clear(request: ClearRequest):
    """Clear chat session"""
    clear_chat_session(request.session_id)
    return {"status": "cleared"}
```

Update `backend/api/__init__.py`:
```python
from api.recommendations import router as recommendations_router

# Add to router assembly
routers.include_router(recommendations_router)
```

### 5. Frontend Chat Widget

Create `frontend/components/AIChatWidget.tsx`:

```typescript
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
  const token = typeof window !== 'undefined' ? localStorage.getItem("guest_token") : null;

  const startChat = async () => {
    setIsOpen(true);
    if (messages.length === 0) {
      await sendMessage("Hi! I'm looking for something to eat.");
    }
  };

  const sendMessage = async (msg: string) => {
    if (!msg.trim() || !token) return;
    
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
      
      if (!response.ok) throw new Error("Failed to get recommendation");
      
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
        className="fixed bottom-6 right-6 rounded-full shadow-lg bg-gradient-to-r from-violet-600 to-indigo-600"
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
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)} className="text-slate-400">
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
            onKeyPress={(e) => e.key === "Enter" && sendMessage(input)}
            className="bg-slate-800 border-slate-700 text-white"
          />
          <Button size="icon" onClick={() => sendMessage(input)} disabled={isLoading} className="bg-violet-600">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 6. Integrate in Customer Page

Update `frontend/app/customer/page.tsx`:

Add import:
```typescript
import { AIChatWidget } from "@/components/AIChatWidget";
```

Add the widget component inside `CustomerContent`, before the closing `</div>`:
```tsx
{/* AI Chat Widget - only show when authenticated */}
{guestToken && (
  <AIChatWidget 
    onAddToCart={(item) => {
      // Add to cart logic
      const newItem = {
        id: Math.random().toString(36).substr(2, 9),
        productId: item.id,
        name: item.name,
        price: item.price,
        quantity: 1,
        notes: ""
      };
      setCart(prev => [...prev, newItem]);
      showToast(`✅ ${item.name} added from AI recommendation!`);
    }}
  />
)}
```

---

## Testing

1. **Open customer page** → Click "Let AI recommend me something"
2. **Chat with AI** → Ask "I want something spicy"
3. **Verify** → AI asks clarifying questions, then suggests 2-3 dishes
4. **Test safety guard** → Ask "Who won the election?" → Should get redirect message
5. **Test fallback** → Works even if DeepSeek API unavailable

---

## Cost Estimate

~$0.01 per 1,000 conversations (DeepSeek V4 is 10x cheaper than competitors)
