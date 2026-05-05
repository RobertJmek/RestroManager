# RestroManager Frontend - Claude Instructions

See [AGENTS.md](AGENTS.md) for Next.js 16+ specific guidance.
See [../AGENTS.md](../AGENTS.md) for full project architecture, conventions, and development setup.

## Focus Areas for Frontend Development

1. **Component building**: Use shadcn/ui components + Tailwind CSS 4
2. **API integration**: Use `apiRequest()` helper from `lib/api.ts` (handles JWT auth)
3. **Role-based views**: Customer, Waiter, Chef, Manager each have their own page in `app/`
4. **Real-time updates**: WebSocket connections managed by backend; listen for events in client
5. **Type safety**: Maintain strict TypeScript; add interfaces for all data structures
6. **Git workflow**: Each feature in its own branch (`feat/feature-name`); minimum 5 commits required
