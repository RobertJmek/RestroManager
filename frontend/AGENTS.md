<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

---

# RestroManager Frontend - Next.js 16+ Specific Guidance

**See the root [../AGENTS.md](../AGENTS.md) for full project context, architecture, and development setup.**

## 🎯 Frontend Quick Facts

- **Next.js 16.2.4** with **App Router** (not Pages router)
- **React 19.2.4** — Latest stable release
- **Tailwind CSS 4** — Latest major version with PostCSS 4 support
- **shadcn/ui** — Component library pre-configured with `button`, `card`, `dialog`
- **TypeScript** — Strict mode enabled

## 🗂️ File Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout wrapping all pages
│   ├── page.tsx            # Home page (/)
│   ├── globals.css         # Global Tailwind styles
│   ├── customer/
│   │   └── page.tsx        # Customer catalog + cart
│   ├── waiter/
│   │   └── page.tsx        # Waiter dashboard
│   ├── chef/
│   │   └── page.tsx        # Chef KDS
│   ├── manager/
│   │   └── page.tsx        # Manager dashboard
│   └── login/
│       └── page.tsx        # Login page
├── components/
│   └── ui/                 # shadcn/ui components (button, card, dialog)
├── lib/
│   ├── api.ts              # Centralized HTTP layer with JWT auth
│   └── utils.ts            # Helper functions
├── package.json
├── tsconfig.json           # TypeScript strict mode
├── tailwind.config.ts      # Tailwind CSS configuration
├── eslint.config.mjs       # ESLint setup
└── AGENTS.md               # This file
```

## 🔑 Key Patterns

### API Requests with Auth
Always use `apiRequest()` from `lib/api.ts`. It handles:
- JWT token from localStorage
- Authorization header injection
- Auto-logout on 401 (token expired)

```typescript
import { apiRequest } from "@/lib/api";

const response = await apiRequest("/menu");
const data = response.ok ? await response.json() : null;
```

### Component Examples
```typescript
// Use shadcn/ui components
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function MenuItem() {
  return (
    <Card>
      <CardContent>
        <h3 className="font-bold">Pizza Margherita</h3>
        <Button onClick={() => addToCart(item)}>Add to Cart</Button>
      </CardContent>
    </Card>
  );
}
```

### Styling
- Use **Tailwind CSS utility classes** (e.g., `className="flex gap-4 p-6"`)
- Import shadcn/ui components from `@/components/ui/*`
- Avoid inline `<style>` tags
- Use `globals.css` for global overrides only

## ⚡ Common Tasks

| Task | Command |
|------|---------|
| **Start dev server** | `npm run dev` (auto-reloads on file changes) |
| **Build for production** | `npm run build && npm start` |
| **Check TypeScript errors** | `npx tsc --noEmit` |
| **Run linter** | `npm run lint` |
| **Add shadcn/ui component** | `npx shadcn@latest add [component-name]` |

## ⚠️ Gotchas

1. **App Router async components**: Pages and layouts can be async (`async function Page()`)
2. **No `useLayoutEffect` on server components**: Only in client components (`"use client"`)
3. **Tailwind CSS 4 PostCSS changes**: Don't use `@apply` excessively; use utility classes directly
4. **JWT storage**: Stored in `localStorage`; validate on every API call
5. **API calls in Server Components**: Can be made directly (no CORS issues); client components use `apiRequest()`
6. **Environment variables**: Use `.env.local` for local overrides (already in `.gitignore`)

## 🔄 Integration with Backend

- Backend API runs on `http://localhost:8000`
- All REST endpoints prefixed with `/api/` (e.g., `/api/menu`, `/api/orders`)
- WebSocket endpoints (no `/api/` prefix): `/ws/chef`, `/ws/waiter`
- See backend `main.py` for CORS configuration

## 📖 See Also

- Root [../AGENTS.md](../AGENTS.md) — Full project architecture and conventions
- [../README.md](../README.md) — Product vision and user stories
- [../dev1_action_plan.md](../dev1_action_plan.md) — Development roadmap
