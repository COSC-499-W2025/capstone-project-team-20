import { useState, useEffect } from "react";
import { listProjects, getProject, getPortfolio, listSkills, getBadgeProgress, getYearlyWrapped, } from "./api/client";
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
  const [error, setError] = useState(null);

  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);

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

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <>
      <h3>Projects</h3>

      <button onClick={loadProjects} disabled={loading}>
        {loading ? "Loading..." : "Refresh Projects"}
      </button>

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

  return (
    <>
      <h3>Badges</h3>

      <button onClick={loadBadgeData} disabled={loading}>
        {loading ? "Loading..." : "Refresh Badge Data"}
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <h4>🎯 Badge Progress Tracker</h4>
      {progress.length === 0 ? (
        <p>No badge progress data yet. Upload projects to start earning badges.</p>
      ) : (
        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
          {progress.map((b) => (
            <li key={b.badge_id} style={{ marginBottom: 12, border: "1px solid #2f4d6f", borderRadius: 8, padding: 10 }}>
              <strong>{b.label}</strong> — {Math.round((b.progress ?? 0) * 100)}%
              <div style={{ height: 10, borderRadius: 999, background: "#21344a", marginTop: 8, overflow: "hidden" }}>
                <div style={{ width: `${Math.round((b.progress ?? 0) * 100)}%`, height: "100%", background: b.earned ? "#29c77d" : "#55BDCA" }} />
              </div>
              <small>
                {b.metric}: {(b.current ?? 0).toFixed(2)} / {b.target} • Closest project: {b.project?.name ?? "N/A"}
                {b.earned ? " • ✅ Earned" : " • ⏳ In progress"}
              </small>
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
                    🏅 {m.badge_id} earned in <strong>{m.project}</strong>
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

function Resume(){
    return(
        <>
        <h3>This is the Resume page.</h3>
        </>
    );
}

function Portfolio(){
    return(
        <>
        <h3>This is the Portfolio page.</h3>
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
