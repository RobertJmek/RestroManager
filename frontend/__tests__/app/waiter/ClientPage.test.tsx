import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import WaiterPage from '@/app/waiter/ClientPage'
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

describe('Waiter Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.getStoredUser as any).mockReturnValue({ id: 2, role: 'Waiter', name: 'John Doe' })
    
    // Default mocks for fetch
    ;(api.apiRequest as any).mockImplementation((url: string) => {
      if (url === '/waiter/tables') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: 1, number: 5, capacity: 4, status: 'free', waiter_id: null }
          ])
        })
      }
      if (url === '/menu') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([])
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  it('renders the waiter dashboard header and tables', async () => {
    render(<WaiterPage />)
    expect(screen.getByText('WAITER DASHBOARD')).toBeInTheDocument()
    
    // Wait for fetch to complete
    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // Table number 5
      expect(screen.getByText('Liberă')).toBeInTheDocument()
    })
  })

  it('shows claim button for occupied tables without a waiter', async () => {
    ;(api.apiRequest as any).mockImplementation((url: string) => {
      if (url === '/waiter/tables') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: 1, number: 5, capacity: 4, status: 'occupied', waiter_id: null }
          ])
        })
      }
      if (url.includes('/active-order')) {
        return Promise.resolve({
           ok: false,
           json: () => Promise.resolve(null)
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })
    
    render(<WaiterPage />)
    
    // Wait for the "Needs pickup" tag
    await waitFor(() => expect(screen.getByText('Necesită Preluare!')).toBeInTheDocument())
    
    // Click the table
    const tableDiv = screen.getByText('5').closest('div')
    fireEvent.click(tableDiv!)
    
    await waitFor(() => {
      expect(screen.getByText('Masă #5')).toBeInTheDocument()
      expect(screen.getByText('PREIA MASA')).toBeInTheDocument()
    })
  })
})
