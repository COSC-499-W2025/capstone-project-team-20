import { useState, useEffect } from "react";
import Settings from "./Settings";
import ProfileSetup from "./pages/ProfileSetup";
import Projects from "./pages/Projects";
import Badges from "./pages/Badges"
import ResumePage from "./pages/ResumePage";
import PortfolioPage from "./pages/PortfolioPage";
import Help from "./pages/Help";
import {getConfig,} from "./api/client";
import "./App.css";

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

  const whenClick = (id) => {
    //takes the button of the id clicked and sets our 'current' variable to it
    console.log("Clicked:",id);
    setCurrent(id);
  };

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

  if (profileReady === null) return <div className="loading">Loading…</div>;
  if (!profileReady) return <ProfileSetup onComplete={() => setProfileReady(true)} />;

  //on app construction/refresh, builds our UI
  return(
    <div className="app-shell">
      <div className="grid-bg"></div>
      
      <div className="screen">
        {/* Left Side Buttons */}
        <div className="sidebar">
          <div className="bar" aria-hidden="true" />
          {buttons.map(button => (
            <button
              key = {button.id}
              className={
                button.id === current
                  ? "nav-btn nav-btn--active"
                  : "nav-btn"
              }
              onClick={()=>whenClick(button.id)}
            >
              {button.label}
            </button>
          ))}
        </div>
        {/* Right Side Content */}
        <div className="menu">
          <div className="bar" aria-hidden="true" style={{ marginLeft: "-30px", marginRight: "-30px"}} />
          {menuRender()}
        </div>
      </div>
    </div>
  );
}

export default App;
