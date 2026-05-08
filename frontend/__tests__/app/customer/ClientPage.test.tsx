import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CustomerPage from '@/app/customer/page'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: (key: string) => key === 'table_id' ? '5' : null
  }),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn()
  }),
  usePathname: () => ''
}))

// Mock components
vi.mock('@/components/ui/UserProfileMenu', () => ({
  default: () => <div>User Menu</div>
}))

describe('Customer Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock fetch
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/guest-login')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ access_token: 'fake_guest_token' })
        })
      }
      if (url.includes('/menu')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: 1, name: 'Pizza Margherita', price: 35, category: 'Pizza', is_available: true, description: 'Classic pizza' }
          ])
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    }) as any
  })

  it('renders customer menu correctly', async () => {
    render(<CustomerPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Pizza Margherita')).toBeInTheDocument()
      expect(screen.getByText(/35.00/)).toBeInTheDocument()
    })
  })

  it('can open item dialog and add to cart', async () => {
    render(<CustomerPage />)
    
    await waitFor(() => expect(screen.getByText('Pizza Margherita')).toBeInTheDocument())
    
    const commandButton = screen.getByRole('button', { name: /Comandă/i })
    fireEvent.click(commandButton)
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /🛒 Adaugă în coș/i })).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByRole('button', { name: /🛒 Adaugă în coș/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/a fost adăugat în coș!/i)).toBeInTheDocument()
    })
  })
})
