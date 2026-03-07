import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Settings from '../Settings'

vi.mock('../api/client', () => ({
  getConfig:         vi.fn(),
  saveConfig:        vi.fn(),
  setPrivacyConsent: vi.fn(),
  getPrivacyConsent: vi.fn(),
  clearProjects:     vi.fn(),
}))

import { getConfig, saveConfig, setPrivacyConsent, getPrivacyConsent, clearProjects } from '../api/client'

beforeEach(() => {
  vi.clearAllMocks()
  getConfig.mockResolvedValue({})
  getPrivacyConsent.mockResolvedValue(false)
})

// ── Rendering ─────────────────────────────────────────────────────────────────

describe('Initial render', () => {
  it('shows the Profile tab by default', async () => {
    render(<Settings />)
    await waitFor(() =>
      expect(screen.getByText(/these details will appear on your resume/i)).toBeInTheDocument()
    )
  })

  it('renders all three nav buttons', async () => {
    render(<Settings />)
    expect(screen.getByRole('button', { name: /profile/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /privacy/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /data/i })).toBeInTheDocument()
  })
})

// ── Profile tab ───────────────────────────────────────────────────────────────

describe('Profile tab', () => {
  it('loads and pre-fills saved config values', async () => {
    getConfig.mockResolvedValue({
      name: 'Ada Lovelace', email: 'ada@lovelace.dev', phone: '5558675309',
      github: 'ada-lv', linkedin: 'ada-lovelace',
    })
    render(<Settings />)
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/ada lovelace/i)).toHaveValue('Ada Lovelace')
    )
    expect(screen.getByPlaceholderText(/ada@lovelace\.dev/i)).toHaveValue('ada@lovelace.dev')
    expect(screen.getByPlaceholderText(/555/i)).toHaveValue('5558675309')
    const [githubInput, linkedinInput] = screen.getAllByPlaceholderText(/ada-lovelace/)
    expect(githubInput).toHaveValue('ada-lv')
    expect(linkedinInput).toHaveValue('ada-lovelace')
  })

  it('shows validation errors when saving with empty required fields', async () => {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /save changes/i }))
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    expect(screen.getByText(/full name is required/i)).toBeInTheDocument()
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/phone is required/i)).toBeInTheDocument()
  })

  it('shows an error for an invalid email', async () => {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /save changes/i }))
    await user.type(screen.getByPlaceholderText(/ada lovelace/i), 'Ada')
    await user.type(screen.getByPlaceholderText(/ada@lovelace\.dev/i), 'not-an-email')
    await user.type(screen.getByPlaceholderText(/555/i), '1234567890')
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument()
  })

  it('calls saveConfig with correct values', async () => {
    saveConfig.mockResolvedValue({})
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByPlaceholderText(/ada lovelace/i))
    await user.type(screen.getByPlaceholderText(/ada lovelace/i), 'Ada Lovelace')
    await user.type(screen.getByPlaceholderText(/ada@lovelace\.dev/i), 'ada@lovelace.dev')
    await user.type(screen.getByPlaceholderText(/555/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() =>
      expect(saveConfig).toHaveBeenCalledWith({
        name: 'Ada Lovelace', email: 'ada@lovelace.dev', phone: '5558675309',
        github: undefined, linkedin: undefined,
      })
    )
  })

  it('shows "Saved." after a successful save', async () => {
    saveConfig.mockResolvedValue({})
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByPlaceholderText(/ada lovelace/i))
    await user.type(screen.getByPlaceholderText(/ada lovelace/i), 'Ada Lovelace')
    await user.type(screen.getByPlaceholderText(/ada@lovelace\.dev/i), 'ada@lovelace.dev')
    await user.type(screen.getByPlaceholderText(/555/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(screen.getByText(/saved\./i)).toBeInTheDocument())
  })

  it('shows an error message when saveConfig fails', async () => {
    saveConfig.mockRejectedValue(new Error('Network error'))
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByPlaceholderText(/ada lovelace/i))
    await user.type(screen.getByPlaceholderText(/ada lovelace/i), 'Ada Lovelace')
    await user.type(screen.getByPlaceholderText(/ada@lovelace\.dev/i), 'ada@lovelace.dev')
    await user.type(screen.getByPlaceholderText(/555/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(screen.getByText(/network error/i)).toBeInTheDocument())
  })

  it('disables save button while saving', async () => {
    saveConfig.mockImplementation(() => new Promise(() => {})) // never resolves
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByPlaceholderText(/ada lovelace/i))
    await user.type(screen.getByPlaceholderText(/ada lovelace/i), 'Ada Lovelace')
    await user.type(screen.getByPlaceholderText(/ada@lovelace\.dev/i), 'ada@lovelace.dev')
    await user.type(screen.getByPlaceholderText(/555/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /save changes/i }))
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
  })
})

// ── Privacy tab ───────────────────────────────────────────────────────────────

describe('Privacy tab', () => {
  async function goToPrivacy() {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /privacy/i }))
    await user.click(screen.getByRole('button', { name: /privacy/i }))
    return user
  }

  it('shows consent not granted by default', async () => {
    await goToPrivacy()
    expect(screen.getByText(/consent not granted/i)).toBeInTheDocument()
  })

  it('shows consent granted when getPrivacyConsent returns true', async () => {
    getPrivacyConsent.mockResolvedValue(true)
    await goToPrivacy()
    await waitFor(() =>
      expect(screen.getByText(/consent granted/i)).toBeInTheDocument()
    )
  })

  it('calls setPrivacyConsent with true when granting consent', async () => {
    setPrivacyConsent.mockResolvedValue({})
    const user = await goToPrivacy()
    await user.click(screen.getByRole('button', { name: /grant consent/i }))
    expect(setPrivacyConsent).toHaveBeenCalledWith(true)
  })

  it('calls setPrivacyConsent with false when revoking consent', async () => {
    getPrivacyConsent.mockResolvedValue(true)
    setPrivacyConsent.mockResolvedValue({})
    const user = await goToPrivacy()
    await waitFor(() => screen.getByRole('button', { name: /revoke consent/i }))
    await user.click(screen.getByRole('button', { name: /revoke consent/i }))
    expect(setPrivacyConsent).toHaveBeenCalledWith(false)
  })

  it('toggles status text after granting consent', async () => {
    setPrivacyConsent.mockResolvedValue({})
    const user = await goToPrivacy()
    await user.click(screen.getByRole('button', { name: /grant consent/i }))
    await waitFor(() =>
      expect(screen.getByText(/consent granted/i)).toBeInTheDocument()
    )
  })

  it('disables the button while consent is updating', async () => {
    setPrivacyConsent.mockImplementation(() => new Promise(() => {}))
    const user = await goToPrivacy()
    await user.click(screen.getByRole('button', { name: /grant consent/i }))
    expect(screen.getByRole('button', { name: /updating/i })).toBeDisabled()
  })
})

// ── Data tab ──────────────────────────────────────────────────────────────────

describe('Data tab', () => {
  async function goToData() {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /^data$/i }))
    await user.click(screen.getByRole('button', { name: /^data$/i }))
    return user
  }

  it('shows the clear all projects button', async () => {
    await goToData()
    expect(screen.getByRole('button', { name: /clear all projects/i })).toBeInTheDocument()
  })

  it('shows a confirmation prompt on first click', async () => {
    const user = await goToData()
    await user.click(screen.getByRole('button', { name: /clear all projects/i }))
    expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /yes, delete everything/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('cancel resets back to the initial state', async () => {
    const user = await goToData()
    await user.click(screen.getByRole('button', { name: /clear all projects/i }))
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.getByRole('button', { name: /clear all projects/i })).toBeInTheDocument()
    expect(screen.queryByText(/this cannot be undone/i)).not.toBeInTheDocument()
  })

  it('calls clearProjects on confirmation', async () => {
    clearProjects.mockResolvedValue({})
    const user = await goToData()
    await user.click(screen.getByRole('button', { name: /clear all projects/i }))
    await user.click(screen.getByRole('button', { name: /yes, delete everything/i }))
    expect(clearProjects).toHaveBeenCalledOnce()
  })

  it('shows success message after clearing', async () => {
    clearProjects.mockResolvedValue({})
    const user = await goToData()
    await user.click(screen.getByRole('button', { name: /clear all projects/i }))
    await user.click(screen.getByRole('button', { name: /yes, delete everything/i }))
    await waitFor(() =>
      expect(screen.getByText(/all projects cleared/i)).toBeInTheDocument()
    )
  })
})

// ── Tab navigation ────────────────────────────────────────────────────────────

describe('Tab navigation', () => {
  it('switches to Privacy tab', async () => {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /privacy/i }))
    await user.click(screen.getByRole('button', { name: /privacy/i }))
    expect(screen.getByText(/consent is required/i)).toBeInTheDocument()
  })

  it('switches to Data tab', async () => {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /^data$/i }))
    await user.click(screen.getByRole('button', { name: /^data$/i }))
    expect(screen.getByText(/irreversible actions/i)).toBeInTheDocument()
  })

  it('switches back to Profile tab from Privacy', async () => {
    const user = userEvent.setup()
    render(<Settings />)
    await waitFor(() => screen.getByRole('button', { name: /privacy/i }))
    await user.click(screen.getByRole('button', { name: /privacy/i }))
    await user.click(screen.getByRole('button', { name: /profile/i }))
    expect(screen.getByText(/these details will appear/i)).toBeInTheDocument()
  })
})

// ── Consent persistence ───────────────────────────────────────────────────────

describe('Consent persistence', () => {
  it('loads consent state from getPrivacyConsent on mount', async () => {
    getPrivacyConsent.mockResolvedValue(true)
    const user = userEvent.setup()
    render(<Settings />)
    await user.click(screen.getByRole('button', { name: /privacy/i }))
    await waitFor(() =>
      expect(screen.getByText(/consent granted/i)).toBeInTheDocument()
    )
  })

  it('consent state survives switching tabs and returning', async () => {
    getPrivacyConsent.mockResolvedValue(true)
    setPrivacyConsent.mockResolvedValue({})
    const user = userEvent.setup()
    render(<Settings />)
    await user.click(screen.getByRole('button', { name: /privacy/i }))
    await waitFor(() => screen.getByRole('button', { name: /revoke consent/i }))

    // switch away and come back
    await user.click(screen.getByRole('button', { name: /profile/i }))
    await user.click(screen.getByRole('button', { name: /privacy/i }))

    expect(screen.getByText(/consent granted/i)).toBeInTheDocument()
  })
})
