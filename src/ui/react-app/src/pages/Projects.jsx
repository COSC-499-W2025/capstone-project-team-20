import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects,
  resolveContributors,
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
    return; }

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
    return; }

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
      const key = `${project.project_id}::${group.display_name}`;
      selections[key] = group.suggested_canonical;
    }
  }

  return selections;
}

function updateMergeSelection(projectId, displayName, canonical) {
  const key = `${projectId}::${displayName}`;
  setMergeSelections((prev) => ({
    ...prev,
    [key]: canonical,
  }));
}

async function handleApplyContributorMerges() {
  try {
    setUploading(true);
    setError(null);

    for (const project of pendingDuplicates) {
      const resolutions = (project.duplicate_groups ?? []).map((group) => {
        const key = `${project.project_id}::${group.display_name}`;
        return {
          canonical: mergeSelections[key] || group.suggested_canonical,
          merge: group.candidates,
        };
      });

      await resolveContributors(project.project_id, resolutions);
    }

    await loadProjects();

    if (pendingDuplicates?.length) {
      const firstProjectId = pendingDuplicates[0]?.project_id;
      if (firstProjectId) {
        await handleSelect(firstProjectId);
      }
    }

    setPendingDuplicates([]);
    setMergeSelections({});
    setShowMergeModal(false);
    setUploadStatus("Contributor merges applied.");
  } catch (e) {
    setError(e.message ?? "Failed to apply contributor merges");
  } finally {
    setUploading(false);
  }
}

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <>
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
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: "white",
              color: "black",
              width: "min(900px, 90vw)",
              maxHeight: "85vh",
              overflowY: "auto",
              borderRadius: 12,
              padding: 20,
              boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
            }}
          >
            <h3>Resolve Duplicate Contributors</h3>
            <p>
              We found contributors that look like the same person using different
              emails or usernames. Choose which identity should be kept.
            </p>

            {pendingDuplicates.map((project) => (
              <div
                key={project.project_id}
                style={{
                  marginBottom: 20,
                  padding: 12,
                  border: "1px solid #ddd",
                  borderRadius: 8,
                }}
              >
                <h4 style={{ marginTop: 0 }}>{project.project_name}</h4>

                {(project.duplicate_groups ?? []).map((group) => {
                  const key = `${project.project_id}::${group.display_name}`;
                  const selectedCanonical =
                    mergeSelections[key] || group.suggested_canonical;

                  return (
                    <div
                      key={key}
                      style={{
                        marginBottom: 16,
                        padding: 12,
                        border: "1px solid #eee",
                        borderRadius: 8,
                      }}
                    >
                      <div style={{ marginBottom: 8 }}>
                        <strong>{group.display_name}</strong>
                      </div>

                      <div style={{ marginBottom: 8 }}>
                        <div style={{ marginBottom: 4 }}>Detected identities:</div>
                        <ul style={{ marginTop: 0 }}>
                          {group.candidates.map((candidate) => (
                            <li key={candidate}>{candidate}</li>
                          ))}
                        </ul>
                      </div>

                      <label>
                        Keep as:
                        <select
                          value={selectedCanonical}
                          onChange={(e) =>
                            updateMergeSelection(
                              project.project_id,
                              group.display_name,
                              e.target.value
                            )
                          }
                          style={{ marginLeft: 8 }}
                        >
                          {group.candidates.map((candidate) => (
                            <option key={candidate} value={candidate}>
                              {candidate}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                  );
                })}
              </div>
            ))}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                onClick={() => {
                  setShowMergeModal(false);
                  setPendingDuplicates([]);
                  setMergeSelections({});
                }}
                disabled={uploading}
              >
                Cancel
              </button>
              <button onClick={handleApplyContributorMerges} disabled={uploading}>
                {uploading ? "Applying..." : "Apply Merges"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
export default Projects;