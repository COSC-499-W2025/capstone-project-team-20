import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects,
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
    
    setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
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
    
    setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
    setZipFile(null);

  } catch (e) {
    setError(e.message ?? "Upload failed");
    setUploadStatus(null);
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
    </>
  );
}
export default Projects;