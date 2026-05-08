import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { describe, it, expect } from 'vitest'

describe('Card Component', () => {
  it('renders card with title and content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>My Card Title</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Card Content Here</p>
        </CardContent>
      </Card>
    )

    expect(screen.getByText('My Card Title')).toBeInTheDocument()
    expect(screen.getByText('Card Content Here')).toBeInTheDocument()
  })
})
