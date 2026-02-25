import { useState, useEffect } from "react";
import {
  listProjects,
  getProject,
  listSkills,
  setPrivacyConsent,
  createReport,
  exportResume,
  exportPortfolio,
  uploadProjectZip,
  uploadProjectFromPath
} from "./api/client";
import './App.css'

function App() {
  //starts the actual app itself, all pages are gathered here

  //creates a variable 'current' with a method 'setcurrent' that updates it, we set to 1 by default here.
  const [current, setCurrent] = useState(1);

  const buttons = [
    //id for use with 'current', label is a placeholder as of now
    {id:0, label:"Settings"},
    {id:1, label:"Projects"},
    {id:2, label:"Badges"},
    {id:3, label:"Resume"},
    {id:4, label:"Portfolio"},
    {id:5, label:"Help"}
  ];

  const whenClick = (id) => {
    //takes the button of the id clicked and sets our 'current' variable to it
    console.log("Clicked:",id);
    setCurrent(id);
  };

  const menuRender = () => {
    //ran on render, renders correct page based on selection
    //menu pages currently stored as individual functions within this file. Scroll down to locate.
    switch(current) {
      case 0:
        return <Settings />;
      case 1:
        return <Projects />;
      case 2:
        return <Badges />;
      case 3:
        return <Resume />;
      case 4:
        return <Portfolio />;
      case 5:
        return <Help />;
    }
  }

  //on app construction/refresh, builds our UI
  return(
    <div className="screen">
      {/* Left Side Buttons */}
      <div className="stacked-buttons">
        {buttons.map(button => (
          <button
            key = {button.id}
            className={
              button.id === current
                ? "button-on"
                : "button-off"
            }
            onClick={()=>whenClick(button.id)}
          >
            {button.label}
          </button>
        ))}
      </div>

      {/* Right Side Content */}
      <div className="menu">
        {menuRender()}
      </div>
    </div>
  );
}

function Settings(){
    return(
        <>
        <h3>This is the Settings page.</h3>
        </>
    );
}

function Projects() {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [zipFile, setZipFile] = useState(null);
  const [pathInput, setPathInput] = useState("");

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await listProjects();
      setProjects(data.projects ?? []);
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
      const data = await getProject(id); // { project: {...} }
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

  setUploading(true);
  setError(null);

  try {
    await setPrivacyConsent(true);

    const res = await uploadProjectFromPath(pathInput.trim());

    await loadProjects();

    if (res?.projects?.length) {
      await handleSelect(res.projects[0].id);
    }

    setPathInput("");
  } catch (e) {
    setError(e.message ?? "Path upload failed");
  } finally {
    setUploading(false);
  }
}

  async function handleUpload() {
  if (!zipFile) {
    setError("Pick a .zip file first.");
    return;
  }

  setUploading(true);
  setError(null);

  try {
    // consent first
    await setPrivacyConsent(true);

    // upload zip, backend creates projects
    const res = await uploadProjectZip(zipFile);

    // refresh list
    await loadProjects();

    // auto-select first created project
    if (res?.projects?.length) {
      await handleSelect(res.projects[0].id);
    }

    setZipFile(null);
  } catch (e) {
    setError(e.message ?? "Upload failed");
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
      <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
      <h4>Add Project (Upload ZIP)</h4>

      <input
        type="file"
        accept=".zip"
        onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
        disabled={loading}
      />

      <button
        onClick={handleUpload}
        disabled={uploading || !zipFile}
        style={{ marginLeft: 8 }}
      >
        {loading ? "Uploading..." : "Upload ZIP"}
      </button>

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

            <button onClick={() => setPathInput(p)} disabled={uploading}>
              Use
            </button>
          </div>
        ))}
      </div>

    <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
      <h4>Or Load from Local Path (Dev)</h4>

      <input
        type="text"
        placeholder="TestResources/sample.zip"
        value={pathInput}
        onChange={(e) => setPathInput(e.target.value)}
        disabled={loading}
        style={{ width: 320 }}
      />

      <button
        onClick={handleUploadPath}
        disabled={uploading || !pathInput.trim()}
        style={{ marginLeft: 8 }}
      >
        {uploading ? "Loading..." : "Load From Path"}
      </button>
    </div>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
        <div style={{ minWidth: 260 }}>
          <ul>
            {projects.map((p) => (
              <li key={p.id}>
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
        </div>

        <div style={{ flex: 1 }}>
          <h4>Selected Project</h4>
          {selected ? (
            <pre>{JSON.stringify(selected, null, 2)}</pre>
          ) : (
            <p>Click a project to view details.</p>
          )}
        </div>
      </div>
    </>
  );
}

function Badges() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [skills, setSkills] = useState([]);

  async function loadSkills() {
    setLoading(true);
    setError(null);
    try {
      const data = await listSkills(); // { skills: [{name, project_count}, ...] }
      setSkills(data.skills ?? []);
    } catch (e) {
      setError(e.message ?? "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSkills();
  }, []);

  return (
    <>
      <h3>Badges</h3>

      <button onClick={loadSkills} disabled={loading}>
        {loading ? "Loading..." : "Refresh Skills"}
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      {skills.length === 0 ? (
        <p>No skills found yet. Upload a project first.</p>
      ) : (
        <ul>
          {skills.map((s) => (
            <li key={s.name}>
              {s.name} — used in {s.project_count} project{s.project_count === 1 ? "" : "s"}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Resume() {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  async function handleExport() {
    setLoading(true);
    setMsg("");
    try {
      await setPrivacyConsent(true);

      // TEMP: create a report from all projects in DB
      const { projects } = await listProjects();
      const ids = (projects ?? []).map((p) => p.id);

      if (ids.length === 0) {
        setMsg("No projects found. Upload a project first.");
        return;
      }

      const created = await createReport({
        title: "Resume Report",
        sort_by: "resume_score",
        notes: "Generated from UI",
        project_ids: ids,
      });

      const reportId = created.report.id;

      const exp = await exportResume({
        report_id: reportId,
        template: "jake",
        output_name: "resume.pdf",
      });

      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
      setMsg("Resume export started — opened download in a new tab.");
    } catch (e) {
      setMsg(e.message ?? "Failed to export resume");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h3>Resume</h3>
      <button onClick={handleExport} disabled={loading}>
        {loading ? "Exporting..." : "Export Resume PDF"}
      </button>
      {msg && <p>{msg}</p>}
    </>
  );
}

function Portfolio() {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  async function handleExport() {
    setLoading(true);
    setMsg("");
    try {
      await setPrivacyConsent(true);

      const { projects } = await listProjects();
      const ids = (projects ?? []).map((p) => p.id);

      if (ids.length === 0) {
        setMsg("No projects found. Upload a project first.");
        return;
      }

      const created = await createReport({
        title: "Portfolio Report",
        sort_by: "resume_score",
        notes: "Generated from UI",
        project_ids: ids,
      });

      const reportId = created.report.id;

      // NOTE: portfolio export will fail unless portfolio_details exist for each report project
      // If you haven’t generated them yet, add that step later.
      const exp = await exportPortfolio({
        report_id: reportId,
        output_name: "portfolio.pdf",
      });

      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
      setMsg("Portfolio export started — opened download in a new tab.");
    } catch (e) {
      setMsg(e.message ?? "Failed to export portfolio");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h3>Portfolio</h3>
      <button onClick={handleExport} disabled={loading}>
        {loading ? "Exporting..." : "Export Portfolio PDF"}
      </button>
      {msg && <p>{msg}</p>}
    </>
  );
}

function Help(){
    return(
        <>
        <h3>This is the Help page.</h3>
        </>
    );
}

export default App;
