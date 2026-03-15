import { useState } from "react";

function Section({ title, children }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="help-section">
      <button
        className="help-toggle"
        onClick={() => setOpen(!open)}
      >
        {title}
        <span className="help-arrow">{open ? "▲" : "▼"}</span>
      </button>

      {open && <div className="help-content">{children}</div>}
    </div>
  );
}

export default function Help() {
  return (
    <div className="help-page">
      <h3>Help & Info</h3>

      <Section title="Overview">
        <p>
          Project Analyzer evaluates software projects to identify technical
          skills, code quality attributes, and project complexity.
        </p>

        <p>The system analyzes:</p>

        <ul>
          <li>project structure</li>
          <li>source code files</li>
          <li>dependencies</li>
          <li>technologies used</li>
          <li>code content</li>
          <li>metadata</li>
          <li>github commit contributions</li>
        </ul>

        <p>
          The result is a detailed report describing the developer skills
          demonstrated in the project, which can then be used in the creation of 
          a resume or portfolio, exported as a pdf.
        </p>
      </Section>

      <Section title="Uploading a Project">
        <p>You can analyze projects in two ways:</p>

        <h4>Upload a ZIP</h4>
        <ul>
          <li>Compress your project folder into a .zip file</li>
          <li>Go to the Projects tab</li>
          <li>Click Upload and select your file</li>
        </ul>

        <h4>Import a Git Repository</h4>
        <ul>
          <li>Paste the repository URL</li>
          <li>Ensure the repository is accessible</li>
        </ul>
      </Section>

      <Section title="Running an Analysis">
        <ol>
          <li>Select a project from the project list</li>
          <li>Click Analyze Project</li>
          <li>Wait while the system processes the files</li>
        </ol>
      </Section>

      <Section title="Understanding Results">
        <p>The analysis report includes:</p>

        <ul>
          <li><b>Project Summary</b> – languages and size</li>
          <li><b>Technologies Used</b> – frameworks and libraries</li>
          <li><b>Skill Indicators</b> – detected technical skills</li>
          <li><b>Code Quality Insights</b> – complexity and structure</li>
        </ul>
      </Section>

      <Section title="Badges">
        <p>
          Badges represent recognized technical achievements discovered in the
          project to help you recognize what strengths you show through your work.
        </p>
      </Section>

      <Section title="Troubleshooting">
        <h4>Upload Failed</h4>
        <ul>
          <li>Ensure the zip file is not corrupted</li>
          <li>Files must be compressed in the zip format, not just renamed to .zip</li>
        </ul>
      </Section>

      <Section title="Privacy & Security">
        <p>
          Uploaded projects are analyzed locally, no information is uploaded to any third party.
        </p>
      </Section>
    </div>
  );
}