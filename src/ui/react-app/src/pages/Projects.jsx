import { useEffect, useRef, useState } from "react";
import {
  listProjects,
  getProject,
  getPrivacyConsent,
  uploadProjectZip,
  deleteProject,
  resolveContributorsBatch,
  uploadThumbnail,
  thumbnailUrl,
} from "../api/client";

// ── Language colours ──────────────────────────────────────────────────────────
const LANG_COLORS = {
  Python:"#3572A5", JavaScript:"#f1e05a", TypeScript:"#2b7489",
  Java:"#b07219", "C++":"#f34b7d", C:"#555555", "C#":"#178600",
  Go:"#00ADD8", Rust:"#dea584", Ruby:"#701516", PHP:"#4F5D95",
  Swift:"#ffac45", Kotlin:"#A97BFF", Scala:"#c22d40", HTML:"#e34c26",
  CSS:"#563d7c", Shell:"#89e051", R:"#198CE7", MATLAB:"#e16737",
  Lua:"#000080", Haskell:"#5e5086", Dart:"#00B4AB", Elixir:"#6e4a7e",
  default:"#4a5568",
};
const lc = (l) => LANG_COLORS[l] ?? LANG_COLORS.default;
const scoreColor = (s) => s >= 7 ? "#4ade80" : s >= 4 ? "#fbbf24" : "#6b7280";
const fmt = (iso) => iso
  ? new Date(iso).toLocaleDateString("en-CA", { year:"numeric", month:"short" })
  : null;

// ── Language bar ──────────────────────────────────────────────────────────────
function LangBar({ share = {}, langs = [], height = 4 }) {
  const entries = Object.entries(share).sort((a, b) => b[1] - a[1]);
  if (!entries.length && langs.length) {
    const pct = 100 / langs.length;
    langs.forEach(l => entries.push([l, pct]));
  }
  if (!entries.length) return null;
  return (
    <div style={{ display:"flex", height, borderRadius:99, overflow:"hidden", gap:1 }}>
      {entries.map(([l, p]) => (
        <div key={l} title={`${l} ${p.toFixed(1)}%`}
          style={{ flex:p, background:lc(l), minWidth:2 }} />
      ))}
    </div>
  );
}

// ── Thumbnail placeholder ─────────────────────────────────────────────────────
function ThumbPlaceholder({ project, size = 56 }) {
  const lang = project.languages?.[0] ?? "";
  const color = lc(lang);
  const initial = lang ? lang[0].toUpperCase() : project.name?.[0]?.toUpperCase() ?? "?";
  return (
    <div style={{
      width:"100%", height:"100%",
      background:`linear-gradient(135deg,${color}22,${color}44)`,
      display:"flex", alignItems:"center", justifyContent:"center",
      position:"relative", overflow:"hidden",
    }}>
      <div style={{
        position:"absolute", inset:0,
        backgroundImage:`linear-gradient(${color}18 1px,transparent 1px),linear-gradient(90deg,${color}18 1px,transparent 1px)`,
        backgroundSize:"14px 14px",
      }}/>
      <span style={{
        fontFamily:"'DM Mono','Fira Mono',monospace",
        fontSize:size * 0.44, fontWeight:700, color, opacity:.65,
        position:"relative", zIndex:1,
      }}>{initial}</span>
    </div>
  );
}

// ── Upload zone ───────────────────────────────────────────────────────────────
function UploadZone({ onFile, uploading, uploadStatus, error, hasProjects }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef();
  const big = !hasProjects;
  return (
    <div
      className={`pj-drop${drag?" pj-drop--over":""}${uploading?" pj-drop--busy":""}${big?" pj-drop--big":""}`}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f?.name.endsWith(".zip")) onFile(f); }}
      onClick={() => !uploading && ref.current?.click()}
    >
      <input ref={ref} type="file" accept=".zip" style={{ display:"none" }}
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value=""; }} />
      {uploading
        ? <><div className="pj-spinner" /><span className="pj-drop-label">{uploadStatus ?? "Analyzing…"}</span></>
        : <>
            <svg width={big?36:20} height={big?36:20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity:.45, flexShrink:0 }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <div style={{ textAlign: big ? "center" : "left" }}>
              <span className="pj-drop-label" style={{ fontSize: big ? 14 : 12 }}>
                Drop <strong>.zip</strong> or click to browse
              </span>
              {big && <div style={{ fontSize:11, color:"rgba(255,255,255,.25)", marginTop:4 }}>Upload a ZIP of your project to get started</div>}
            </div>
          </>
      }
      {error && <span style={{ fontSize:11, color:"#f87171", marginTop:4, display:"block" }}>{error}</span>}
    </div>
  );
}

// ── Project list item ─────────────────────────────────────────────────────────
function ProjectItem({ project, isSelected, onClick, onDelete }) {
  const color = lc(project.languages?.[0] ?? "");
  const [hovered, setHovered] = useState(false);
  return (
    <div
      className={`pj-item${isSelected ? " pj-item--active" : ""}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={onClick}
        style={{
          display:"flex", alignItems:"center", gap:10, flex:1, minWidth:0,
          background:"none", border:"none", cursor:"pointer",
          padding:"8px 4px 8px 10px", textAlign:"left",
          color:"inherit", fontFamily:"inherit",
          height:"auto", borderRadius:0, transform:"none", boxShadow:"none",
        }}
      >
        {isSelected && <div className="pj-item-accent" style={{ background: color }} />}
        <div style={{ flex:1, minWidth:0 }}>
          <div className="pj-item-name">{project.name}</div>
          {project.languages?.length > 0 && (
            <div className="pj-item-lang">{project.languages[0]}</div>
          )}
        </div>
        {project.resume_score > 0 && (
          <span className="pj-item-score" style={{ color: scoreColor(project.resume_score) }}>
            {project.resume_score.toFixed(1)}
          </span>
        )}
      </button>
      <button
        onClick={e => { e.stopPropagation(); onDelete(project.id); }}
        title="Delete project"
        style={{
          background:"none", border:"none", cursor:"pointer",
          color: hovered ? "rgba(255,255,255,.25)" : "rgba(255,255,255,.25)",
          padding:"8px 10px 8px 4px",
          display:"flex", alignItems:"center", flexShrink:0,
          height:"auto", borderRadius:5, transform:"none", boxShadow:"none",
          opacity: hovered ? 1 : 0,
          transition:"opacity .15s, color .15s",
          lineHeight:1,
        }}
        onMouseOver={e => { e.currentTarget.style.color = "#f85149"; }}
        onMouseOut={e => { e.currentTarget.style.color = "rgba(255,255,255,.25)"; }}
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6M14 11v6"/>
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
        </svg>
      </button>
    </div>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────
function SLabel({ children }) {
  return (
    <div style={{
      fontSize:10, fontWeight:700, textTransform:"uppercase",
      letterSpacing:".08em", color:"rgba(255,255,255,.3)",
      marginBottom:10,
    }}>{children}</div>
  );
}

// ── Metric tile ───────────────────────────────────────────────────────────────
function Tile({ label, value }) {
  return (
    <div style={{
      background:"rgba(255,255,255,.03)", border:"1px solid rgba(255,255,255,.07)",
      borderRadius:8, padding:"10px 14px",
    }}>
      <div style={{ fontSize:17, fontWeight:700, color:"#f1f5f9", fontFamily:"'DM Mono',monospace", lineHeight:1 }}>{value}</div>
      <div style={{ fontSize:10, color:"rgba(255,255,255,.35)", marginTop:4, textTransform:"uppercase", letterSpacing:".06em" }}>{label}</div>
    </div>
  );
}

// ── Right panel: project detail ───────────────────────────────────────────────
function ProjectDetail({ project, onDelete, onThumbnailUpload, loading }) {
  const thumbInputRef = useRef();

  if (loading) {
    return (
      <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:"100%", color:"rgba(255,255,255,.2)", fontSize:13 }}>
        Loading…
      </div>
    );
  }

  if (!project) {
    return (
      <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"100%", gap:12, color:"rgba(255,255,255,.15)" }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity=".3">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18M9 21V9"/>
        </svg>
        <p style={{ margin:0, fontSize:13 }}>Select a project to view details</p>
      </div>
    );
  }

  const langEntries = Object.entries(project.language_share ?? {}).sort((a, b) => b[1] - a[1]);
  const stack = [...(project.frameworks ?? []), ...(project.skills_used ?? [])];
  const flags = [
    project.has_dockerfile && "Docker",
    project.has_database   && "Database",
    project.has_frontend   && "Frontend",
    project.has_backend    && "Backend",
    project.has_test_files && "Tests",
    project.has_readme     && "README",
  ].filter(Boolean);
  const dateRange = [fmt(project.date_created), fmt(project.last_modified)].filter(Boolean).join(" → ");
  const thumbSrc = project.thumbnail ? thumbnailUrl(project.thumbnail) : null;

  return (
    <div style={{ height:"100%", overflowY:"auto", padding:"28px 32px" }}>

      {/* ── header ── */}
      <div style={{ display:"flex", gap:20, marginBottom:28, alignItems:"flex-start" }}>

        {/* thumbnail — click to change */}
        <div
          className="pj-thumb-wrap"
          onClick={() => thumbInputRef.current?.click()}
          title="Click to change thumbnail"
          style={{ width:96, height:96, borderRadius:12, overflow:"hidden", flexShrink:0, cursor:"pointer", border:"1px solid rgba(255,255,255,.1)", position:"relative" }}
        >
          {thumbSrc
            ? <img src={thumbSrc} alt={project.name} style={{ width:"100%", height:"100%", objectFit:"cover" }}/>
            : <ThumbPlaceholder project={project} size={96}/>
          }
          <div className="pj-thumb-hover">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <input ref={thumbInputRef} type="file" accept="image/*" style={{ display:"none" }}
            onChange={async e => {
              const f = e.target.files?.[0];
              if (f) { e.target.value=""; await onThumbnailUpload(project.id, f); }
            }}
          />
        </div>

        <div style={{ flex:1, minWidth:0 }}>
          <h2 style={{ fontSize:22, fontWeight:700, color:"#f1f5f9", margin:"0 0 8px", lineHeight:1.2 }}>{project.name}</h2>

          <div style={{ display:"flex", flexWrap:"wrap", gap:5, marginBottom:10 }}>
            {project.resume_score > 0 && (
              <span style={{ fontSize:11, fontWeight:700, color:scoreColor(project.resume_score), border:`1px solid ${scoreColor(project.resume_score)}44`, borderRadius:4, padding:"2px 8px" }}>
                ★ {project.resume_score.toFixed(1)}
              </span>
            )}
            <span style={{ fontSize:11, color:"rgba(255,255,255,.4)", border:"1px solid rgba(255,255,255,.1)", borderRadius:4, padding:"2px 8px" }}>
              {project.collaboration_status === "collaborative" ? "👥 team" : "👤 solo"}
            </span>
            {project.project_type && (
              <span style={{ fontSize:11, color:"rgba(255,255,255,.4)", border:"1px solid rgba(255,255,255,.1)", borderRadius:4, padding:"2px 8px" }}>{project.project_type}</span>
            )}
          </div>

          {dateRange && <div style={{ fontSize:12, color:"rgba(255,255,255,.3)", fontFamily:"'DM Mono',monospace", marginBottom:10 }}>{dateRange}</div>}

          <LangBar share={project.language_share} langs={project.languages} height={5} />
        </div>
      </div>

      {/* ── summary ── */}
      {project.summary && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Summary</SLabel>
          <p style={{ fontSize:13, color:"rgba(255,255,255,.65)", lineHeight:1.7, margin:0 }}>{project.summary}</p>
        </div>
      )}

      {/* ── languages ── */}
      {langEntries.length > 0 && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Languages</SLabel>
          <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
            {langEntries.map(([lang, pct]) => (
              <div key={lang} style={{ display:"flex", alignItems:"center", gap:10 }}>
                <span style={{ width:9, height:9, borderRadius:"50%", background:lc(lang), flexShrink:0, display:"inline-block" }}/>
                <span style={{ fontSize:13, color:"rgba(255,255,255,.7)", flex:1 }}>{lang}</span>
                <div style={{ width:120, height:4, borderRadius:99, background:"rgba(255,255,255,.07)", overflow:"hidden" }}>
                  <div style={{ width:`${pct}%`, height:"100%", background:lc(lang), borderRadius:99 }}/>
                </div>
                <span style={{ fontSize:11, color:"rgba(255,255,255,.3)", fontFamily:"'DM Mono',monospace", width:40, textAlign:"right" }}>{pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── resume bullets ── */}
      {project.bullets?.length > 0 && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Resume Bullets</SLabel>
          <ul style={{ margin:0, paddingLeft:18, display:"flex", flexDirection:"column", gap:7 }}>
            {project.bullets.map((b, i) => (
              <li key={i} style={{ fontSize:13, color:"rgba(255,255,255,.65)", lineHeight:1.6 }}>{b}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── stack & skills ── */}
      {stack.length > 0 && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Stack & Skills</SLabel>
          <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
            {stack.map(s => (
              <span key={s} style={{
                fontSize:11, fontWeight:500,
                background:"rgba(255,255,255,.05)", border:"1px solid rgba(255,255,255,.1)",
                borderRadius:5, padding:"3px 9px", color:"rgba(255,255,255,.7)",
              }}>{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── tech flags ── */}
      {flags.length > 0 && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Tech Profile</SLabel>
          <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
            {flags.map(f => (
              <span key={f} style={{
                fontSize:11, fontWeight:500,
                background:"rgba(74,222,128,.06)", border:"1px solid rgba(74,222,128,.2)",
                borderRadius:5, padding:"3px 9px", color:"#4ade80",
              }}>{f}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── metrics ── */}
      {(project.total_loc > 0 || project.num_files > 0) && (
        <div style={{ marginBottom:24 }}>
          <SLabel>Metrics</SLabel>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(110px,1fr))", gap:8 }}>
            {project.total_loc > 0     && <Tile label="Lines"        value={project.total_loc.toLocaleString()} />}
            {project.num_files > 0     && <Tile label="Files"        value={project.num_files} />}
            {project.size_kb > 0       && <Tile label="Size"         value={`${project.size_kb}KB`} />}
            {project.author_count > 0  && <Tile label="Contributors" value={project.author_count} />}
            {project.test_file_ratio > 0 && <Tile label="Test ratio" value={`${(project.test_file_ratio*100).toFixed(0)}%`} />}
            {project.comment_ratio > 0   && <Tile label="Comments"   value={`${(project.comment_ratio*100).toFixed(0)}%`} />}
          </div>
        </div>
      )}

      {/* ── delete ── */}
      <div style={{ marginTop:32, paddingTop:20, borderTop:"1px solid rgba(255,255,255,.06)" }}>
        <button
          onClick={() => onDelete(project.id)}
          style={{
            display:"flex", alignItems:"center", gap:7,
            background:"none", border:"1px solid rgba(248,81,73,.25)",
            borderRadius:7, padding:"7px 14px",
            color:"#f85149", fontSize:12, fontWeight:600,
            cursor:"pointer", fontFamily:"inherit",
            transition:"background .15s, border-color .15s",
          }}
          onMouseOver={e => { e.currentTarget.style.background="rgba(248,81,73,.1)"; e.currentTarget.style.borderColor="#f85149"; }}
          onMouseOut={e => { e.currentTarget.style.background="none"; e.currentTarget.style.borderColor="rgba(248,81,73,.25)"; }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
          Delete project
        </button>
      </div>
    </div>
  );
}

// ── Confirm modal ─────────────────────────────────────────────────────────────
function ConfirmModal({ title, message, confirmLabel, onConfirm, onCancel }) {
  return (
    <div className="pj-overlay">
      <div className="pj-modal">
        <div className="pj-bar"/>
        <div className="pj-confirm-body">
          <div className="pj-confirm-icon">⚠️</div>
          <h2 className="pj-confirm-title">{title}</h2>
          <p className="pj-confirm-sub">{message}</p>
        </div>
        <div className="pj-modal-footer">
          <button className="pj-btn pj-btn--ghost" onClick={onCancel}>← Go back</button>
          <button className="pj-btn pj-btn--ghost pj-btn--danger" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
function Projects() {
  const [loading, setLoading]           = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [uploading, setUploading]       = useState(false);
  const [error, setError]               = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [currentProjects, setCurrentProjects] = useState([]);
  const [previousProjects, setPreviousProjects] = useState([]);
  const [selected, setSelected]         = useState(null);
  const [pendingDuplicates, setPendingDuplicates] = useState([]);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [mergeSelections, setMergeSelections] = useState({});
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  async function loadProjects() {
    setLoading(true); setError(null);
    try {
      const data = await listProjects();
      setCurrentProjects(data.current_projects ?? data.projects ?? []);
      setPreviousProjects(data.previous_projects ?? []);
    } catch(e) { setError(e.message ?? "Failed to load projects"); }
    finally    { setLoading(false); }
  }

  async function handleSelect(id) {
    if (selected?.id === id) { setSelected(null); return; }
    setDetailLoading(true);
    try {
      const data = await getProject(id);
      setSelected(data.project ?? null);
    } catch(e) { setError(e.message ?? "Failed to load project"); }
    finally    { setDetailLoading(false); }
  }

  async function handleFile(file) {
    const consent = await getPrivacyConsent();
    if (!consent) { setError("Grant consent in Settings before uploading."); return; }
    setUploading(true); setError(null);
    setUploadStatus("Uploading and analyzing… this may take a moment.");
    try {
      const res = await uploadProjectZip(file);
      await loadProjects();
      if (res?.projects?.length) await handleSelect(res.projects[0].id);
      if (res?.status === "needs_resolution" && res?.pending_duplicates?.length) {
        setPendingDuplicates(res.pending_duplicates);
        setMergeSelections(buildMergeSelections(res.pending_duplicates));
        setShowMergeModal(true);
        setUploadStatus("Upload complete. Contributor merges need review.");
      } else {
        setUploadStatus(`Done! Loaded ${res?.projects?.length ?? 0} project(s).`);
        setTimeout(() => setUploadStatus(null), 4000);
      }
    } catch(e) { setError(e.message ?? "Upload failed"); setUploadStatus(null); }
    finally    { setUploading(false); }
  }

  async function handleThumbnailUpload(projectId, file) {
    try {
      await uploadThumbnail(projectId, file);
      // Re-fetch the full project — thumbnail path is on the project object
      const data = await getProject(projectId);
      setSelected(data.project ?? null);
    } catch(e) { setError(e.message ?? "Failed to upload thumbnail"); }
  }

  async function handleDelete(id) {
    try { await deleteProject(id); } catch(e) {
      if (e.message && e.message !== "") { setError(e.message); return; }
    }
    setConfirmDeleteId(null);
    setCurrentProjects(prev => prev.filter(p => p.id !== id));
    setPreviousProjects(prev => prev.filter(p => p.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  function buildMergeSelections(pending) {
    const sel = {};
    for (const p of pending ?? [])
      for (const g of p.duplicate_groups ?? [])
        sel[`${p.project_id}::${g.suggested_canonical}`] = g.suggested_canonical;
    return sel;
  }

  async function handleApplyMerges() {
    try {
      setUploading(true); setError(null);
      await resolveContributorsBatch(pendingDuplicates, mergeSelections);
      await loadProjects();
      const fid = pendingDuplicates[0]?.project_id;
      if (fid) await handleSelect(fid);
      setPendingDuplicates([]); setMergeSelections({});
      setShowMergeModal(false); setConfirmCancel(false);
      setUploadStatus("Contributor merges applied.");
      setTimeout(() => setUploadStatus(null), 4000);
    } catch(e) { setError(e.message ?? "Failed to apply merges"); }
    finally    { setUploading(false); }
  }

  async function handleCancelAnalysis() {
    try { await Promise.all(pendingDuplicates.map(p => deleteProject(p.project_id))); await loadProjects(); }
    catch(e) { setError(e.message ?? "Failed to cancel"); }
    finally {
      setShowMergeModal(false); setConfirmCancel(false);
      setPendingDuplicates([]); setMergeSelections({});
      setUploadStatus(null); setSelected(null);
    }
  }

  useEffect(() => { loadProjects(); }, []);

  const hasPrevious = previousProjects.length > 0;

  return (
    <>
      <style>{CSS}</style>

      <div style={{ display:"flex", gap:0, minHeight:"calc(100vh - 60px)", fontFamily:"'DM Sans','Segoe UI',system-ui,sans-serif" }}>

        {/* ── FULL PAGE UPLOAD (no projects yet) ── */}
        {currentProjects.length === 0 && previousProjects.length === 0 && (
          <div style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:40 }}>
            <UploadZone onFile={handleFile} uploading={uploading} uploadStatus={uploadStatus} error={error} hasProjects={false}/>
          </div>
        )}

        {/* ── NORMAL LAYOUT (has projects) ── */}
        {(currentProjects.length > 0 || previousProjects.length > 0) && (<>

        {/* ── LEFT PANEL ── */}
        <div style={{ width:340, flexShrink:0, borderRight:"1px solid rgba(255,255,255,.07)", display:"flex", flexDirection:"column", padding:"24px 16px", gap:8, overflowY:"auto" }}>

          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:8 }}>
            <h2 style={{ fontSize:18, fontWeight:700, margin:0, color:"#f1f5f9", letterSpacing:"-.3px" }}>Projects</h2>
          </div>

          <UploadZone onFile={handleFile} uploading={uploading} uploadStatus={uploadStatus} error={error}
            hasProjects={currentProjects.length > 0 || previousProjects.length > 0}/>

          {currentProjects.length > 0 && (
            <div>
              <div className="pj-group-label">
                <span className="pj-dot pj-dot--green"/>
                Recent Uploads
                <span className="pj-count">{currentProjects.length}</span>
              </div>
              {currentProjects.map(p => (
                <ProjectItem key={p.id} project={p}
                  isSelected={selected?.id === p.id}
                  onClick={() => handleSelect(p.id)}
                  onDelete={id => setConfirmDeleteId(id)}/>
              ))}
            </div>
          )}

          {hasPrevious && (
            <div style={{ marginTop:8 }}>
              <div className="pj-group-label pj-group-label--dim">
                <span className="pj-dot"/>
                Previous
                <span className="pj-count">{previousProjects.length}</span>
              </div>
              {previousProjects.map(p => (
                <ProjectItem key={p.id} project={p}
                  isSelected={selected?.id === p.id}
                  onClick={() => handleSelect(p.id)}
                  onDelete={id => setConfirmDeleteId(id)}/>
              ))}
            </div>
          )}

          {!loading && currentProjects.length === 0 && previousProjects.length === 0 && !uploading && (
            <div style={{ flex:1 }}/>
          )}
        </div>

        {/* ── RIGHT PANEL ── */}
        <div style={{ flex:1, minWidth:0 }}>
          <ProjectDetail
            project={selected}
            loading={detailLoading}
            onDelete={id => setConfirmDeleteId(id)}
            onThumbnailUpload={handleThumbnailUpload}
          />
        </div>
        </>)}
      </div>

      {/* delete confirm */}
      {confirmDeleteId && (
        <ConfirmModal
          title="Delete project?"
          message="This will permanently remove the project and all its analysis data. This cannot be undone."
          confirmLabel="Yes, delete"
          onConfirm={() => handleDelete(confirmDeleteId)}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}

      {/* merge modal */}
      {showMergeModal && (
        <div className="pj-overlay">
          <div className="pj-modal">
            <div className="pj-bar" aria-hidden="true"/>
            {confirmCancel ? (
              <>
                <div className="pj-confirm-body">
                  <div className="pj-confirm-icon">⚠️</div>
                  <h2 className="pj-confirm-title">Cancel analysis?</h2>
                  <p className="pj-confirm-sub">
                    This will delete the {pendingDuplicates.length === 1 ? "project" : `${pendingDuplicates.length} projects`} that were just uploaded. This cannot be undone.
                  </p>
                </div>
                <div className="pj-modal-footer">
                  <button className="pj-btn pj-btn--ghost" disabled={uploading} onClick={() => setConfirmCancel(false)}>← Go back</button>
                  <button className="pj-btn pj-btn--ghost pj-btn--danger" disabled={uploading} onClick={handleCancelAnalysis}>
                    {uploading ? "Cancelling…" : "Yes, cancel analysis"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="pj-modal-header">
                  <h2 className="pj-modal-title">Resolve duplicate contributors</h2>
                  <p className="pj-modal-sub">These contributors appear to be the same person using different emails. Choose which identity to keep.</p>
                </div>
                <div className="pj-modal-body">
                  {pendingDuplicates.map(proj => (
                    <div key={proj.project_id} className="pj-project-group">
                      <p className="pj-project-label">{proj.project_name}</p>
                      {(proj.duplicate_groups ?? []).map(g => {
                        const key = `${proj.project_id}::${g.suggested_canonical}`;
                        return (
                          <div key={key} className="pj-dup-group">
                            <p className="pj-dup-name">{g.display_name}</p>
                            <div className="pj-candidates">{g.candidates.map(c => <span key={c} className="pj-candidate">{c}</span>)}</div>
                            <label className="pj-keep-label">
                              <span className="pj-keep-text">Keep as</span>
                              <select className="pj-select" value={mergeSelections[key] || g.suggested_canonical}
                                onChange={e => setMergeSelections(prev => ({ ...prev, [key]: e.target.value }))}>
                                {g.candidates.map(c => <option key={c} value={c}>{c}</option>)}
                              </select>
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
                <div className="pj-modal-footer">
                  <button className="pj-btn pj-btn--ghost pj-btn--danger" disabled={uploading} onClick={() => setConfirmCancel(true)}>Cancel Analysis</button>
                  <button className="pj-btn pj-btn--primary" disabled={uploading} onClick={handleApplyMerges}>
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

// ── CSS ───────────────────────────────────────────────────────────────────────
const CSS = `
  @keyframes pj-spin { to { transform: rotate(360deg); } }

  /* icon button */
  .pj-icon-btn {
    background: none; border: 1px solid rgba(255,255,255,.1);
    border-radius: 6px; color: rgba(255,255,255,.3);
    cursor: pointer; padding: 6px 8px; display: flex; align-items: center;
    transition: border-color .15s, color .15s;
  }
  .pj-icon-btn:hover { border-color: rgba(255,255,255,.25); color: rgba(255,255,255,.7); }

  /* upload drop */
  .pj-drop {
    border: 1.5px dashed rgba(255,255,255,.1); border-radius: 9px;
    padding: 16px 12px; display: flex; align-items: center; gap: 10px;
    cursor: pointer; transition: border-color .15s, background .15s;
    margin-bottom: 8px; background: rgba(255,255,255,.02);
    color: rgba(255,255,255,.35); user-select: none;
  }
  .pj-drop:hover, .pj-drop--over {
    border-color: rgba(88,166,255,.5); background: rgba(88,166,255,.04); color: rgba(255,255,255,.65);
  }
  .pj-drop--busy { cursor: default; pointer-events: none; }
  .pj-drop--big {
    flex-direction: column; justify-content: center; align-items: center;
    padding: 64px 40px; gap: 16px;
    width: 100%; max-width: 480px;
    border-radius: 16px;
  }
  .pj-drop-label { font-size: 12px; }
  .pj-spinner {
    width: 18px; height: 18px; flex-shrink: 0;
    border: 2px solid rgba(255,255,255,.1); border-top-color: #58a6ff;
    border-radius: 50%; animation: pj-spin .7s linear infinite;
  }

  /* group label */
  .pj-group-label {
    display: flex; align-items: center; gap: 6px;
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: rgba(255,255,255,.25);
    margin: 4px 0 6px; padding: 0 4px;
  }
  .pj-group-label--dim { opacity: .55; }
  .pj-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: rgba(255,255,255,.2); flex-shrink: 0;
  }
  .pj-dot--green { background: #4ade80; }
  .pj-count {
    margin-left: auto; font-size: 10px; font-weight: 600;
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.08);
    border-radius: 9px; padding: 0 6px; color: rgba(255,255,255,.25);
  }

  /* project list item */
  .pj-item {
    display: flex; align-items: center;
    border-radius: 7px;
    transition: background .12s;
  }
  .pj-item:hover { background: rgba(255,255,255,.04); }
  .pj-item--active { background: rgba(255,255,255,.06) !important; }
  .pj-item-accent {
    width: 3px; height: 32px; border-radius: 99px;
    flex-shrink: 0;
  }
  .pj-item-name {
    font-size: 15px; font-weight: 500;
    color: rgba(255,255,255,.5);
    overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
    line-height: 1.2;
    transition: color .12s;
  }
  .pj-item:hover .pj-item-name { color: rgba(255,255,255,.8); }
  .pj-item--active .pj-item-name { color: #f1f5f9; font-weight: 600; }
  .pj-item-lang { font-size: 12px; color: rgba(255,255,255,.2); margin-top: 2px; }
  .pj-item-score {
    font-size: 13px; font-weight: 700;
    font-family: 'DM Mono', monospace;
    flex-shrink: 0;
    opacity: .5;
  }
  .pj-item--active .pj-item-score { opacity: 1; }
  .pj-item-trash {
    background: none; border: none; cursor: pointer;
    color: rgba(255,255,255,.2); padding: 8px 12px 8px 4px;
    display: flex; align-items: center; flex-shrink: 0;
    border-radius: 5px; transition: color .15s;
    opacity: 0; line-height: 1;
  }
  .pj-item:hover .pj-item-trash { opacity: 1; }
  .pj-item-trash:hover { color: #f85149 !important; }
  .pj-item-inner-btn {
    display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0;
    background: none; border: none; cursor: pointer;
    padding: 10px 4px 10px 10px; text-align: left;
    color: inherit; font-family: inherit;
  }

  /* thumbnail hover overlay */
  .pj-thumb-wrap:hover .pj-thumb-hover { opacity: 1 !important; }
  .pj-thumb-hover {
    position: absolute; inset: 0;
    background: rgba(0,0,0,.6);
    display: flex; align-items: center; justify-content: center;
    opacity: 0; transition: opacity .15s; color: #fff;
    border-radius: inherit;
  }

  /* modal (unchanged) */
  .pj-overlay { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.65); display: flex; align-items: center; justify-content: center; }
  .pj-modal { --accent:#58a6ff;--accent2:#f78166;--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--r:10px; width:min(620px,92vw);max-height:80vh;background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.6);font-family:'DM Sans','Segoe UI',system-ui,sans-serif; }
  .pj-bar { height:3px;flex-shrink:0;background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent));background-size:200% 100%;animation:pj-shimmer 3s linear infinite; }
  @keyframes pj-shimmer { 0%{background-position:200% center}100%{background-position:-200% center} }
  .pj-modal-header { padding:20px 24px 16px;flex-shrink:0;border-bottom:1px solid var(--border); }
  .pj-modal-title { font-size:17px;font-weight:700;margin:0 0 6px;color:var(--text); }
  .pj-modal-sub { font-size:13px;color:var(--muted);line-height:1.6;margin:0; }
  .pj-modal-body { padding:16px 24px;overflow-y:auto;flex:1; }
  .pj-project-group { margin-bottom:20px; }
  .pj-project-label { font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 10px; }
  .pj-dup-group { margin-bottom:10px;padding:14px 16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--r); }
  .pj-dup-name { font-size:14px;font-weight:600;color:var(--text);margin:0 0 8px; }
  .pj-candidates { display:flex;flex-direction:column;gap:3px;margin-bottom:12px; }
  .pj-candidate { font-size:12px;color:var(--muted); }
  .pj-keep-label { display:flex;align-items:center;gap:8px; }
  .pj-keep-text { font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);white-space:nowrap; }
  .pj-select { flex:1;height:36px;padding:0 10px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);color:var(--text);font-size:12px;outline:none;cursor:pointer;transition:border-color .15s; }
  .pj-select:focus { border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,166,255,.15); }
  .pj-modal-footer { padding:14px 24px;flex-shrink:0;border-top:1px solid var(--border);display:flex;justify-content:flex-end;align-items:center;gap:8px; }
  .pj-confirm-body { flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px 32px 32px;text-align:center; }
  .pj-confirm-icon { font-size:40px;margin-bottom:16px; }
  .pj-confirm-title { font-size:20px;font-weight:700;color:var(--text);margin:0 0 12px; }
  .pj-confirm-sub { font-size:14px;color:var(--muted);line-height:1.6;max-width:380px;margin:0; }
  .pj-btn { display:inline-flex;align-items:center;justify-content:center;height:38px !important;padding:0 18px;border-radius:var(--r);font-size:14px;font-weight:600;cursor:pointer;border:1.5px solid transparent;font-family:inherit;transition:all .15s;transform:none; }
  .pj-btn--primary { background:var(--accent) !important;color:#0d1117 !important;border-color:var(--accent); }
  .pj-btn--primary:hover:not(:disabled) { background:#79c0ff !important;box-shadow:0 0 14px rgba(88,166,255,.35);transform:translateY(-1px); }
  .pj-btn--primary:disabled { opacity:.5;cursor:not-allowed; }
  .pj-btn--ghost { background:transparent !important;color:var(--muted) !important;border-color:var(--border); }
  .pj-btn--ghost:hover:not(:disabled) { border-color:var(--muted);color:var(--text) !important; }
  .pj-modal .pj-btn--danger { background:transparent !important;color:#f85149 !important;border-color:#f85149; }
  .pj-modal .pj-btn--danger:hover:not(:disabled) { border-color:#ff7b72;color:#ff7b72 !important; }
`;
