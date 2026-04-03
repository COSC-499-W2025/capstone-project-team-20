import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

vi.mock('../api/client', () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  listSkillsUsage: vi.fn(),
  getBadgeProgress: vi.fn(),
  getYearlyWrapped: vi.fn(),
  getConfig: vi.fn(),
  getPrivacyConsent: vi.fn(),
  uploadProjectZip: vi.fn(),
  uploadProjectFromPath: vi.fn(),
  clearProjects: vi.fn(),
  setPrivacyConsent: vi.fn(),
  saveConfig: vi.fn(),
  getReportBundles: vi.fn(),
  getResumeData: vi.fn(),
  getPortfolioData: vi.fn(),
}))

import {
  listProjects,
  listSkillsUsage,
  getBadgeProgress,
  getYearlyWrapped,
  getConfig,
  getPrivacyConsent,
} from '../api/client'

beforeEach(() => {
  vi.clearAllMocks()

  getConfig.mockResolvedValue({
    name: 'Ada Lovelace',
    email: 'ada@lovelace.dev',
    phone: '5558675309',
  })

  listProjects.mockResolvedValue({
    projects: [],
    current_projects: [],
    previous_projects: [],
  })

  getPrivacyConsent.mockResolvedValue(true)
  listSkillsUsage.mockResolvedValue({
    skills: [{ name: 'React', project_count: 2, projects: ['Alpha', 'Big Repo'] }],
  })

  getBadgeProgress.mockResolvedValue({
    badges: [
      {
        badge_id: 'polyglot',
        label: 'Polyglot',
        earned: false,
        progress: 0.65,
        metric: 'language_count',
        current: 2,
        target: 3,
        project: { name: 'Alpha' },
      },
      {
        badge_id: 'team_effort',
        label: 'Team Effort',
        earned: false,
        progress: 0,
        metric: 'contributors',
        current: 0,
        target: 3,
        project: { name: 'Alpha' },
      },
      {
        badge_id: 'gigantana',
        label: 'Gigantana',
        earned: true,
        progress: 1,
        metric: 'project_size_mb',
        current: 1400,
        target: 1024,
        project: { name: 'Big Repo' },
      },
    ],
  })

  getYearlyWrapped.mockResolvedValue({
    wrapped: [
      {
        year: 2025,
        vibe_title: 'Momentum Year',
        projects_count: 1,
        total_loc: 1000,
        total_files: 40,
        avg_test_file_ratio: 0.2,
        highlights: [],
        milestones: [
          {
            badge_id: 'gigantana',
            project: 'Big Repo',
            achieved_on: '2025-07-21',
          },
        ],
      },
    ],
  })
})

describe('App badges heatmap', () => {
  it('copies content for LinkedIn without opening popup windows', async () => {
    const user = userEvent.setup()
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const clipboardTextSpy = vi.fn().mockResolvedValue(undefined)
    const clipboardImageSpy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: clipboardTextSpy,
        write: clipboardImageSpy,
      },
      configurable: true,
    })
    Object.defineProperty(window, 'ClipboardItem', {
      value: class ClipboardItem {
        constructor(data) {
          this.data = data
        }
      },
      configurable: true,
    })
    Object.defineProperty(navigator, 'canShare', {
      value: vi.fn().mockReturnValue(false),
      configurable: true,
    })

    render(<App />)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /badges/i })).toBeInTheDocument()
    )
    await user.click(screen.getByRole('button', { name: /badges/i }))

    const gigButton = await screen.findByRole('button', {
      name: /open gigantana badge details/i,
    })
    await user.click(gigButton)
    await user.click(await screen.findByRole('button', { name: /share badge card image \(any platform\)/i }))

    expect(openSpy).not.toHaveBeenCalled()
    expect(clipboardImageSpy).toHaveBeenCalledTimes(1)
    await user.click(await screen.findByRole('button', { name: /copy badge for linkedin/i }))
    expect(openSpy).not.toHaveBeenCalled()
    expect(clipboardImageSpy).toHaveBeenCalledTimes(2)

    await user.click(screen.getByRole('button', { name: '✕' }))
    await user.click(await screen.findByRole('button', { name: /get 2025 stats/i }))
    await user.click(await screen.findByRole('button', { name: /share wrapped image \(any platform\)/i }))
    expect(clipboardTextSpy).toHaveBeenCalledTimes(3)
    await user.click(await screen.findByRole('button', { name: /copy wrapped for linkedin/i }))
    await waitFor(() => {
      expect(openSpy).not.toHaveBeenCalled()
      expect(clipboardImageSpy).toHaveBeenCalledTimes(4)
      expect(clipboardTextSpy).not.toHaveBeenCalled()
    })
  })

  it('shows heatmap first and opens badge detail modal on tile click', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /badges/i })).toBeInTheDocument()
    )

    await user.click(screen.getByRole('button', { name: /badges/i }))

    expect(await screen.findByRole('heading', { name: /(all badges|badge completion heatmap)/i })).toBeInTheDocument()

    const polyglotTileButton = await screen.findByRole('button', {
      name: /open polyglot badge details/i,
    })
    await user.click(polyglotTileButton)

    const detailDialog = await screen.findByRole('dialog', { name: /polyglot badge details/i })
    expect(detailDialog).toBeInTheDocument()
    expect(within(detailDialog).getByRole('heading', { name: 'Polyglot' })).toBeInTheDocument()
    expect(within(detailDialog).getByText(/how to earn:/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '✕' }))
    expect(screen.queryByRole('heading', { name: 'Polyglot' })).not.toBeInTheDocument()
  })

  it('only shows started badges in progress list', async () => {
    const user = userEvent.setup()
    const { container } = render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /badges/i })).toBeInTheDocument()
    )

    await user.click(screen.getByRole('button', { name: /badges/i }))

    expect(await screen.findByRole('heading', { name: /(all badges|badge completion heatmap)/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /badge progress tracker/i })).toBeInTheDocument()
    const inProgressList = container.querySelector('.in-progress-list')
    expect(inProgressList).toBeInTheDocument()
    expect(inProgressList?.textContent).toContain('Polyglot')
    expect(inProgressList?.textContent).toContain('65%')
    expect(inProgressList?.textContent).not.toContain('Team Effort')

  })
  
it('expands a skill tile to show projects where that skill is used', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /badges/i })).toBeInTheDocument()
    )

    await user.click(screen.getByRole('button', { name: /badges/i }))

    const reactSkillButton = await screen.findByRole('button', { name: /react/i })
    await user.click(reactSkillButton)

    expect(await screen.findByText(/used in:/i)).toBeInTheDocument()
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Big Repo')).toBeInTheDocument()
  })
})