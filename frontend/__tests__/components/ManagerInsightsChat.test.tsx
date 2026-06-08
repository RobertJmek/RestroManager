import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ManagerInsightsChat } from '@/components/ManagerInsightsChat'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({ apiRequest: vi.fn() }))

// Răspuns minimal compatibil cu Response, fără a folosi `any`.
const okResponse = (data: unknown) =>
  ({ ok: true, json: () => Promise.resolve(data) }) as unknown as Response

describe('ManagerInsightsChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.apiRequest).mockResolvedValue(
      okResponse({
        response_text: 'Vânzările au fost bune.',
        insights: ['Top produs: Burger'],
        follow_up_question: null,
        session_id: 'sess-1',
        agent: 'fallback',
      }),
    )
  })

  it('shows the empty-state prompt and suggestion chips', () => {
    render(<ManagerInsightsChat startDate="2026-05-01" endDate="2026-05-07" />)
    expect(screen.getByText(/Întreabă-mă orice/i)).toBeInTheDocument()
    expect(screen.getByText('Care e cel mai vândut produs?')).toBeInTheDocument()
  })

  it('sends a question and renders the AI response with insights', async () => {
    render(<ManagerInsightsChat startDate="2026-05-01" endDate="2026-05-07" />)

    const field = screen.getByPlaceholderText(/Scrie o întrebare/i)
    fireEvent.change(field, { target: { value: 'Cum a fost luna?' } })
    fireEvent.submit(field.closest('form')!)

    await waitFor(() => {
      expect(screen.getByText('Vânzările au fost bune.')).toBeInTheDocument()
      expect(screen.getByText('Top produs: Burger')).toBeInTheDocument()
    })

    // Trimite mesajul + perioada selectată către backend.
    expect(api.apiRequest).toHaveBeenCalledWith(
      '/insights/chat',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"start_date":"2026-05-01"'),
      }),
    )
  })

  it('sends a suggestion chip when clicked', async () => {
    render(<ManagerInsightsChat startDate="2026-05-01" endDate="2026-05-07" />)
    fireEvent.click(screen.getByText('Care e cel mai vândut produs?'))
    await waitFor(() => {
      expect(screen.getByText('Vânzările au fost bune.')).toBeInTheDocument()
    })
  })
})
