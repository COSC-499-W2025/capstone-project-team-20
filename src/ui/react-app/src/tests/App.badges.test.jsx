import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

vi.mock('../api/client', () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  listSkills: vi.fn(),
  getBadgeProgress: vi.fn(),
  getYearlyWrapped: vi.fn(),
  getConfig: vi.fn(),
  getPrivacyConsent: vi.fn(),
  uploadProjectZip: vi.fn(),
  uploadProjectFromPath: vi.fn(),
  clearProjects: vi.fn(),
}))

import {
  listProjects,
  listSkills,
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
  listSkills.mockResolvedValue({
    skills: [{ name: 'React', project_count: 2 }],
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
  it('renders heatmap tiles with completion intensity and improved descriptions', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /badges/i })).toBeInTheDocument()
    )

    await user.click(screen.getByRole('button', { name: /badges/i }))

    expect(await screen.findByRole('heading', { name: /badge completion heatmap/i })).toBeInTheDocument()
    expect(await screen.findByText(/consistent effort over time, showing long-term ownership and discipline/i)).toBeInTheDocument()

    const polyglotLabel = await screen.findByText('Polyglot')
    const polyglotTile = polyglotLabel.closest('article')
    expect(polyglotTile).toHaveClass('badge-heatmap-tile--warm')

    const unlockedState = await screen.findByText('Unlocked')
    const unlockedTile = unlockedState.closest('article')
    expect(unlockedTile).toHaveClass('badge-heatmap-tile--hot')
  })
})