import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects,
  deleteProject,
  resolveContributorsBatch,
} from "../api/client";

function Projects() {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);
  const [projects, setProjects] = useState([]);
  const [currentProjects, setCurrentProjects] = useState([]);
  const [previousProjects, setPreviousProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [zipFile, setZipFile] = useState(null);
  const [pathInput, setPathInput] = useState("");
  const [pendingDuplicates, setPendingDuplicates] = useState([]);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [mergeSelections, setMergeSelections] = useState({});
  const [confirmCancel, setConfirmCancel] = useState(false);

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await listProjects();
      const allProjects = data.projects ?? [];
      const current = data.current_projects ?? allProjects;
      const previous = data.previous_projects ?? [];
      setProjects(allProjects);
      setCurrentProjects(current);
      setPreviousProjects(previous);
    } catch (e) {
      setError(e.message ?? "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(id) {
    setLoading(true);
    setError(null);
    try {
      const data = await getProject(id);
      setSelected(data.project ?? null);
    } catch (e) {
      setError(e.message ?? "Failed to load project");
    } finally {
      setLoading(false);
    }
  }

  async function handleUploadPath() {
    if (!pathInput.trim()) {
      setError("Enter a path first (example: TestResources/sample.zip)");
      return;
    }
    const consent = await getPrivacyConsent();
    if (!consent) {
      setError("You must grant consent in Settings in order to upload projects.");
      return;
    }

    setUploading(true);
    setError(null);
    setUploadStatus("Uploading and analyzing… this may take a moment.");

    try {
      const res = await uploadProjectFromPath(pathInput.trim());
      await loadProjects();

      if (res?.projects?.length) {
        await handleSelect(res.projects[0].id);
      }

      if (res?.status === "needs_resolution" && res?.pending_duplicates?.length) {
        setPendingDuplicates(res.pending_duplicates);
        setMergeSelections(buildInitialMergeSelections(res.pending_duplicates));
        setShowMergeModal(true);
        setUploadStatus("Upload complete. Contributor merges need review.");
      } else {
        setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
      }

      setPathInput("");
    } catch (e) {
      setError(e.message ?? "Path upload failed");
      setUploadStatus(null);
    } finally {
      setUploading(false);
    }
  }

  async function handleUpload() {
    if (!zipFile) {
      setError("Pick a .zip file first.");
      return;
    }
    const consent = await getPrivacyConsent();
    if (!consent) {
      setError("You must grant consent in Settings in order to upload projects.");
      return;
    }

    setUploading(true);
    setError(null);
    setUploadStatus("Uploading and analyzing… this may take a moment.");

    try {
      const res = await uploadProjectZip(zipFile);
      await loadProjects();

      if (res?.projects?.length)
        await handleSelect(res.projects[0].id);

      if (res?.status === "needs_resolution" && res?.pending_duplicates?.length) {
        setPendingDuplicates(res.pending_duplicates);
        setMergeSelections(buildInitialMergeSelections(res.pending_duplicates));
        setShowMergeModal(true);
        setUploadStatus("Upload complete. Contributor merges need review.");
      } else {
        setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
      }

      setZipFile(null);
    } catch (e) {
      setError(e.message ?? "Upload failed");
      setUploadStatus(null);
    } finally {
      setUploading(false);
    }
  }

  function buildInitialMergeSelections(pending) {
    const selections = {};
    for (const project of pending ?? []) {
      for (const group of project.duplicate_groups ?? []) {
        const key = `${project.project_id}::${group.suggested_canonical}`;
        selections[key] = group.suggested_canonical;
      }
    }
    return selections;
  }

  function updateMergeSelection(projectId, displayName, canonical) {
    const key = `${projectId}::${displayName}`;
    setMergeSelections((prev) => ({ ...prev, [key]: canonical }));
  }

  async function handleApplyContributorMerges() {
    try {
      setUploading(true);
      setError(null);

      await resolveContributorsBatch(pendingDuplicates, mergeSelections);
      await loadProjects();

      const firstProjectId = pendingDuplicates[0]?.project_id;
      if (firstProjectId) await handleSelect(firstProjectId);

      setPendingDuplicates([]);
      setMergeSelections({});
      setShowMergeModal(false);
      setConfirmCancel(false);
      setUploadStatus("Contributor merges applied.");
    } catch (e) {
      setError(e.message ?? "Failed to apply contributor merges");
    } finally {
      setUploading(false);
    }
  }

  async function handleCancelAnalysis() {
    try {
      await Promise.all(
        pendingDuplicates.map((p) => deleteProject(p.project_id))
      );
      await loadProjects();
    } catch (e) {
      setError(e.message ?? "Failed to cancel upload");
    } finally {
      setShowMergeModal(false);
      setConfirmCancel(false);
      setPendingDuplicates([]);
      setMergeSelections({});
      setUploadStatus(null);
      setSelected(null);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <>
      <style>{CSS}</style>
      <h3>Projects</h3>

      <button onClick={loadProjects} disabled={loading}>
        {loading ? "Loading..." : "Refresh Projects"}
      </button>
      <button
        onClick={async () => {
          setLoading(true);
          setError(null);
          try {
            await clearProjects();
            setSelected(null);
            await loadProjects();
          } catch (e) {
            setError(e.message ?? "Failed to clear database");
          } finally {
            setLoading(false);
          }
        }}
        disabled={loading}
        style={{ marginLeft: 8 }}
      >
        {loading ? "Clearing..." : "Clear Database"}
      </button>

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Add Project (Upload ZIP)</h4>

        <input
          ref={fileInputRef}
          type="file"
          accept=".zip"
          onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
          disabled={loading}
          style={{ display: "none" }}
        />

        <button
          onClick={() => zipFile ? handleUpload() : fileInputRef.current?.click()}
          disabled={uploading}
          style={{ marginLeft: 8 }}
        >
          {uploading ? "Uploading..." : zipFile ? "Upload ZIP" : "Choose ZIP"}
        </button>

        {uploadStatus && <p style={{ marginTop: 8, opacity: 0.8 }}>{uploadStatus}</p>}

        {zipFile && (
          <p style={{ marginTop: 8, opacity: 0.8 }}>
            Selected: {zipFile.name}
          </p>
        )}
      </div>

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Quick Load Test Projects</h4>

        {[
          "testResources/testMultiFileAndRepos.zip",
          "testResources/testMultiRepo.zip",
          "testResources/earlyProject.zip",
          "testResources/lateProject.zip",
        ].map((p) => (
          <div key={p} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <code style={{ flex: 1 }}>{p}</code>
            <button onClick={() => setPathInput(p)} disabled={uploading}>Use</button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h4>Or Load from Local Path (Dev)</h4>

        <input
          type="text"
          placeholder="testResources/sample.zip"
          value={pathInput}
          onChange={(e) => setPathInput(e.target.value)}
          disabled={loading}
          style={{ width: 320 }}
        />

        <button onClick={handleUploadPath} disabled={uploading || !pathInput.trim()} style={{ marginLeft: 8 }}>
          {uploading ? "Loading..." : "Load From Path"}
        </button>
      </div>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
        <div style={{ minWidth: 320 }}>
          <h4>Current Projects</h4>
          {currentProjects.length === 0 ? <p>No projects in the current import batch yet.</p> : (
            <ul>
              {currentProjects.map((p) => (
                <li key={`current-${p.id}`}>
                  <button
                    onClick={() => handleSelect(p.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    {p.name} (#{p.id})
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h4>Previous Projects</h4>
          {previousProjects.length === 0 ? <p>No previous projects yet.</p> : (
            <ul>
              {previousProjects.map((p) => (
                <li key={`previous-${p.id}`}>
                  <button
                    onClick={() => handleSelect(p.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    {p.name} (#{p.id})
                  </button>
                </li>
              ))}
            </ul>
          )}

          <p style={{ opacity: 0.7 }}>Total projects stored: {projects.length}</p>
        </div>

        <div style={{ flex: 1 }}>
          <h4>Selected Project</h4>
          {selected ? <pre>{JSON.stringify(selected, null, 2)}</pre> : <p>Click a project to view details.</p>}
        </div>
      </div>

      {showMergeModal && (
        <div className="pj-overlay">
          <div className="pj-modal">
            <div className="pj-bar" aria-hidden="true" />

            {confirmCancel ? (
              <>
                <div className="pj-confirm-body">
                  <div className="pj-confirm-icon">⚠️</div>
                  <h2 className="pj-confirm-title">Cancel analysis?</h2>
                  <p className="pj-confirm-sub">
                    This will delete the {pendingDuplicates.length === 1 ? "project" : `${pendingDuplicates.length} projects`} that were just uploaded. This cannot be undone — you'll need to re-upload to analyze them.
                  </p>
                </div>
                <div className="pj-modal-footer">
                  <button
                    className="pj-btn pj-btn--ghost"
                    disabled={uploading}
                    onClick={() => setConfirmCancel(false)}
                  >
                    ← Go back
                  </button>
                  <button
                    className="pj-btn pj-btn--ghost pj-btn--danger"
                    disabled={uploading}
                    onClick={handleCancelAnalysis}
                  >
                    {uploading ? "Cancelling…" : "Yes, cancel analysis"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="pj-modal-header">
                  <h2 className="pj-modal-title">Resolve duplicate contributors</h2>
                  <p className="pj-modal-sub">
                    These contributors appear to be the same person using different emails. Choose which identity to keep.
                  </p>
                </div>

                <div className="pj-modal-body">
                  {pendingDuplicates.map((project) => (
                    <div key={project.project_id} className="pj-project-group">
                      <p className="pj-project-label">{project.project_name}</p>
                      {(project.duplicate_groups ?? []).map((group) => {
                        const key = `${project.project_id}::${group.suggested_canonical}`;
                        const selectedCanonical = mergeSelections[key] || group.suggested_canonical;
                        return (
                          <div key={key} className="pj-dup-group">
                            <p className="pj-dup-name">{group.display_name}</p>
                            <div className="pj-candidates">
                              {group.candidates.map((c) => (
                                <span key={c} className="pj-candidate">{c}</span>
                              ))}
                            </div>
                            <label className="pj-keep-label">
                              <span className="pj-keep-text">Keep as</span>
                              <select
                                className="pj-select"
                                value={selectedCanonical}
                                onChange={(e) =>
                                  updateMergeSelection(project.project_id, group.display_name, e.target.value)
                                }
                              >
                                {group.candidates.map((c) => (
                                  <option key={c} value={c}>{c}</option>
                                ))}
                              </select>
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>

                <div className="pj-modal-footer">
                  <button
                    className="pj-btn pj-btn--ghost pj-btn--danger"
                    disabled={uploading}
                    onClick={() => setConfirmCancel(true)}
                  >
                    Cancel Analysis
                  </button>
                  <button
                    className="pj-btn pj-btn--primary"
                    disabled={uploading}
                    onClick={handleApplyContributorMerges}
                  >
                    {uploading ? "Applying…" : "Apply merges →"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default Projects;

// ── Styles ────────────────────────────────────────────────────────────────────

const CSS = `
.pj-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
}
.pj-modal {
  --accent:  #58a6ff;
  --accent2: #f78166;
  --bg:      #0d1117;
  --surface: #161b22;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --r:       10px;
  width: min(620px, 92vw); max-height: 80vh;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; overflow: hidden;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(88,166,255,.06);
  font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
  animation: pj-fadein .2s ease both;
}
@keyframes pj-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.pj-bar {
  height: 3px; flex-shrink: 0;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent));
  background-size: 200% 100%;
  animation: pj-shimmer 3s linear infinite;
}
@keyframes pj-shimmer {
  0%   { background-position: 200% center; }
  100% { background-position: -200% center; }
}
.pj-modal-header {
  padding: 20px 24px 16px; flex-shrink: 0;
  border-bottom: 1px solid var(--border);
}
.pj-modal-title {
  font-size: 17px; font-weight: 700; margin: 0 0 6px;
  color: var(--text);
}
.pj-modal-sub {
  font-size: 13px; color: var(--muted); line-height: 1.6; margin: 0;
}
.pj-modal-body {
  padding: 16px 24px; overflow-y: auto; flex: 1;
}
.pj-project-group { margin-bottom: 20px; }
.pj-project-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: var(--muted); margin: 0 0 10px;
}
.pj-dup-group {
  margin-bottom: 10px; padding: 14px 16px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--r);
}
.pj-dup-name {
  font-size: 14px; font-weight: 600; color: var(--text); margin: 0 0 8px;
}
.pj-candidates {
  display: flex; flex-direction: column; gap: 3px; margin-bottom: 12px;
}
.pj-candidate {
  font-size: 12px; color: var(--muted);
}
.pj-keep-label {
  display: flex; align-items: center; gap: 8px;
}
.pj-keep-text {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .6px; color: var(--muted); white-space: nowrap;
}
.pj-select {
  flex: 1; height: 36px; padding: 0 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); color: var(--text);
  font-size: 12px;
  outline: none; cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
}
.pj-select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(88,166,255,.15);
}
.pj-modal-footer {
  padding: 14px 24px; flex-shrink: 0;
  border-top: 1px solid var(--border);
  display: flex; justify-content: flex-end; align-items: center; gap: 8px;
}
.pj-confirm-body {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 48px 32px 32px;
  text-align: center;
}
.pj-confirm-icon {
  font-size: 40px; margin-bottom: 16px;
}
.pj-confirm-title {
  font-size: 20px; font-weight: 700; color: var(--text);
  margin: 0 0 12px;
}
.pj-confirm-sub {
  font-size: 14px; color: var(--muted); line-height: 1.6;
  max-width: 380px; margin: 0;
}
.pj-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 38px; padding: 0 18px; border-radius: var(--r);
  font-size: 14px; font-weight: 600; cursor: pointer;
  border: 1.5px solid transparent; font-family: inherit;
  transition: all .15s;
}
.pj-btn--primary {
  background: var(--accent); color: #0d1117; border-color: var(--accent);
}
.pj-btn--primary:hover:not(:disabled) {
  background: #79c0ff; border-color: #79c0ff;
  box-shadow: 0 0 14px rgba(88,166,255,.35); transform: translateY(-1px);
}
.pj-btn--primary:disabled { opacity: .5; cursor: not-allowed; }
.pj-btn--ghost {
  background: transparent; color: var(--muted); border-color: var(--border);
}
.pj-btn--ghost:hover:not(:disabled) { border-color: var(--muted); color: var(--text); }
.pj-modal .pj-btn--danger {
  background: transparent; color: #f85149; border-color: #f85149;
}
.pj-modal .pj-btn--danger:hover:not(:disabled) { background: transparent; border-color: #ff7b72; color: #ff7b72; }
`;
