import { useState, useEffect } from "react";
import { getConfig, saveConfig, setPrivacyConsent, getPrivacyConsent, clearProjects } from "./api/client";

export default function Settings() {
  const [tab, setTab] = useState("profile");

  const [form, setForm] = useState({ name: "", email: "", phone: "", github: "", linkedin: "" });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [touched, setTouched] = useState({});
  const [errors, setErrors] = useState({});

  const [consent, setConsent] = useState(false);
  const [consentSaving, setConsentSaving] = useState(false);

  const [clearState, setClearState] = useState("idle");

  useEffect(() => {
    getConfig().then((cfg) => {
      if (!cfg) return;
      setForm({
        name:     cfg.name     ? String(cfg.name)     : "",
        email:    cfg.email    ? String(cfg.email)    : "",
        phone:    cfg.phone    ? String(cfg.phone)    : "",
        github:   cfg.github   ? String(cfg.github)   : "",
        linkedin: cfg.linkedin ? String(cfg.linkedin) : "",
      });
    }).catch(() => {});

    getPrivacyConsent().then(setConsent).catch(() => {});
  }, []);

  function change(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      setTouched((t) => ({ ...t, [field]: true }));
      if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }));
    };
  }

  function validate() {
    const errs = {};
    if (!form.name.trim())  errs.name  = "Full name is required.";
    if (!form.email.trim()) errs.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errs.email = "Enter a valid email.";
    if (!form.phone.trim()) errs.phone = "Phone is required.";
    return errs;
  }

  async function handleSaveProfile() {
    const errs = validate();
    setErrors(errs);
    setTouched({ name: true, email: true, phone: true });
    if (Object.keys(errs).length) return;
    setSaving(true);
    setSaveMsg("");
    try {
      await saveConfig({
        name:     form.name.trim(),
        email:    form.email.trim(),
        phone:    form.phone.trim(),
        github:   form.github.trim()   || undefined,
        linkedin: form.linkedin.trim() || undefined,
      });
      setSaveMsg("Saved.");
    } catch (e) {
      setSaveMsg(e?.message ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleConsent() {
    setConsentSaving(true);
    try {
      const next = !consent;
      await setPrivacyConsent(next);
      setConsent(next);
    } catch {}
    finally { setConsentSaving(false); }
  }

  async function handleClearProjects() {
    if (clearState === "idle")    { setClearState("confirm"); return; }
    if (clearState === "confirm") {
      setClearState("clearing");
      try {
        await clearProjects();
        setClearState("done");
        setTimeout(() => setClearState("idle"), 3000);
      } catch {
        setClearState("idle");
      }
    }
  }

  const inputStyle = {
    width: "100%",
    fontSize: "15px",
    padding: "6px 8px",
    boxSizing: "border-box",
    marginTop: 4,
    display: "block",
  };

  const labelStyle = {
    fontSize: "13px",
    fontWeight: "600",
    display: "block",
    marginTop: 12,
  };

  const errorStyle = {
    color: "red",
    fontSize: "12px",
    marginTop: 2,
    display: "block",
  };

  return (
    <>
      <style>{`
        .s-nav-btn {
          border-radius:var(--r);
          border:1px solid var(--border);

          background:transparent;
          color:var(--muted);

          font-weight:600;
          font-size:14px;

          cursor:pointer;

          transition:all .15s;
        }
        .s-nav-btn--off {
          background: var(--primary);
          color: var(--secondary);
        }
        .s-nav-btn--off:hover {
          background: var(--primary_high);
          color: var(--secondary);
        }
        .s-nav-btn--on {
          background: var(--secondary);
          color: var(--primary);
          cursor: default;
        }
          .nav-btn:hover{
          border-color:var(--muted);
          color:var(--text);
        }

        .s-btn {
          padding: 6px 16px;
          font-size: 14px;
          font-weight: bold;
          font-family: inherit;
          aspect-ratio: unset;
          border-radius: 0;
          cursor: pointer;
          background: var(--primary);
          color: var(--secondary);
          border: 2px solid var(--primary);
          box-sizing: border-box;
        }
        .s-btn:hover:not(:disabled) {
          background: var(--primary_desat);
          border-color: var(--primary_desat);
        }
        .s-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .s-btn--danger {
          background: transparent;
          color: #f85149;
          border: 1px solid rgba(248,81,73,0.35);
          border-radius: 0;
          padding: 6px 16px;
          font-size: 14px;
          font-weight: bold;
          font-family: inherit;
          cursor: pointer;
        }
        .s-btn--danger:hover:not(:disabled) {
          background: rgba(248,81,73,0.08);
          border-color: #f85149;
        }
        .s-btn--danger:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }
      `}</style>

      <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", width: 120, flexShrink: 0, gap: 10, marginTop: 30, background: "var(--surface)"}}>
          {[["profile","Profile"],["privacy","Privacy"],["data","Data"]].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`s-nav-btn ${tab === id ? "s-nav-btn--on" : "s-nav-btn--off"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: "24px 32px", flex: 1, overflowY: "auto", fontSize: "15px" }}>

          {/* ── Profile ── */}
          {tab === "profile" && (
            <div style={{ maxWidth: 500 }}>
              <h3 style={{ marginTop: 0, marginBottom: 4 }}>Profile</h3>
              <p style={{ marginTop: 0, opacity: 0.7, fontSize: "13px" }}>
                These details will appear on your resume and portfolio exports.
              </p>
              <hr style={{ marginBottom: 16 }} />

              <div style={{ display: "flex", gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Full Name *</label>
                  <input style={{ ...inputStyle, minWidth: 240 }} value={form.name} onChange={change("name")} placeholder="Ada Lovelace" />
                  {touched.name && errors.name && <span style={errorStyle}>{errors.name}</span>}
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Email *</label>
                  <input style={{ ...inputStyle, minWidth: 300 }} type="email" value={form.email} onChange={change("email")} placeholder="ada@lovelace.dev" />
                  {touched.email && errors.email && <span style={errorStyle}>{errors.email}</span>}
                </div>
              </div>

              <div style={{ display: "flex", gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Phone *</label>
                  <input style={{ ...inputStyle, minWidth: 240 }} type="tel" value={form.phone} onChange={change("phone")} placeholder="+1 (555) 867-5309" />
                  {touched.phone && errors.phone && <span style={errorStyle}>{errors.phone}</span>}
                </div>
                <div style={{ flex: 1 }} />
              </div>

              <p style={{ fontSize: "12px", opacity: 0.5, margin: "16px 0 0" }}>Online presence (optional)</p>
              <hr style={{ marginBottom: 0 }} />

              <div style={{ display: "flex", gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>GitHub</label>
                  <input style={{ ...inputStyle, minWidth: 240 }} value={form.github} onChange={change("github")} placeholder="ada-lovelace" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>LinkedIn</label>
                  <input style={{ ...inputStyle, minWidth: 300 }} value={form.linkedin} onChange={change("linkedin")} placeholder="ada-lovelace" />
                </div>
              </div>

              <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 12 }}>
                <button className="s-btn" onClick={handleSaveProfile} disabled={saving} style={{ minWidth: 120 }}>
                  {saving ? "Saving…" : "Save changes"}
                </button>
                {saveMsg && <span style={{ fontSize: "13px", opacity: 0.8 }}>{saveMsg}</span>}
              </div>
            </div>
          )}

          {/* ── Privacy ── */}
          {tab === "privacy" && (
            <div style={{ maxWidth: 500 }}>
              <h3 style={{ marginTop: 0, marginBottom: 4 }}>Privacy</h3>
              <p style={{ marginTop: 0, opacity: 0.7, fontSize: "13px" }}>
                Consent is required to generate reports and export resumes and portfolios. 
                Data is only ever stored locally.
              </p>
              <hr />

              <p>Status: <strong>{consent ? "Consent granted" : "Consent not granted"}</strong></p>
              <p style={{ fontSize: "13px", opacity: 0.7 }}>
                Enables: generating PDFs, exporting resumes, exporting portfolios, saving reports.
              </p>

              <button className="s-btn" onClick={handleToggleConsent} disabled={consentSaving} style={{ minWidth: 140 }}>
                {consentSaving ? "Updating…" : consent ? "Revoke consent" : "Grant consent"}
              </button>
            </div>
          )}

          {/* ── Data ── */}
          {tab === "data" && (
            <div style={{ maxWidth: 500 }}>
              <h3 style={{ marginTop: 0, marginBottom: 4 }}>Data</h3>
              <p style={{ marginTop: 0, opacity: 0.7, fontSize: "13px" }}>
                Irreversible actions affecting stored project data.
              </p>
              <hr />

              <p><strong>Clear all projects</strong></p>
              <p style={{ fontSize: "13px", opacity: 0.7 }}>
                Permanently removes all uploaded projects and analysis data. 
              </p>

              {clearState === "done" && <p>✓ All projects cleared.</p>}

              {clearState !== "done" && (
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  {clearState === "confirm" && (
                    <span style={{ color: "#f85149", fontSize: "13px", width: "100%" }}>
                      ⚠ This cannot be undone. Are you sure?
                    </span>
                  )}
                  <button
                    className="s-btn--danger"
                    onClick={handleClearProjects}
                    disabled={clearState === "clearing"}
                    style={{ minWidth: 160 }}
                  >
                    {clearState === "clearing" ? "Clearing…"
                      : clearState === "confirm"  ? "Yes, delete everything"
                      : "Clear all projects"}
                  </button>
                  {clearState === "confirm" && (
                    <button className="s-btn" onClick={() => setClearState("idle")} style={{ minWidth: 80 }}>
                      Cancel
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </>
  );
}
