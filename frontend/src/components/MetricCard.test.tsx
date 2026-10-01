import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CalendarDays } from 'lucide-react'
import { MetricCard } from './MetricCard'

describe('MetricCard', () => {
  it('shows a live metric label, value and context', () => {
    render(<MetricCard label="Appointments today" value={12} note="Confirmed and pending" icon={CalendarDays} tone="mint" />)
    expect(screen.getByText('Appointments today')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Confirmed and pending')).toBeInTheDocument()
  })
})
