import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Projects from '../pages/Projects'

vi.mock('../api/client', () => ({
  listProjects:             vi.fn(),
  getProject:               vi.fn(),
  getPrivacyConsent:        vi.fn(),
  uploadProjectZip:         vi.fn(),
  deleteProject:            vi.fn(),
  resolveContributorsBatch: vi.fn(),
  setIdentity:              vi.fn(),
  uploadThumbnail:          vi.fn(),
  thumbnailUrl:             vi.fn((path) => `http://localhost:8000/thumbnails/${path}`),
}))

import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  deleteProject,
  resolveContributorsBatch,
  setIdentity,
} from '../api/client'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EMPTY_LIST = { projects: [], current_projects: [], previous_projects: [] }

const PROJECT_LIST = {
  projects:          [{ id: 1, name: 'my-app' }, { id: 2, name: 'old-app' }],
  current_projects:  [{ id: 1, name: 'my-app' }],
  previous_projects: [{ id: 2, name: 'old-app' }],
}

const PROJECT_DETAIL = {
  project: {
    id: 1, name: 'my-app',
    languages: ['Python'], language_share: { Python: 100 },
    frameworks: ['FastAPI'], skills_used: [],
    bullets: ['Built REST API'], summary: 'A cool project',
    resume_score: 7.5, author_count: 1,
    collaboration_status: 'individual',
    has_dockerfile: false, has_database: false,
    has_frontend: false, has_backend: true,
    has_test_files: false, has_readme: true,
    total_loc: 1200, num_files: 40, size_kb: 80,
    date_created: '2024-01-01T00:00:00', last_modified: '2024-06-01T00:00:00',
    thumbnail: null,
  },
}

const PENDING_DUPLICATES = [
  {
    project_id:   1,
    project_name: 'my-app',
    repo_path:    '/tmp/my-app',
    duplicate_groups: [
      {
        display_name:        'Dale S',
        suggested_canonical: 'dale@example.com',
        candidates:          ['dale@example.com', 'dale@old.com'],
      },
    ],
  },
]

const PENDING_IDENTITY = [
  {
    project_id:   1,
    project_name: 'my-app',
    candidates: [
      { email: 'alice@example.com', name: 'Alice' },
      { email: 'bob@example.com',   name: 'Bob'   },
    ],
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  listProjects.mockResolvedValue(EMPTY_LIST)
  getProject.mockResolvedValue(PROJECT_DETAIL)
  getPrivacyConsent.mockResolvedValue(true)
  deleteProject.mockResolvedValue(undefined)
  resolveContributorsBatch.mockResolvedValue({})
  setIdentity.mockResolvedValue({})
})

// ── Initial load ──────────────────────────────────────────────────────────────

describe('Initial load', () => {
  it('calls listProjects on mount', async () => {
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
  })

  it('renders current and previous project groups when projects exist', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    render(<Projects />)
    await waitFor(() => {
      expect(screen.getByText('my-app')).toBeInTheDocument()
      expect(screen.getByText('old-app')).toBeInTheDocument()
      expect(screen.getByText(/current batch/i)).toBeInTheDocument()
      expect(screen.getByText(/previous/i)).toBeInTheDocument()
    })
  })

  it('shows the upload zone when there are no projects', async () => {
    render(<Projects />)
    await waitFor(() =>
      expect(screen.getByText(/upload a zip of your project to get started/i)).toBeInTheDocument()
    )
  })

  it('shows an error if listProjects fails', async () => {
    listProjects.mockRejectedValue(new Error('DB offline'))
    render(<Projects />)
    await waitFor(() =>
      expect(screen.getByText(/db offline/i)).toBeInTheDocument()
    )
  })
})

// ── Project selection ─────────────────────────────────────────────────────────

describe('Project selection', () => {
  it('loads and displays project detail when a project is clicked', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByText('my-app')[0])
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(1)
      expect(screen.getByText('A cool project')).toBeInTheDocument()
      expect(screen.getByText('Built REST API')).toBeInTheDocument()
    })
  })

  it('clicking the same project again deselects it', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByText('my-app')[0])
    await waitFor(() => screen.getByText('A cool project'))
    await user.click(screen.getAllByText('my-app')[0])
    await waitFor(() =>
      expect(screen.queryByText('A cool project')).not.toBeInTheDocument()
    )
  })

  it('shows an error if getProject fails', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    getProject.mockRejectedValue(new Error('Not found'))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByText('my-app')[0])
    await waitFor(() =>
      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    )
  })
})

// ── ZIP upload ────────────────────────────────────────────────────────────────

describe('ZIP upload', () => {
  it('blocks upload and shows error when consent is not given', async () => {
    getPrivacyConsent.mockResolvedValue(false)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())

    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)

    await waitFor(() =>
      expect(screen.getByText(/grant consent in settings/i)).toBeInTheDocument()
    )
    expect(uploadProjectZip).not.toHaveBeenCalled()
  })

  it('shows uploading status while upload is in progress', async () => {
    uploadProjectZip.mockImplementation(() => new Promise(() => {}))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())

    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)

    expect(screen.getByText(/uploading and analyzing/i)).toBeInTheDocument()
  })

  it('loads projects into the list after a clean upload', async () => {
    uploadProjectZip.mockResolvedValue({
      status: 'complete',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: [],
    })
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())

    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)

    await waitFor(() => {
      expect(uploadProjectZip).toHaveBeenCalledOnce()
      expect(screen.getAllByText('my-app').length).toBeGreaterThan(0)
    })
  })

  it('opens the merge modal when duplicates are detected', async () => {
    uploadProjectZip.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())

    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)

    await waitFor(() =>
      expect(screen.getByText(/resolve duplicate contributors/i)).toBeInTheDocument()
    )
  })

  it('shows an error if the upload fails', async () => {
    uploadProjectZip.mockRejectedValue(new Error('Upload failed'))
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())

    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)

    await waitFor(() =>
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
    )
  })
})

// ── Delete project ────────────────────────────────────────────────────────────

describe('Delete project', () => {
  it('shows confirm modal when trash icon is clicked', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByTitle('Delete project')[0])
    expect(screen.getByText(/delete project\?/i)).toBeInTheDocument()
    expect(screen.getByText(/permanently remove/i)).toBeInTheDocument()
  })

  it('dismisses modal without deleting on go back', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByTitle('Delete project')[0])
    await user.click(screen.getByRole('button', { name: /go back/i }))
    expect(deleteProject).not.toHaveBeenCalled()
    expect(screen.queryByText(/delete project\?/i)).not.toBeInTheDocument()
  })

  it('calls deleteProject and removes project from list on confirm', async () => {
    listProjects.mockResolvedValue(PROJECT_LIST)
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => screen.getByText('my-app'))
    await user.click(screen.getAllByTitle('Delete project')[0])
    await user.click(screen.getByRole('button', { name: /yes, delete/i }))
    await waitFor(() => {
      expect(deleteProject).toHaveBeenCalledWith(1)
      expect(screen.queryByText('my-app')).not.toBeInTheDocument()
    })
  })
})

// ── Merge modal ───────────────────────────────────────────────────────────────

describe('Merge modal', () => {
  async function openMergeModal() {
    uploadProjectZip.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)
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

  it('closes the modal and reloads after merges are applied', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /apply merges/i }))
    await waitFor(() => {
      expect(resolveContributorsBatch).toHaveBeenCalledOnce()
      expect(screen.queryByText(/resolve duplicate contributors/i)).not.toBeInTheDocument()
    })
  })
})

// ── Cancel analysis ───────────────────────────────────────────────────────────

describe('Cancel analysis', () => {
  async function openMergeModal() {
    uploadProjectZip.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)
    await waitFor(() => screen.getByText(/resolve duplicate contributors/i))
    return user
  }

  it('shows confirmation screen when Cancel Analysis is clicked', async () => {
    const user = await openMergeModal()
    await user.click(screen.getByRole('button', { name: /cancel analysis/i }))
    expect(screen.getByText(/cancel analysis\?/i)).toBeInTheDocument()
    expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument()
  })

  it('returns to the merge screen when Go back is clicked', async () => {
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
})

// ── Identity modal ─────────────────────────────────────────────────────────────

describe('Identity modal', () => {
  async function openIdentityModal() {
    uploadProjectZip.mockResolvedValue({
      status: 'needs_identity',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: [],
      pending_identity: PENDING_IDENTITY,
    })
    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)
    await waitFor(() => screen.getByText(/which contributor are you\?/i))
    return user
  }

  it('opens the identity modal when upload returns needs_identity', async () => {
    await openIdentityModal()
    expect(screen.getByText(/which contributor are you\?/i)).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('Skip dismisses the modal without calling setIdentity', async () => {
    const user = await openIdentityModal()
    await user.click(screen.getByRole('button', { name: /skip/i }))
    await waitFor(() =>
      expect(screen.queryByText(/which contributor are you\?/i)).not.toBeInTheDocument()
    )
    expect(setIdentity).not.toHaveBeenCalled()
  })

  it('"This is me" calls setIdentity with the selected email and project id', async () => {
    const user = await openIdentityModal()
    // first candidate is pre-selected by default
    await user.click(screen.getByRole('button', { name: /this is me/i }))
    await waitFor(() =>
      expect(setIdentity).toHaveBeenCalledWith(
        ['alice@example.com'],
        [1],
      )
    )
  })

  it('closes the modal after confirming identity', async () => {
    const user = await openIdentityModal()
    await user.click(screen.getByRole('button', { name: /this is me/i }))
    await waitFor(() =>
      expect(screen.queryByText(/which contributor are you\?/i)).not.toBeInTheDocument()
    )
  })

  it('opens identity modal after merge resolution when pending_identity is returned', async () => {
    uploadProjectZip.mockResolvedValue({
      status: 'needs_resolution',
      projects: [{ id: 1, name: 'my-app' }],
      pending_duplicates: PENDING_DUPLICATES,
      pending_identity: [],
    })
    resolveContributorsBatch.mockResolvedValue({
      pending_identity: PENDING_IDENTITY,
    })

    const user = userEvent.setup()
    render(<Projects />)
    await waitFor(() => expect(listProjects).toHaveBeenCalledOnce())
    const file = new File(['content'], 'project.zip', { type: 'application/zip' })
    const input = document.querySelector('input[type="file"][accept=".zip"]')
    await user.upload(input, file)
    await waitFor(() => screen.getByText(/resolve duplicate contributors/i))
    await user.click(screen.getByRole('button', { name: /apply merges/i }))
    await waitFor(() =>
      expect(screen.getByText(/which contributor are you\?/i)).toBeInTheDocument()
    )
  })
})
