import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import Help from '../Help'

// ── Rendering ─────────────────────────────────────────────────────────────────

describe('Initial render', () => {
  it('renders the Help & Info heading', () => {
    render(<Help />)
    expect(screen.getByRole('heading', { name: /help & info/i })).toBeInTheDocument()
  })

  it('renders all seven section toggle buttons', () => {
    render(<Help />)
    const sections = [
      /overview/i,
      /uploading a project/i,
      /running an analysis/i,
      /understanding results/i,
      /badges/i,
      /troubleshooting/i,
      /privacy & security/i,
    ]
    for (const name of sections) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
  })

  it('renders no section content by default (all collapsed)', () => {
    render(<Help />)
    expect(screen.queryByText(/project analyzer evaluates/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/compress your project/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/select a project/i)).not.toBeInTheDocument()
  })
})

// ── Section toggling ──────────────────────────────────────────────────────────

describe('Section toggling', () => {
  it('expands Overview on click and shows content', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.getByText(/project analyzer evaluates/i)).toBeInTheDocument()
  })

  it('collapses Overview on second click', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.getByText(/project analyzer evaluates/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.queryByText(/project analyzer evaluates/i)).not.toBeInTheDocument()
  })

  it('expands Uploading a Project and shows ZIP instructions', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /uploading a project/i }))
    expect(screen.getByText(/compress your project folder/i)).toBeInTheDocument()
  })

  it('expands Running an Analysis and shows numbered steps', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /running an analysis/i }))
    expect(screen.getByText(/select a project from the project list/i)).toBeInTheDocument()
    expect(screen.getByText(/click analyze project/i)).toBeInTheDocument()
  })

  it('expands Understanding Results and shows report sections', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /understanding results/i }))
    expect(screen.getByText(/project summary/i)).toBeInTheDocument()
    expect(screen.getByText(/skill indicators/i)).toBeInTheDocument()
  })

  it('expands Badges and shows badge description', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /badges/i }))
    expect(screen.getByText(/recognized technical achievements/i)).toBeInTheDocument()
  })

  it('expands Troubleshooting and shows upload failure tips', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /troubleshooting/i }))
    expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
    expect(screen.getByText(/zip file is not corrupted/i)).toBeInTheDocument()
  })

  it('expands Privacy & Security and shows privacy message', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /privacy & security/i }))
    expect(screen.getByText(/analyzed locally/i)).toBeInTheDocument()
  })
})

// ── Arrow indicator ───────────────────────────────────────────────────────────

describe('Arrow indicator', () => {
  it('shows ▼ when section is collapsed', () => {
    render(<Help />)
    const btn = screen.getByRole('button', { name: /overview/i })
    expect(btn).toHaveTextContent('▼')
  })

  it('shows ▲ when section is expanded', async () => {
    const user = userEvent.setup()
    render(<Help />)
    const btn = screen.getByRole('button', { name: /overview/i })
    await user.click(btn)
    expect(btn).toHaveTextContent('▲')
  })

  it('reverts to ▼ after collapsing', async () => {
    const user = userEvent.setup()
    render(<Help />)
    const btn = screen.getByRole('button', { name: /overview/i })
    await user.click(btn)
    await user.click(btn)
    expect(btn).toHaveTextContent('▼')
  })
})

// ── Independent section state ─────────────────────────────────────────────────

describe('Independent section state', () => {
  it('expanding one section does not expand others', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.queryByText(/compress your project folder/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/select a project from the project list/i)).not.toBeInTheDocument()
  })

  it('multiple sections can be open simultaneously', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    await user.click(screen.getByRole('button', { name: /badges/i }))
    expect(screen.getByText(/project analyzer evaluates/i)).toBeInTheDocument()
    expect(screen.getByText(/recognized technical achievements/i)).toBeInTheDocument()
  })

  it('collapsing one section leaves others unaffected', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    await user.click(screen.getByRole('button', { name: /badges/i }))
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.queryByText(/project analyzer evaluates/i)).not.toBeInTheDocument()
    expect(screen.getByText(/recognized technical achievements/i)).toBeInTheDocument()
  })
})

// ── Content spot-checks ───────────────────────────────────────────────────────

describe('Content spot-checks', () => {
  it('Overview lists github commit contributions', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /overview/i }))
    expect(screen.getByText(/github commit contributions/i)).toBeInTheDocument()
  })

  it('Uploading section mentions Git repository import option', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /uploading a project/i }))
    expect(screen.getByText(/import a git repository/i)).toBeInTheDocument()
  })

  it('Troubleshooting mentions files must be compressed, not just renamed', async () => {
    const user = userEvent.setup()
    render(<Help />)
    await user.click(screen.getByRole('button', { name: /troubleshooting/i }))
    expect(screen.getByText(/not just renamed to \.zip/i)).toBeInTheDocument()
  })
})
