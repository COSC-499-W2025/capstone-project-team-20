import { useState, useEffect } from "react";
import Settings from "./Settings";
import ProfileSetup from "./pages/ProfileSetup";
import Projects from "./pages/Projects";
import Badges from "./pages/Badges"
import ResumePage from "./pages/ResumePage";
import PortfolioPage from "./pages/PortfolioPage";
import Help from "./pages/Help";
import {
  listProjects,
  getProject,
  listSkills,
  getBadgeProgress,
  getYearlyWrapped,
  getConfig,
  getPrivacyConsent,
  uploadProjectZip,
  uploadProjectFromPath,
  clearProjects
} from "./api/client";
import "./App.css";
import { getConfig } from "./api/client";

function App() {
  const [profileReady, setProfileReady] = useState(null);
  const [current, setCurrent] = useState(1);

  useEffect(() => {
    getConfig().then((cfg) => setProfileReady(!!(cfg?.name && cfg?.email && cfg?.phone))).catch(() => setProfileReady(false));
  }, []);

  const buttons = [
    { id: 0, label: "Settings" },
    { id: 1, label: "Projects" },
    { id: 2, label: "Badges" },
    { id: 3, label: "Resume" },
    { id: 4, label: "Portfolio"},
    { id: 5, label: "Help" }
  ];

  const menuRender = () => {
    switch (current) {
      case 0: return <Settings />;
      case 1: return <Projects />;
      case 2: return <Badges />;
      case 3: return <ResumePage />;
      case 4: return <PortfolioPage />;
      case 5: return <Help />;
      default: return <Projects />;
    }
  };

  if (profileReady === null) return <div className="ps-loading">Loading…</div>;
  if (!profileReady) return <ProfileSetup onComplete={() => setProfileReady(true)} />;

  return (
    <div className="screen">
      <div className="stacked-buttons">
        {buttons.map((button) => (
          <button key={button.id} className={button.id === current ? "button-on" : "button-off"} onClick={() => setCurrent(button.id)}>
            {button.label}
          </button>
        ))}
      </div>
      <div className="menu">{menuRender()}</div>
    </div>
  );
}

export default App;
