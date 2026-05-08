import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ManagerPage from '@/app/manager/ClientPage'
import * as api from '@/lib/api'

// Mock components
vi.mock('@/components/ClientRoleGuard', () => ({
  default: ({ children }: any) => <>{children}</>
}))
vi.mock('@/components/ui/UserProfileMenu', () => ({
  default: () => <div>User Menu</div>
}))

// Mock recharts
vi.mock('recharts', async () => {
  return {
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    BarChart: ({ children }: any) => <div>{children}</div>,
    Bar: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />
  }
})

// Mock API
vi.mock('@/lib/api', () => ({
  getStoredUser: vi.fn(),
  apiRequest: vi.fn(),
}))

describe('Manager Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.getStoredUser as any).mockReturnValue({ id: 1, role: 'Manager', name: 'Admin' })
    
    // Default mocks
    ;(api.apiRequest as any).mockImplementation((url: string) => {
      if (url === '/menu') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: 1, name: 'Burger', price: 20, category: 'Food', is_available: true }
          ])
        })
      }
      if (url === '/categories') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: 1, name: 'Food' }])
        })
      }
      if (url === '/manager/stats') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ total_revenue: 500, total_orders: 10, menu_items_count: 1 })
        })
      }
      if (url.includes('/reports/range')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
             total_revenue: 500, 
             total_orders: 10, 
             average_order_value: 50, 
             revenue_by_day: [],
             top_items: []
          })
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  it('renders stats and menu items correctly', async () => {
    render(<ManagerPage />)
    expect(screen.getByText('MANAGER DASHBOARD')).toBeInTheDocument()
    
    await waitFor(() => {
      expect(screen.getByText('500.00 RON')).toBeInTheDocument()
      expect(screen.getByText('Burger')).toBeInTheDocument()
    })
  })

  it('can open add product modal', async () => {
    render(<ManagerPage />)
    await waitFor(() => expect(screen.getByText('Burger')).toBeInTheDocument())
    
    fireEvent.click(screen.getByText('+ Adaugă Produs Nou'))
    
    expect(screen.getByText('Nume Produs *')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Adaugă Produs' })).toBeInTheDocument()
  })

  it('can switch tabs', async () => {
    render(<ManagerPage />)
    
    fireEvent.click(screen.getByText('Categorii'))
    await waitFor(() => {
      expect(screen.getByText('Gestiune Categorii')).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByText('Rapoarte'))
    await waitFor(() => {
      // First heading should be the Reports section
      const headers = screen.getAllByText('Rapoarte')
      expect(headers.length).toBeGreaterThan(0)
    })
  })
})
