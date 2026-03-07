import { useState, useEffect } from "react";
import { getConfig, saveConfig, setPrivacyConsent, getPrivacyConsent, clearProjects } from "./api/client";

export default function Settings() {
  const [tab, setTab] = useState("profile");

  // Profile
  const [form, setForm] = useState({ name: "", email: "", phone: "", github: "", linkedin: "" });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [touched, setTouched] = useState({});
  const [errors, setErrors] = useState({});

  // Consent
  const [consent, setConsent] = useState(false);
  const [consentSaving, setConsentSaving] = useState(false);

  // Clear
  const [clearState, setClearState] = useState("idle"); // idle | confirm | clearing | done

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

  return (
    <div style={{ display: "flex", height: "100%" }}>

      {/* Sidebar */}
      <div className="stacked-buttons" style={{ width: "fit-content" }}>
        {[["profile","Profile"],["privacy","Privacy"],["data","Data"]].map(([id, label]) => (
          <button
            key={id}
            className={tab === id ? "button-on" : "button-off"}
            onClick={() => setTab(id)}
            style={{ minWidth: 100 }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: "20px 24px", flex: 1, overflowY: "auto" }}>

        {/* ── Profile ── */}
        {tab === "profile" && (
          <div>
            <h3>Profile</h3>
            <p>These details appear on your resume and portfolio exports.</p>
            <hr />

            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 480 }}>
              <label>
                Full name *<br />
                <input value={form.name} onChange={change("name")} placeholder="Ada Lovelace" />
                {touched.name && errors.name && <span style={{ color: "red" }}> {errors.name}</span>}
              </label>
              <label>
                Email *<br />
                <input type="email" value={form.email} onChange={change("email")} placeholder="ada@lovelace.dev" />
                {touched.email && errors.email && <span style={{ color: "red" }}> {errors.email}</span>}
              </label>
              <label>
                Phone *<br />
                <input type="tel" value={form.phone} onChange={change("phone")} placeholder="+1 (555) 867-5309" />
                {touched.phone && errors.phone && <span style={{ color: "red" }}> {errors.phone}</span>}
              </label>
              <label>
                GitHub (optional)<br />
                <input value={form.github} onChange={change("github")} placeholder="ada-lovelace" />
              </label>
              <label>
                LinkedIn (optional)<br />
                <input value={form.linkedin} onChange={change("linkedin")} placeholder="ada-lovelace" />
              </label>
            </div>

            <br />
            <button className="button-off" onClick={handleSaveProfile} disabled={saving}
              style={{ minWidth: 120, aspectRatio: "unset", padding: "6px 16px" }}>
              {saving ? "Saving…" : "Save changes"}
            </button>
            {saveMsg && <span style={{ marginLeft: 12 }}>{saveMsg}</span>}
          </div>
        )}

        {/* ── Privacy ── */}
        {tab === "privacy" && (
          <div>
            <h3>Privacy</h3>
            <p>Consent is required to generate reports and export resumes/portfolios. Data is stored locally only.</p>
            <hr />

            <p>Status: <strong>{consent ? "Consent granted" : "Consent not granted"}</strong></p>
            <p>Enables: generating PDFs, exporting resumes, exporting portfolios, saving reports.</p>

            <button className="button-off" onClick={handleToggleConsent} disabled={consentSaving}
              style={{ minWidth: 140, aspectRatio: "unset", padding: "6px 16px" }}>
              {consentSaving ? "Updating…" : consent ? "Revoke consent" : "Grant consent"}
            </button>

            <p><small>Revoking consent does not delete already-exported files.</small></p>
          </div>
        )}

        {/* ── Data ── */}
        {tab === "data" && (
          <div>
            <h3>Data</h3>
            <p>Irreversible actions affecting stored project data.</p>
            <hr />

            <p><strong>Clear all projects</strong></p>
            <p>Permanently removes all uploaded projects and analysis data. Existing reports will have no linked data.</p>

            {clearState === "done" && <p>✓ All projects cleared.</p>}

            {clearState !== "done" && (
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {clearState === "confirm" && <span style={{ color: "red" }}>⚠ This cannot be undone. Are you sure?</span>}
                <button className="button-off" onClick={handleClearProjects} disabled={clearState === "clearing"}
                  style={{ minWidth: 160, aspectRatio: "unset", padding: "6px 16px" }}>
                  {clearState === "clearing" ? "Clearing…"
                    : clearState === "confirm"  ? "Yes, delete everything"
                    : "Clear all projects"}
                </button>
                {clearState === "confirm" && (
                  <button className="button-off" onClick={() => setClearState("idle")}
                    style={{ minWidth: 80, aspectRatio: "unset", padding: "6px 16px" }}>
                    Cancel
                  </button>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
