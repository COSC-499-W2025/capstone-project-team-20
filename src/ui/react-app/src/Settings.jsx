import { useState, useEffect } from "react";
import { getConfig, saveConfig, setPrivacyConsent, clearProjects } from "./api/client";

export default function Settings() {
  const [activeSection, setActiveSection] = useState("profile");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [saveMsg, setSaveMsg] = useState("");
  const [consent, setConsent] = useState(false);
  const [consentSaving, setConsentSaving] = useState(false);
  const [clearState, setClearState] = useState("idle");
  const [touched, setTouched] = useState({});
  const [errors, setErrors] = useState({});

  const [form, setForm] = useState({
    name: "", email: "", phone: "", github: "", linkedin: "",
  });

  useEffect(() => {
    getConfig().then((cfg) => {
      if (!cfg) return;
      setForm({
        name:     cfg.name     ?? "",
        email:    cfg.email    ?? "",
        phone:    cfg.phone    ?? "",
        github:   cfg.github   ?? "",
        linkedin: cfg.linkedin ?? "",
      });
    }).catch(() => {});
  }, []);

  function change(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      setTouched((t) => ({ ...t, [field]: true }));
      if (errors[field]) setErrors((e) => ({ ...e, [field]: null }));
    };
  }

  function validate() {
    const errs = {};
    if (!form.name.trim())  errs.name  = "Full name is required.";
    if (!form.email.trim()) errs.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errs.email = "Enter a valid email address.";
    if (!form.phone.trim()) errs.phone = "Phone number is required.";
    return errs;
  }

  async function handleSaveProfile() {
    const errs = validate();
    setErrors(errs);
    setTouched({ name: true, email: true, phone: true });
    if (Object.keys(errs).length) return;

    setSaving(true);
    setSaveStatus(null);
    try {
      await saveConfig({
        name:     form.name.trim(),
        email:    form.email.trim(),
        phone:    form.phone.trim(),
        github:   form.github.trim()   || undefined,
        linkedin: form.linkedin.trim() || undefined,
      });
      setSaveStatus("success");
      setSaveMsg("Profile saved.");
    } catch (e) {
      setSaveStatus("error");
      setSaveMsg(e?.message ?? "Failed to save profile.");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(null), 3500);
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
    if (clearState === "idle") { setClearState("confirm"); return; }
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

  const nav = [
    { id: "profile", label: "Profile" },
    { id: "privacy", label: "Privacy" },
    { id: "danger",  label: "Data" },
  ];

  return (
    <>
      <style>{CSS}</style>
      <div className="st-root">

        {/* ── Sidebar nav ── */}
        <nav className="st-nav" aria-label="Settings sections">
          <div className="st-nav-header">Settings</div>
          {nav.map((n) => (
            <button
              key={n.id}
              className={"st-nav-item" + (activeSection === n.id ? " st-nav-item--active" : "")}
              onClick={() => setActiveSection(n.id)}
              aria-current={activeSection === n.id ? "page" : undefined}
            >
              {n.label}
            </button>
          ))}
        </nav>

        {/* ── Main panel ── */}
        <main className="st-main">

          {/* ── Profile section ── */}
          {activeSection === "profile" && (
            <section className="st-section st-fade" key="profile">
              <h2 className="st-h2">Profile</h2>
              <p className="st-sub">These details appear on your resume and portfolio exports.</p>
              <div className="st-divider" />

              <div className="st-form">
                <div className="st-form-row">
                  <Field id="name" label="Full name" type="text" placeholder="Ada Lovelace"
                    value={form.name} onChange={change("name")}
                    error={touched.name && errors.name} required />
                  <Field id="email" label="Email" type="email" placeholder="ada@lovelace.dev"
                    value={form.email} onChange={change("email")}
                    error={touched.email && errors.email} required />
                </div>
                <div className="st-form-row">
                  <Field id="phone" label="Phone" type="tel" placeholder="+1 (555) 867-5309"
                    value={form.phone} onChange={change("phone")}
                    error={touched.phone && errors.phone} required />
                  <div className="st-field-spacer" />
                </div>

                <p className="st-sub-label">Online presence <span className="st-optional">(optional)</span></p>

                <div className="st-form-row">
                  <Field id="github" label="GitHub" type="text" placeholder="ada-lovelace"
                    prefix="github.com/" value={form.github} onChange={change("github")} />
                  <Field id="linkedin" label="LinkedIn" type="text" placeholder="ada-lovelace"
                    prefix="linkedin.com/in/" value={form.linkedin} onChange={change("linkedin")} />
                </div>
              </div>

              {saveStatus === "success" && (
                <div className="st-alert st-alert--success" role="status">✓ {saveMsg}</div>
              )}
              {saveStatus === "error" && (
                <div className="st-alert st-alert--error" role="alert">⚠ {saveMsg}</div>
              )}

              <div className="st-actions">
                <button className="st-btn st-btn--primary" onClick={handleSaveProfile} disabled={saving}>
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </div>
            </section>
          )}

          {/* ── Privacy section ── */}
          {activeSection === "privacy" && (
            <section className="st-section st-fade" key="privacy">
              <h2 className="st-h2">Privacy</h2>
              <p className="st-sub">Control how your data is used for report generation and exports.</p>
              <div className="st-divider" />

              <div className="st-consent-card">
                <p className="st-consent-title">Data processing consent</p>
                <p className="st-consent-desc">
                  Required to generate reports, export resumes, and export portfolios.
                  Your data is stored locally and never sent to a third party.
                </p>
                <ul className="st-consent-list">
                  {[
                    "Generate and export resume PDFs",
                    "Generate and export portfolio PDFs",
                    "Create and manage saved reports",
                  ].map((item) => (
                    <li key={item} className="st-consent-list-item">— {item}</li>
                  ))}
                </ul>

                <div className="st-toggle-row">
                  <span className="st-toggle-label">
                    {consent ? "Consent granted" : "Consent not granted"}
                  </span>
                  <button
                    className={"st-toggle" + (consent ? " st-toggle--on" : "")}
                    onClick={handleToggleConsent}
                    disabled={consentSaving}
                    aria-pressed={consent}
                    aria-label="Toggle data processing consent"
                  >
                    <span className="st-toggle-thumb" />
                  </button>
                </div>
              </div>

              <p className="st-info-note">
                You can revoke consent at any time. Revoking will not delete existing exported files.
              </p>
            </section>
          )}

          {/* ── Data section ── */}
          {activeSection === "danger" && (
            <section className="st-section st-fade" key="danger">
              <h2 className="st-h2">Data</h2>
              <p className="st-sub">Irreversible actions that affect your stored project data.</p>
              <div className="st-divider" />

              <div className="st-danger-card">
                <p className="st-danger-title">Clear all projects</p>
                <p className="st-danger-desc">
                  Permanently removes all uploaded projects and their analysis data from the database.
                  Reports that reference those projects will still exist but will have no linked data.
                </p>

                <div className="st-danger-action">
                  {clearState === "done" ? (
                    <div className="st-alert st-alert--success" role="status" style={{ marginBottom: 0 }}>
                      ✓ All projects cleared.
                    </div>
                  ) : (
                    <>
                      {clearState === "confirm" && (
                        <p className="st-confirm-warning" role="alert">
                          ⚠ This cannot be undone. Are you sure?
                        </p>
                      )}
                      <button
                        className={"st-btn st-btn--danger" + (clearState === "confirm" ? " st-btn--danger-confirm" : "")}
                        onClick={handleClearProjects}
                        disabled={clearState === "clearing"}
                      >
                        {clearState === "clearing" ? "Clearing…"
                          : clearState === "confirm" ? "Yes, delete everything"
                          : "Clear all projects"}
                      </button>
                      {clearState === "confirm" && (
                        <button className="st-btn st-btn--ghost" onClick={() => setClearState("idle")}>
                          Cancel
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </section>
          )}
        </main>
      </div>
    </>
  );
}

// ── Field component ───────────────────────────────────────────────────────────

function Field({ id, label, type, placeholder, value, onChange, error, required, prefix }) {
  return (
    <div className={"st-field" + (error ? " st-field--err" : "")}>
      <label className="st-label" htmlFor={id}>
        {label}{required && <span className="st-req"> *</span>}
      </label>
      <div className={"st-input-row" + (prefix ? " st-input-row--prefix" : "")}>
        {prefix && <span className="st-prefix">{prefix}</span>}
        <input
          id={id} type={type} placeholder={placeholder}
          value={value} onChange={onChange}
          className="st-input"
          aria-required={required}
          aria-invalid={!!error}
          aria-describedby={error ? id + "-err" : undefined}
        />
      </div>
      {error && <p className="st-field-err" id={id + "-err"} role="alert">{error}</p>}
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const CSS = `
.st-root *, .st-root *::before, .st-root *::after { box-sizing: border-box; margin: 0; padding: 0; }

.st-root {
  display: flex;
  height: 100%;
  min-height: 0;
  color: var(--primary_desat);
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  overflow: hidden;
}

/* ── Sidebar ── */
.st-nav {
  width: 150px;
  flex-shrink: 0;
  background: var(--secondary_low);
  border-right: 2px solid var(--secondary);
  display: flex;
  flex-direction: column;
  padding: 14px 8px;
  gap: 3px;
}

.st-nav-header {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: var(--primary_desat);
  padding: 2px 6px 10px;
  border-bottom: 1px solid rgba(85,189,202,.15);
  margin-bottom: 4px;
  opacity: .6;
}

.st-nav-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background: var(--primary);
  color: var(--secondary);
  border: solid 6px var(--secondary_low);
  border-right: solid 6px var(--secondary_low);
  border-top: solid 3px var(--secondary_low);
  border-bottom: solid 3px var(--secondary_low);
  font-size: 13px;
  font-weight: bold;
  font-family: inherit;
  cursor: pointer;
  transition: border-color .1s;
  text-align: left;
  width: 100%;
}
.st-nav-item:hover {
  border-color: var(--primary_desat);
  border-top-color: var(--primary_desat);
  border-bottom-color: var(--primary_desat);
}
.st-nav-item--active {
  color: var(--primary);
  background: var(--secondary);
  border-color: var(--secondary_low);
  border-right-color: var(--secondary_low);
  border-top-color: var(--secondary_low);
  border-bottom-color: var(--secondary_low);
}

/* ── Main ── */
.st-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: var(--secondary);
}

.st-section {
  padding: 28px 32px 36px;
  max-width: 660px;
}

.st-fade {
  animation: st-fadein .15s ease both;
}
@keyframes st-fadein {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.st-h2 {
  font-size: 17px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 4px;
}
.st-sub {
  font-size: 13px;
  color: var(--primary_desat);
  opacity: .65;
  line-height: 1.5;
}
.st-divider {
  height: 1px;
  background: rgba(85,189,202,.12);
  margin: 16px 0 20px;
}

/* ── Form ── */
.st-form { display: flex; flex-direction: column; gap: 14px; }
.st-form-row { display: flex; gap: 14px; }
.st-form-row > * { flex: 1; min-width: 0; }
.st-field-spacer { flex: 1; }

.st-sub-label {
  font-size: 12px;
  color: var(--primary_desat);
  opacity: .55;
}
.st-optional { opacity: .8; }

.st-field { display: flex; flex-direction: column; gap: 5px; }
.st-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary_desat);
  letter-spacing: .5px;
  text-transform: uppercase;
  opacity: .75;
}
.st-req { color: var(--tertiary); opacity: 1; }

.st-input-row { display: flex; align-items: center; }
.st-input-row--prefix .st-input { border-left: none; }

.st-prefix {
  font-size: 11px;
  color: var(--primary_desat);
  opacity: .45;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--secondary_low);
  border: 1px solid rgba(85,189,202,.2);
  border-right: none;
  padding: 0 8px;
  height: 36px;
  display: flex;
  align-items: center;
}

.st-input {
  width: 100%; height: 36px; padding: 0 10px;
  background: var(--secondary_low);
  border: 1px solid rgba(85,189,202,.2);
  color: var(--primary_desat);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  border-radius: 0;
  transition: border-color .12s;
}
.st-input::placeholder { color: rgba(200,239,249,.18); }
.st-input:focus { border-color: var(--primary); }
.st-field--err .st-input { border-color: var(--tertiary); }
.st-field-err { font-size: 11.5px; color: var(--tertiary); }
.st-field-err::before { content: '⚠ '; }

/* ── Actions ── */
.st-actions { margin-top: 20px; display: flex; align-items: center; gap: 10px; }

.st-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 16px;
  font-size: 13px; font-weight: bold; cursor: pointer;
  font-family: inherit;
  border-radius: 0;
  transition: border-color .1s, background .1s, color .1s;
}

.st-btn--primary {
  color: var(--secondary);
  background: var(--primary);
  border: solid 6px var(--secondary_low);
  border-right: solid 6px var(--secondary);
  border-top: solid 3px var(--secondary_low);
  border-bottom: solid 3px var(--secondary_low);
}
.st-btn--primary:hover:not(:disabled) {
  background: var(--primary_high);
  border-color: var(--primary_desat);
  border-right-color: var(--secondary);
  border-top-color: var(--primary_desat);
  border-bottom-color: var(--primary_desat);
}
.st-btn--primary:disabled { opacity: .4; cursor: not-allowed; }

.st-btn--ghost {
  background: transparent;
  color: var(--primary_desat);
  border: 1px solid rgba(85,189,202,.25);
  opacity: .8;
}
.st-btn--ghost:hover { border-color: var(--primary); color: var(--primary); opacity: 1; }

.st-btn--danger {
  background: transparent;
  color: #f85149;
  border: 1px solid rgba(248,81,73,.3);
}
.st-btn--danger:hover:not(:disabled) {
  background: rgba(248,81,73,.07);
  border-color: #f85149;
}
.st-btn--danger-confirm {
  background: #da3633;
  color: #fff;
  border-color: #da3633;
}
.st-btn--danger-confirm:hover:not(:disabled) {
  background: #e5534b;
}
.st-btn:disabled { opacity: .4; cursor: not-allowed; }

/* ── Alerts ── */
.st-alert {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px;
  font-size: 13px; margin-bottom: 12px;
  border-radius: 0;
}
.st-alert--success {
  background: rgba(63,185,80,.07);
  border: 1px solid rgba(63,185,80,.2);
  color: #3fb950;
}
.st-alert--error {
  background: rgba(248,81,73,.07);
  border: 1px solid rgba(248,81,73,.2);
  color: #f85149;
}

/* ── Consent card ── */
.st-consent-card {
  background: var(--secondary_low);
  border: 1px solid rgba(85,189,202,.12);
  padding: 18px;
  display: flex;
  flex-direction: column;
}

.st-consent-title { font-size: 14px; font-weight: 600; color: var(--primary); margin-bottom: 8px; }
.st-consent-desc  { font-size: 13px; color: var(--primary_desat); opacity: .65; line-height: 1.6; margin-bottom: 12px; }

.st-consent-list { list-style: none; display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.st-consent-list-item {
  font-size: 13px;
  color: var(--primary_desat);
  opacity: .8;
  padding-left: 2px;
}

.st-toggle-row {
  display: flex; align-items: center; gap: 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(85,189,202,.1);
}
.st-toggle-label { font-size: 13px; color: var(--primary_desat); opacity: .65; flex: 1; }

.st-toggle {
  position: relative; width: 44px; height: 24px;
  border-radius: 999px;
  border: 1px solid rgba(85,189,202,.25);
  background: var(--secondary);
  cursor: pointer;
  transition: background .2s, border-color .2s;
  flex-shrink: 0;
}
.st-toggle--on { background: var(--primary); border-color: var(--primary); }
.st-toggle-thumb {
  position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; border-radius: 50%;
  background: rgba(85,189,202,.35);
  transition: transform .2s, background .2s;
}
.st-toggle--on .st-toggle-thumb {
  transform: translateX(20px);
  background: var(--secondary);
}
.st-toggle:disabled { opacity: .4; cursor: not-allowed; }

.st-info-note {
  margin-top: 12px;
  font-size: 12px;
  color: var(--primary_desat);
  opacity: .45;
  line-height: 1.5;
}

/* ── Danger card ── */
.st-danger-card {
  background: var(--secondary_low);
  border: 1px solid rgba(248,81,73,.18);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.st-danger-title { font-size: 14px; font-weight: 600; color: var(--primary_desat); }
.st-danger-desc  { font-size: 13px; color: var(--primary_desat); opacity: .55; line-height: 1.6; }

.st-danger-action {
  display: flex; align-items: center;
  flex-wrap: wrap; gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(248,81,73,.1);
}

.st-confirm-warning {
  font-size: 12.5px;
  color: var(--tertiary);
  width: 100%;
}

@media (max-width: 560px) {
  .st-nav { width: 52px; }
  .st-nav-header { display: none; }
  .st-nav-item { justify-content: center; font-size: 10px; padding: 8px 4px; }
  .st-section { padding: 18px 14px 24px; }
  .st-form-row { flex-direction: column; }
}
`;
