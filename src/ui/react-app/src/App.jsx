import { useState } from 'react'
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

function Projects(){
    return(
        <>
        <h3>This is the Projects page.</h3>
        </>
    );
}

function Badges(){
    return(
        <>
        <h3>This is the Badges page.</h3>
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
