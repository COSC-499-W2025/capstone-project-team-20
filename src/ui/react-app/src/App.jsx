import { useState, useEffect } from "react";
import ProfileSetup from "./ProfileSetup";
import Settings from "./Settings";
import {
  listProjects,
  getProject,
  listSkills,
  getBadgeProgress, 
  getYearlyWrapped,
  getConfig,
  setPrivacyConsent,
  getPrivacyConsent,
  createReport,
  exportResume,
  exportPortfolio,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects
} from "./api/client";
import './App.css'

function App() {
  //starts the actual app itself, all pages are gathered here

  //creates a variable 'current' with a method 'setcurrent' that updates it, we set to 1 by default here.
  const [profileReady, setProfileReady] = useState(null);
  const [current, setCurrent] = useState(1);

  useEffect(() => {
    getConfig()
      .then((cfg) => setProfileReady(!!(cfg?.name && cfg?.email && cfg?.phone)))
      .catch(() => setProfileReady(false));
  }, []);

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
      case 0: return <Settings />;
      case 1: return <Projects />;
      case 2: return <Badges />;
      case 3: return <Resume />;
      case 4: return <Portfolio />;
      case 5: return <Help />;
    }
  }
  // ensure name, phone, email are set
  if (profileReady === null) return <div className="ps-loading">Loading…</div>;
  if (!profileReady) return <ProfileSetup onComplete={() => setProfileReady(true)} />;

  //on app construction/refresh, builds our UI
  return(
    <div className="app-shell">
      <div className="grid-bg"></div>
      
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
    </div>
  );
}

function Projects() {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

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
  const consent = await getPrivacyConsent();
  if (!consent) { setError("You must grant consent in Settings in order to upload projects."); return; }

  setUploading(true);
  setError(null);

  try {

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
  const consent = await getPrivacyConsent();
  if (!consent) { setError("You must grant consent in Settings in order to upload projects."); return; }

  setUploading(true);
  setError(null);

  try {

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
        <div style={{ minWidth: 320 }}>
          <h4>Current Projects</h4>
          {currentProjects.length === 0 ? (
            <p>No projects in the current import batch yet.</p>
          ) : (
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
          {previousProjects.length === 0 ? (
            <p>No previous projects yet.</p>
          ) : (
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
  const [progress, setProgress] = useState([]);
  const [wrapped, setWrapped] = useState([]);

  async function loadBadgeData() {
    setLoading(true);
    setError(null);
    try {
      const [skillsData, progressData, wrappedData] = await Promise.all([
          listSkills(),
          getBadgeProgress(),
          getYearlyWrapped(),
        ]);
        setSkills(skillsData.skills ?? []);
        setProgress(progressData.badges ?? []);
        setWrapped(wrappedData.wrapped ?? []);
      } catch (e) {
        setError(e.message ?? "Failed to load badges and wrapped stats");
      } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBadgeData();
  }, []);

  const inProgress = progress.filter((b) => !b.earned);
    const achievedProgressBadges = progress.filter((b) => b.earned);

    const achievedBadgeMap = new Map();
    wrapped.forEach((yearBlock) => {
      (yearBlock.milestones ?? []).forEach((m) => {
        if (!achievedBadgeMap.has(m.badge_id)) {
          achievedBadgeMap.set(m.badge_id, { badge_id: m.badge_id, projects: [] });
        }
        const badge = achievedBadgeMap.get(m.badge_id);
        const projectKey = `${m.project}::${m.achieved_on ?? ""}`;
        const alreadyListed = badge.projects.some((p) => `${p.project}::${p.achieved_on ?? ""}` === projectKey);
        if (!alreadyListed) {
          badge.projects.push({
            project: m.project,
            achieved_on: m.achieved_on,
          });
        }
      });
    });

    achievedProgressBadges.forEach((b) => {
    const projectName = b.project?.name ?? "Unknown project";
    if (!achievedBadgeMap.has(b.badge_id)) {
      achievedBadgeMap.set(b.badge_id, { badge_id: b.badge_id, label: b.label, projects: [] });
    }
    const badge = achievedBadgeMap.get(b.badge_id);
    if (!badge.label) {
      badge.label = b.label;
    }
    const alreadyListed = badge.projects.some((p) => p.project === projectName);
    if (!alreadyListed) {
      badge.projects.push({ project: projectName, achieved_on: null });
    }
  });

  const achievedBadges = Array.from(achievedBadgeMap.values()).sort((a, b) =>
    (a.label ?? a.badge_id).localeCompare(b.label ?? b.badge_id)
  );

  return (
    <>
      <h3>Badges</h3>

      <button onClick={loadBadgeData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Badge Data"}
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <h4>🎯 Badge Progress Tracker (Uncompleted)</h4>
      {inProgress.length === 0 ? (
        <p>All tracked progress badges are complete 🎉</p>
      ) : (
        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
          {inProgress.map((b) => (
            <li key={b.badge_id} style={{ marginBottom: 12, border: "1px solid #2f4d6f", borderRadius: 8, padding: 10 }}>
              <strong>{b.label}</strong> — {Math.round((b.progress ?? 0) * 100)}%
              <div style={{ height: 10, borderRadius: 999, background: "#21344a", marginTop: 8, overflow: "hidden" }}>
                <div style={{ width: `${Math.round((b.progress ?? 0) * 100)}%`, height: "100%", background: "#55BDCA" }} />
              </div>
              <small>
                {b.metric}: {(b.current ?? 0).toFixed(2)} / {b.target} • Closest project: {b.project?.name ?? "N/A"} • ⏳ In progress
              </small>
            </li>
          ))}
        </ul>
      )}

      <h4>🏅 Achieved Badges</h4>
      {achievedBadges.length === 0 ? (
        <p>No achieved badges yet. Upload and analyze projects to start earning them.</p>
      ) : (
        <ul>
          {achievedBadges.map((badge) => (
            <li key={`achieved-${badge.badge_id}`}>
              ✅ <strong>{badge.label ?? badge.badge_id}</strong>
              <ul>
                {badge.projects.map((projectEntry, idx) => (
                  <li key={`achieved-${badge.badge_id}-${projectEntry.project}-${idx}`}>
                    <strong>{projectEntry.project}</strong>
                    {projectEntry.achieved_on ? ` — ${projectEntry.achieved_on}` : ""}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}


      <h4>🎉 Yearly Wrapped</h4>
      {wrapped.length === 0 ? (
        <p>No yearly wrapped history available yet.</p>
      ) : (
        wrapped.map((yearBlock) => (
          <div key={yearBlock.year} style={{ marginBottom: 14, border: "1px solid #3f638c", borderRadius: 12, padding: 12, background: "linear-gradient(135deg, rgba(85,189,202,0.12), rgba(242,125,66,0.10))" }}>
            <h5>{yearBlock.vibe_title}</h5>
            <p>
              Projects: {yearBlock.projects_count} • LOC: {yearBlock.total_loc} • Files: {yearBlock.total_files} • Avg test ratio: {(yearBlock.avg_test_file_ratio * 100).toFixed(1)}%
            </p>
            {yearBlock.highlights?.length ? (
              <ul>
                {yearBlock.highlights.map((line, idx) => (
                  <li key={`${yearBlock.year}-highlight-${idx}`}>{line}</li>
                ))}
              </ul>
            ) : null}
            <p><strong>Milestones:</strong></p>
            {yearBlock.milestones?.length ? (
              <ul>
                {yearBlock.milestones.map((m, idx) => (
                  <li key={`${yearBlock.year}-${m.badge_id}-${idx}`}>
                    🏅 {m.badge_id} earned in <strong>{m.project}</strong>{m.achieved_on ? ` on ${m.achieved_on}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No badge milestones recorded for this year.</p>
            )}
          </div>
        ))
      )}

      <h4>🔥 Skill Heatmap</h4>

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
