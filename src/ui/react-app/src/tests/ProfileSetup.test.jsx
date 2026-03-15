import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProfileSetup from '../pages/ProfileSetup'

// Mock the API call so tests never hit the network
vi.mock('../api/client', () => ({
  saveConfig: vi.fn(),
}))
import { saveConfig } from '../api/client'

const onComplete = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
})

// ── Step 0: Welcome ───────────────────────────────────────────────────────────

describe('Step 0 — Welcome', () => {
  it('renders the welcome screen by default', () => {
    render(<ProfileSetup onComplete={onComplete} />)
    expect(screen.getByText(/hey — looks like you're new here/i)).toBeInTheDocument()
  })

  it('advances to step 1 when "Let\'s get started" is clicked', async () => {
    const user = userEvent.setup()
    render(<ProfileSetup onComplete={onComplete} />)
    await user.click(screen.getByRole('button', { name: /let's get started/i }))
    expect(screen.getByText(/your identity/i)).toBeInTheDocument()
  })
})

// ── Step 1: Identity ──────────────────────────────────────────────────────────

describe('Step 1 — Identity', () => {
  async function goToStep1() {
    const user = userEvent.setup()
    render(<ProfileSetup onComplete={onComplete} />)
    await user.click(screen.getByRole('button', { name: /let's get started/i }))
    return user
  }

  it('shows validation errors when continuing with empty fields', async () => {
    const user = await goToStep1()
    await user.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByText(/full name is required/i)).toBeInTheDocument()
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/phone number is required/i)).toBeInTheDocument()
  })

  it('shows an error for an invalid email', async () => {
    const user = await goToStep1()
    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/phone/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument()
  })

  it('advances to step 2 when all required fields are valid', async () => {
    const user = await goToStep1()
    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'ada@lovelace.dev')
    await user.type(screen.getByLabelText(/phone/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByText(/online presence/i)).toBeInTheDocument()
  })

  it('goes back to step 0 when Back is clicked', async () => {
    const user = await goToStep1()
    await user.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByText(/hey — looks like you're new here/i)).toBeInTheDocument()
  })
})

// ── Step 2: Links ─────────────────────────────────────────────────────────────

describe('Step 2 — Links', () => {
  async function goToStep2() {
    const user = userEvent.setup()
    render(<ProfileSetup onComplete={onComplete} />)
    await user.click(screen.getByRole('button', { name: /let's get started/i }))
    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'ada@lovelace.dev')
    await user.type(screen.getByLabelText(/phone/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    return user
  }

  it('calls saveConfig with correct values on save', async () => {
    saveConfig.mockResolvedValue({})
    const user = await goToStep2()
    await user.type(screen.getByLabelText(/github/i), 'ada-lovelace')
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    expect(saveConfig).toHaveBeenCalledWith({
      name:     'Ada Lovelace',
      email:    'ada@lovelace.dev',
      phone:    '5558675309',
      github:   'ada-lovelace',
      linkedin: undefined,
    })
  })

  it('advances to step 3 after a successful save', async () => {
    saveConfig.mockResolvedValue({})
    const user = await goToStep2()
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    await waitFor(() =>
      expect(screen.getByText(/you're all set/i)).toBeInTheDocument()
    )
  })

  it('shows an error banner when saveConfig fails', async () => {
    saveConfig.mockRejectedValue(new Error('Network error'))
    const user = await goToStep2()
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    await waitFor(() =>
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    )
  })

  it('disables the save button while saving', async () => {
    saveConfig.mockImplementation(() => new Promise(() => {})) // never resolves
    const user = await goToStep2()
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
  })

  it('goes back to step 1 when Back is clicked', async () => {
    const user = await goToStep2()
    await user.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByText(/your identity/i)).toBeInTheDocument()
  })

  it("sends undefined for empty optional fields", async () => {
    saveConfig.mockResolvedValue({})
    const user = await goToStep2()
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    expect(saveConfig).toHaveBeenCalledWith(
      expect.objectContaining({
        github: undefined,
        linkedin: undefined,
      })
    )
  })

  
})

// ── Step 3: Done ──────────────────────────────────────────────────────────────

describe('Step 3 — Done', () => {
  async function goToStep3() {
    saveConfig.mockResolvedValue({})
    const user = userEvent.setup()
    render(<ProfileSetup onComplete={onComplete} />)
    await user.click(screen.getByRole('button', { name: /let's get started/i }))
    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'ada@lovelace.dev')
    await user.type(screen.getByLabelText(/phone/i), '5558675309')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await user.click(screen.getByRole('button', { name: /save profile/i }))
    await waitFor(() => screen.getByText(/you're all set/i))
    return user
  }

  it('shows the user\'s first name in the completion message', async () => {
    await goToStep3()
    expect(screen.getByText(/you're all set, ada/i)).toBeInTheDocument()
  })

  it('calls onComplete when "Go to Projects" is clicked', async () => {
    const user = await goToStep3()
    await user.click(screen.getByRole('button', { name: /go to projects/i }))
    expect(onComplete).toHaveBeenCalledOnce()
  })
})
