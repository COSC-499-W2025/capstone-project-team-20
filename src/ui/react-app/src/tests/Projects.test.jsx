import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Projects from '../pages/Projects'

vi.mock('../api/client', () => ({
  listProjects:           vi.fn(),
  getProject:             vi.fn(),
  getPrivacyConsent:      vi.fn(),
  uploadProjectZip:       vi.fn(),
  uploadProjectFromPath:  vi.fn(),
  clearProjects:          vi.fn(),
  deleteProject:          vi.fn(),
  resolveContributorsBatch: vi.fn(),
}))

import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects,
  deleteProject,
  resolveContributorsBatch,
} from '../api/client'

// ── Shared fixtures ───────────────────────────────────────────────────────────

const EMPTY_LIST = { projects: [], current_projects: [], previous_projects: [] }

const PROJECT_LIST = {
  projects:          [{ id: 1, name: 'my-app' }, { id: 2, name: 'old-app' }],
  current_projects:  [{ id: 1, name: 'my-app' }],
  previous_projects: [{ id: 2, name: 'old-app' }],
}

const PROJECT_DETAIL = { project: { id: 1, name: 'my-app', languages: ['Python'] } }

const PENDING_DUPLICATES = [
  {
    project_id:   1,
    project_name: 'my-app',
    duplicate_groups: [
      {
        display_name:        'Dale S',
        suggested_canonical: 'dale@example.com',
        candidates:          ['dale@example.com', 'dale@old.com'],
      },
    ],
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  // Safe default for every test: empty list loads cleanly
  listProjects.mockResolvedValue(EMPTY_LIST)
  getProject.mockResolvedValue(PROJECT_DETAIL)
  getPrivacyConsent.mockResolvedValue(true)
  deleteProject.mockResolvedValue({})
  resolveContributorsBatch.mockResolvedValue({})
  clearProjects.mockResolvedValue({})
})

// ── Initial load ──────────────────────────────────────────────────────────────

describe('Initial load', () => {
  it('calls listProjects on mount', async () => {
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
  })

  it('renders current and previous project lists', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    render(<Projects />)
    await waitFor(() => {
      expect(screen.getByText(/my-app \(#1\)/i)).toBeInTheDocument()
      expect(screen.getByText(/old-app \(#2\)/i)).toBeInTheDocument()
    })
  })

  it('shows empty state messages when there are no projects', async () => {
    render(<Projects />)
    await waitFor(() => {
      expect(screen.getByText(/no projects in the current import batch yet/i)).toBeInTheDocument()
      expect(screen.getByText(/no previous projects yet/i)).toBeInTheDocument()
    })
  })

  it('shows an error if listProjects fails', async () => {
    listProjects.mockRejectedValue(new Error('DB offline'))
    render(<Projects />)
    await waitFor(() =>
      expect(screen.getByText(/db offline/i)).toBeInTheDocument()
    )
  })
})

// ── Refresh / Clear ───────────────────────────────────────────────────────────

describe('Refresh and Clear', () => {
  it('re-fetches projects when Refresh is clicked', async () => {
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.click(screen.getByRole('button', { name: /refresh projects/i }))
    await waitFor(() => expect(listProjects).toHaveBeenCalledTimes(2))
  })

  it('calls clearProjects and reloads when Clear Database is clicked', async () => {
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.click(screen.getByRole('button', { name: /clear database/i }))
    await waitFor(() => {
      expect(clearProjects).toHaveBeenCalledOnce()
      expect(listProjects).toHaveBeenCalledTimes(2)
    })
  })

  it('shows an error if clearProjects fails', async () => {
    clearProjects.mockRejectedValue(new Error('Clear failed'))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.click(screen.getByRole('button', { name: /clear database/i }))
    await waitFor(() =>
      expect(screen.getByText(/clear failed/i)).toBeInTheDocument()
    )
  })
})

// ── Project selection ─────────────────────────────────────────────────────────

describe('Project selection', () => {
  it('shows project details when a project is clicked', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText(/my-app \(#1\)/i))
    await user.click(screen.getByText(/my-app \(#1\)/i))
    await waitFor(() =>
      expect(screen.getByText(/"name": "my-app"/i)).toBeInTheDocument()
    )
  })

  it('shows an error if getProject fails', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    getProject.mockRejectedValue(new Error('Not found'))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText(/my-app \(#1\)/i))
    await user.click(screen.getByText(/my-app \(#1\)/i))
    await waitFor(() =>
      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    )
  })
})

// ── Path upload ───────────────────────────────────────────────────────────────

describe('Path upload', () => {
  it('the load button is disabled when the path field is empty', async () => {
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    expect(screen.getByRole('button', { name: /load from path/i })).toBeDisabled()
  })

  it('blocks upload when consent is not given', async () => {
    getPrivacyConsent.mockResolvedValue(false)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() =>
      expect(screen.getByText(/you must grant consent/i)).toBeInTheDocument()
    )
    expect(uploadProjectFromPath).not.toHaveBeenCalled()
  })

  it('shows the status message while uploading', async () => {
    uploadProjectFromPath.mockImplementation(() => new Promise(() => {})) // never resolves
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    expect(screen.getByText(/uploading and analyzing/i)).toBeInTheDocument()
  })

  it('shows success status after a clean upload', async () => {
    uploadProjectFromPath.mockResolvedValue({
      status: 'complete',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: [],
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() =>
      expect(screen.getByText(/done! loaded 1 project/i)).toBeInTheDocument()
    )
  })

  it('opens the merge modal when duplicates are detected', async () => {
    uploadProjectFromPath.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() =>
      expect(screen.getByText(/resolve duplicate contributors/i)).toBeInTheDocument()
    )
  })

  it('shows an error if the upload fails', async () => {
    uploadProjectFromPath.mockRejectedValue(new Error('Path upload failed'))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() =>
      expect(screen.getByText(/path upload failed/i)).toBeInTheDocument()
    )
  })

  it('clears the path input after a successful upload', async () => {
    uploadProjectFromPath.mockResolvedValue({
      status: 'complete',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: [],
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    const input = screen.getByPlaceholderText(/testresources\/sample\.zip/i)
    await user.type(input, 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() => expect(input.value).toBe(''))
  })
})

// ── Merge modal ───────────────────────────────────────────────────────────────

describe('Merge modal', () => {
  async function openMergeModal() {
    uploadProjectFromPath.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() => screen.getByText(/resolve duplicate contributors/i))
    return user
  }

  it('renders the project name and candidate emails', async () => {
    await openMergeModal()
    expect(screen.getByText('my-app')).toBeInTheDocument()
    expect(screen.getAllByText('dale@example.com').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dale@old.com').length).toBeGreaterThan(0)
  })

  it('calls resolveContributorsBatch and closes modal on Apply', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /apply merges/i }))
    await waitFor(() => {
      expect(resolveContributorsBatch).toHaveBeenCalledOnce()
      expect(screen.queryByText(/resolve duplicate contributors/i)).not.toBeInTheDocument()
    })
  })

  it('shows an error if resolveContributorsBatch fails', async () => {
    resolveContributorsBatch.mockRejectedValue(new Error('Merge failed'))
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /apply merges/i }))
    await waitFor(() =>
      expect(screen.getByText(/merge failed/i)).toBeInTheDocument()
    )
  })

  it('shows upload status after merges are applied', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /apply merges/i }))
    await waitFor(() =>
      expect(screen.getByText(/contributor merges applied/i)).toBeInTheDocument()
    )
  })
})

// ── Cancel analysis flow ──────────────────────────────────────────────────────

describe('Cancel analysis', () => {
  async function openMergeModal() {
    uploadProjectFromPath.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.type(screen.getByPlaceholderText(/testresources\/sample\.zip/i), 'some/path.zip')
    await user.click(screen.getByRole('button', { name: /load from path/i }))
    await waitFor(() => screen.getByText(/resolve duplicate contributors/i))
    return user
  }

  it('shows the confirmation screen when "Cancel Analysis" is clicked', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    expect(screen.getByText(/cancel analysis\?/i)).toBeInTheDocument()
    expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument()
  })

  it('returns to the merge screen when "Go back" is clicked', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    await user.click(screen.getByRole('button', { name: /go back/i }))
    expect(screen.getByText(/resolve duplicate contributors/i)).toBeInTheDocument()
  })

  it('calls deleteProject for each pending project on confirm', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    await user.click(screen.getByRole('button', { name: /yes, cancel analysis/i }))
    await waitFor(() =>
      expect(deleteProject).toHaveBeenCalledWith(1)
    )
  })

  it('closes the modal after confirming cancel', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    await user.click(screen.getByRole('button', { name: /yes, cancel analysis/i }))
    await waitFor(() =>
      expect(screen.queryByText(/cancel analysis\?/i)).not.toBeInTheDocument()
    )
  })

  it('shows an error if deleteProject fails but still closes the modal', async () => {
    deleteProject.mockRejectedValue(new Error('Delete failed'))
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    await user.click(screen.getByRole('button', { name: /yes, cancel analysis/i }))
    await waitFor(() => {
      expect(screen.getByText(/delete failed/i)).toBeInTheDocument()
      expect(screen.queryByText(/cancel analysis\?/i)).not.toBeInTheDocument()
    })
  })

  it('shows the correct project count in the confirmation message', async () => {
    // Single project → "project" (not "2 projects")
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    expect(screen.getByText(/this will delete the project that were just uploaded/i)).toBeInTheDocument()
  })
})

// ── Quick load buttons ────────────────────────────────────────────────────────

describe('Quick load buttons', () => {
  it('populates the path input when a quick-load button is clicked', async () => {
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    await user.click(screen.getAllByRole('button', { name: /use/i })[0])
    expect(screen.getByPlaceholderText(/testresources\/sample\.zip/i).value)
      .toBe('testResources/testMultiFileAndRepos.zip')
  })
})
