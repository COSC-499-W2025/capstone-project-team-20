import { useState } from "react";
import { saveConfig } from "../api/client";

export default function ProfileSetup({ onComplete }) {
  const [step, setStep]     = useState(0);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const [form, setForm] = useState({
    name: "", email: "", phone: "", github: "", linkedin: "",
  });

  function change(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      setTouched((t) => ({ ...t, [field]: true }));
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

  function goToLinks() {
    const errs = validate();
    setErrors(errs);
    setTouched({ name: true, email: true, phone: true });
    if (!Object.keys(errs).length) setStep(2);
  }

  async function handleSave() {
    setSaving(true);
    setErrors({});
    try {
      await saveConfig({
        name:     form.name.trim(),
        email:    form.email.trim(),
        phone:    form.phone.trim(),
        github:   form.github.trim()   || undefined,
        linkedin: form.linkedin.trim() || undefined,
      });
      setStep(3);
    } catch (e) {
      setErrors({ save: e?.message ?? "Failed to save. Please try again." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <style>{CSS}</style>
      <div className="ps-root">
        <div className="ps-grid" aria-hidden="true" />

        <div className="ps-card">
          <div className="ps-bar" aria-hidden="true" />

          {/* stepper */}
          {step < 3 && (
            <div className="ps-stepper" role="list" aria-label="Setup progress">
              {["Welcome", "Identity", "Links"].map((label, i) => (
                <div
                  key={label}
                  role="listitem"
                  className={
                    "ps-step" +
                    (i === step ? " ps-step--active" : "") +
                    (i < step  ? " ps-step--done"   : "")
                  }
                >
                  <div className="ps-dot">
                    {i < step ? <CheckSVG size={12} /> : <span>{i + 1}</span>}
                  </div>
                  <span className="ps-step-label">{label}</span>
                  {i < 2 && <div className="ps-step-line" aria-hidden="true" />}
                </div>
              ))}
            </div>
          )}

          {/* ── Step 0: Welcome ── */}
          {step === 0 && (
            <div className="ps-panel ps-fade" key="welcome">
              <div className="ps-icon-wrap" aria-hidden="true"><FolderSVG /></div>
              <h1 className="ps-h1">Hey — looks like you're new here!</h1>
              <p className="ps-sub">
                We'll just need a few details from you.
              </p>
              <div className="ps-checklist" role="list">
                {[
                  ["✦", "Name, email & phone",            "required"],
                  ["◈", "GitHub & LinkedIn",               "optional"],
                  ["◉", "Ready to analyze your projects",  ""],
                ].map(([icon, text, badge]) => (
                  <div className="ps-check-row" role="listitem" key={text}>
                    <span className="ps-check-icon" aria-hidden="true">{icon}</span>
                    <span>{text}</span>
                    {badge && (
                      <span className={"ps-badge ps-badge--" + badge}>{badge}</span>
                    )}
                  </div>
                ))}
              </div>
              <button className="ps-btn ps-btn--primary" onClick={() => setStep(1)}>
                Let's get started <ArrowSVG />
              </button>
            </div>
          )}

          {/* ── Step 1: Identity ── */}
          {step === 1 && (
            <div className="ps-panel ps-fade" key="identity">
              <h2 className="ps-h2">Your identity</h2>
              <p className="ps-sub">These three fields appear directly on your resume.</p>
              <div className="ps-form">
                <Field id="name"  label="Full name" type="text"  placeholder="Ada Lovelace"
                  value={form.name}  onChange={change("name")}
                  error={touched.name  && errors.name}  required />
                <Field id="email" label="Email"     type="email" placeholder="ada@lovelace.dev"
                  value={form.email} onChange={change("email")}
                  error={touched.email && errors.email} required />
                <Field id="phone" label="Phone"     type="tel"   placeholder="+1 (555) 867-5309"
                  value={form.phone} onChange={change("phone")}
                  error={touched.phone && errors.phone} required />
              </div>
              <div className="ps-actions">
                <button className="ps-btn ps-btn--ghost" onClick={() => setStep(0)}>
                  Back
                </button>
                <button className="ps-btn ps-btn--primary" onClick={goToLinks}>
                  Continue <ArrowSVG />
                </button>
              </div>
            </div>
          )}

          {/* ── Step 2: Links ── */}
          {step === 2 && (
            <div className="ps-panel ps-fade" key="links">
              <h2 className="ps-h2">Online presence</h2>
              <p className="ps-sub">Optional — you can always update these in Settings.</p>
              <div className="ps-form">
                <Field id="github"   label="GitHub username" type="text"
                  placeholder="ada-lovelace" prefix="github.com/"
                  value={form.github}   onChange={change("github")} />
                <Field id="linkedin" label="LinkedIn handle" type="text"
                  placeholder="ada-lovelace" prefix="linkedin.com/in/"
                  value={form.linkedin} onChange={change("linkedin")} />
              </div>
              {errors.save && (
                <p className="ps-error-banner" role="alert">{errors.save}</p>
              )}
              <div className="ps-actions">
                <button className="ps-btn ps-btn--ghost" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  className="ps-btn ps-btn--primary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? "Saving…" : <span>Save profile <ArrowSVG /></span>}
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Done ── */}
          {step === 3 && (
            <div className="ps-panel ps-panel--done ps-fade" key="done">
              <div className="ps-burst" aria-hidden="true">
                <div className="ps-ring ps-ring--1" />
                <div className="ps-ring ps-ring--2" />
                <div className="ps-ring-check"><CheckSVG size={28} /></div>
              </div>
              <h2 className="ps-h2">
                You're all set{form.name ? `, ${form.name.split(" ")[0]}` : ""}!
              </h2>
              <p className="ps-sub">
                Profile saved. Upload your first project zip to get started —
                we'll analyze it, score it, and help you build a standout resume.
              </p>
              <button className="ps-btn ps-btn--primary" onClick={onComplete}>
                Go to Projects <ArrowSVG />
              </button>
            </div>
          )}
        </div>

        {step < 3 && (
          <p className="ps-footer" role="note">
            Your data is stored locally and never sent to a third party.
          </p>
        )}
      </div>
    </>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Field({ id, label, type, placeholder, value, onChange, error, required, prefix }) {
  return (
    <div className={"ps-field" + (error ? " ps-field--err" : "")}>
      <label className="ps-label" htmlFor={id}>
        {label}
        {required && <span className="ps-req" aria-label="required"> *</span>}
      </label>
      <div className={"ps-input-row" + (prefix ? " ps-input-row--prefix" : "")}>
        {prefix && <span className="ps-prefix" aria-hidden="true">{prefix}</span>}
        <input
          id={id} type={type} placeholder={placeholder}
          value={value} onChange={onChange}
          className="ps-input"
          aria-required={required}
          aria-invalid={!!error}
          aria-describedby={error ? id + "-err" : undefined}
        />
      </div>
      {error && (
        <p className="ps-field-err" id={id + "-err"} role="alert">{error}</p>
      )}
    </div>
  );
}

function CheckSVG({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ArrowSVG() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true"
      style={{ marginLeft: 6, display: "inline-block", verticalAlign: "middle" }}>
      <path d="M3 7H11M11 7L7.5 3.5M11 7L7.5 10.5"
        stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FolderSVG() {
  return (
    <svg width="48" height="48" viewBox="0 0 52 52" fill="none" aria-hidden="true">
      <path
        d="M6 14C6 11.8 7.8 10 10 10H22L27 16H42C44.2 16 46 17.8 46 20V38C46 40.2 44.2 42 42 42H10C7.8 42 6 40.2 6 38V14Z"
        fill="currentColor" fillOpacity=".15" stroke="currentColor" strokeWidth="2" />
      <path d="M20 26l2.5 5 5-9 5 7 2.5-3"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="41" cy="11" r="1.5" fill="currentColor" />
      <circle cx="45" cy="7"  r="1"   fill="currentColor" />
      <circle cx="38" cy="7"  r="1"   fill="currentColor" />
    </svg>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const CSS = `
.ps-root *, .ps-root *::before, .ps-root *::after { box-sizing: border-box; margin: 0; padding: 0; }

.ps-root {
  --accent:  #58a6ff;
  --accent2: #f78166;
  --bg:      #0d1117;
  --surface: #161b22;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --success: #3fb950;
  --error:   #f85149;
  --r:       10px;
  min-height: 100vh;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: var(--bg);
  padding: 24px 16px 48px;
  position: relative; overflow: hidden;
  font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
  color: var(--text);
}

.ps-grid {
  position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(88,166,255,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(88,166,255,.05) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black 20%, transparent 100%);
}

.ps-card {
  position: relative; width: 100%; max-width: 460px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(88,166,255,.06);
}

.ps-bar {
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent));
  background-size: 200% 100%;
  animation: ps-shimmer 3s linear infinite;
}
@keyframes ps-shimmer {
  0%   { background-position: 200% center; }
  100% { background-position: -200% center; }
}

.ps-stepper { display: flex; align-items: center; padding: 18px 28px 0; gap: 0; }
.ps-step    { display: flex; align-items: center; gap: 8px; flex: 1; }
.ps-step:last-child { flex: 0; }

.ps-dot {
  width: 26px; height: 26px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
  border: 1.5px solid var(--border); color: var(--muted); background: var(--bg);
  transition: all .2s;
}
.ps-step--active .ps-dot {
  border-color: var(--accent); color: var(--accent);
  background: rgba(88,166,255,.12); box-shadow: 0 0 10px rgba(88,166,255,.3);
}
.ps-step--done .ps-dot {
  border-color: var(--success); color: var(--success);
  background: rgba(63,185,80,.12);
}
.ps-step-label { font-size: 11px; color: var(--muted); font-weight: 500; white-space: nowrap; }
.ps-step--active .ps-step-label { color: var(--accent); }
.ps-step--done   .ps-step-label { color: var(--success); }
.ps-step-line { flex: 1; height: 1px; background: var(--border); margin: 0 8px; }

.ps-panel { padding: 24px 28px 28px; }
.ps-panel--done { text-align: center; padding: 32px 28px 36px; }

.ps-fade { animation: ps-fadein .25s ease both; }
@keyframes ps-fadein {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ps-icon-wrap { color: var(--accent); margin-bottom: 18px; }

.ps-checklist {
  display: flex; flex-direction: column; gap: 9px;
  margin: 20px 0; padding: 16px 18px;
  background: rgba(88,166,255,.05);
  border: 1px solid rgba(88,166,255,.1);
  border-radius: var(--r);
}
.ps-check-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 14px; color: var(--text);
}
.ps-check-icon { color: var(--accent); font-size: 11px; width: 14px; flex-shrink: 0; }

.ps-badge {
  margin-left: auto; font-size: 10px; font-weight: 700;
  letter-spacing: .4px; text-transform: uppercase;
  padding: 2px 7px; border-radius: 999px;
}
.ps-badge--required { background: rgba(247,129,102,.15); color: var(--accent2); }
.ps-badge--optional { background: rgba(139,148,158,.12); color: var(--muted); }

.ps-h1 { font-size: 22px; font-weight: 800; line-height: 1.3; margin-bottom: 8px; letter-spacing: -.3px; }
.ps-h2 { font-size: 20px; font-weight: 700; line-height: 1.3; margin-bottom: 8px; }
.ps-sub { font-size: 14px; color: var(--muted); line-height: 1.6; margin-bottom: 4px; }

.ps-form { display: flex; flex-direction: column; gap: 16px; margin-top: 18px; }
.ps-field { display: flex; flex-direction: column; gap: 5px; }

.ps-label {
  font-size: 11px; font-weight: 700; color: var(--muted);
  letter-spacing: .6px; text-transform: uppercase;
}
.ps-req { color: var(--accent2); }

.ps-input-row { display: flex; align-items: center; }
.ps-prefix {
  font-size: 12px; color: var(--muted); white-space: nowrap; flex-shrink: 0;
  background: var(--bg); border: 1px solid var(--border); border-right: none;
  padding: 0 10px; height: 40px; display: flex; align-items: center;
  border-radius: var(--r) 0 0 var(--r);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
}

.ps-input {
  width: 100%; height: 40px; padding: 0 12px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--r); color: var(--text); font-size: 14px;
  font-family: inherit; outline: none;
  transition: border-color .15s, box-shadow .15s;
}
.ps-input-row--prefix .ps-input {
  border-left: none; border-radius: 0 var(--r) var(--r) 0;
}
.ps-input::placeholder { color: #3d444d; }
.ps-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(88,166,255,.15);
}
.ps-field--err .ps-input { border-color: var(--error); }
.ps-field--err .ps-input:focus { box-shadow: 0 0 0 3px rgba(248,81,73,.15); }
.ps-field-err { font-size: 12px; color: var(--error); }
.ps-field-err::before { content: '⚠ '; }

.ps-actions { display: flex; justify-content: space-between; gap: 10px; margin-top: 24px; }

.ps-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 40px; padding: 0 18px; border-radius: var(--r);
  font-size: 14px; font-weight: 600; cursor: pointer;
  border: 1.5px solid transparent; font-family: inherit;
  transition: all .15s;
}
.ps-btn--primary {
  background: var(--accent); color: #0d1117; border-color: var(--accent);
}
.ps-btn--primary:hover:not(:disabled) {
  background: #79c0ff; border-color: #79c0ff;
  box-shadow: 0 0 14px rgba(88,166,255,.35); transform: translateY(-1px);
}
.ps-btn--primary:disabled { opacity: .5; cursor: not-allowed; }
.ps-btn--ghost {
  background: transparent; color: var(--muted); border-color: var(--border);
}
.ps-btn--ghost:hover { border-color: var(--muted); color: var(--text); }

/* full-width for welcome & done panels */
.ps-panel > .ps-btn--primary,
.ps-panel--done .ps-btn--primary {
  width: 100%; height: 44px; font-size: 15px; margin-top: 4px;
}
/* but NOT in ps-actions (two-button rows) */
.ps-actions .ps-btn--primary { width: auto; height: 40px; font-size: 14px; margin-top: 0; }

.ps-error-banner {
  margin-top: 12px; padding: 10px 14px;
  background: rgba(248,81,73,.1); border: 1px solid rgba(248,81,73,.2);
  border-radius: var(--r); color: var(--error); font-size: 13px;
}

.ps-burst { position: relative; width: 72px; height: 72px; margin: 0 auto 22px; }
.ps-ring {
  position: absolute; border-radius: 50%; border: 2px solid var(--success);
  inset: 0; opacity: 0; animation: ps-burst .5s ease forwards;
}
.ps-ring--1 { animation-delay: .05s; }
.ps-ring--2 { inset: -12px; border-color: rgba(63,185,80,.3); animation-delay: .15s; }
@keyframes ps-burst {
  0%   { transform: scale(.6); opacity: .8; }
  100% { transform: scale(1);  opacity: .2; }
}
.ps-ring-check {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(63,185,80,.14); border-radius: 50%;
  color: var(--success); border: 2px solid var(--success);
  animation: ps-fadein .35s ease .2s both;
}

.ps-footer {
  margin-top: 16px; font-size: 11px; color: var(--muted);
  opacity: .55; text-align: center; font-family: monospace;
}

/* used in App.jsx during the getConfig() check */
.ps-loading {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: #0d1117; color: #8b949e; font-family: monospace; font-size: 13px;
}
`;
