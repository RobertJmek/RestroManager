import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ChefPage from '@/app/chef/ClientPage'
import * as api from '@/lib/api'

// Mock components
vi.mock('@/components/ClientRoleGuard', () => ({
  default: ({ children }: any) => <>{children}</>
}))
vi.mock('@/components/ui/UserProfileMenu', () => ({
  default: () => <div>User Menu</div>
}))

// Mock API
vi.mock('@/lib/api', () => ({
  getStoredUser: vi.fn(),
  apiRequest: vi.fn(),
}))

describe('Chef Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.getStoredUser as any).mockReturnValue({ id: 3, role: 'Chef', name: 'Chef Gordon' })
    
    // Default mock for fetch active-orders
    ;(api.apiRequest as any).mockImplementation((url: string) => {
      if (url === '/chef/active-orders') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            {
              id: 1,
              table_number: 10,
              items: [{ id: 101, name: 'Pizza', quantity: 2, status: 'pending' }],
              notes: '',
              ai_metadata: { urgency: 'NORMAL', cooking_strategy: 'Standard' }
            }
          ])
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  it('renders the chef dashboard and active orders', async () => {
    render(<ChefPage />)
    expect(screen.getByText('KITCHEN DISPLAY SYSTEM')).toBeInTheDocument()
    
    await waitFor(() => {
      expect(screen.getByText('MASA #10')).toBeInTheDocument()
      expect(screen.getByText('Pizza')).toBeInTheDocument()
    })
  })

  it('marks an order as ready', async () => {
    render(<ChefPage />)
    
    await waitFor(() => expect(screen.getByText('MASA #10')).toBeInTheDocument())
    
    const markReadyBtn = screen.getByText('MARCHEAZĂ GATA')
    
    ;(api.apiRequest as any).mockImplementation((url: string) => {
      if (url.includes('/ready-for-pickup')) {
        return Promise.resolve({ ok: true })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
    
    fireEvent.click(markReadyBtn)
    
    await waitFor(() => {
      expect(screen.queryByText('MASA #10')).not.toBeInTheDocument()
    })
  })
})
