import os
import tkinter as tk
#from tkinter import Menu, PhotoImage

class App(tk.Tk):

    #window variables
    #self   #The app window itself, appears when window.mainloop() is run, closes when window.destroy() is run.

    #name of app
    appname: str

    #color palette (temp)
    color_primary_high: str
    color_primary: str
    color_primary_desat: str
    color_secondary: str
    color_tertiary: str

    #menu section
    menusection: tk.Frame # frame containing the selected menu
    menuframes: list = [] #list containing each menu's corresponding object to access their menus

    #menu nav
    navsection: tk.Frame # frame containing the nav section
    navidx:int # which menu are we currently in as an index
        #[0] - Settings
    SettingsButton: tk.Button
        #[1] - Projects
    ProjectsButton: tk.Button
        #[2] - Badges
    BadgesButton: tk.Button
        #[3] - Resume
    ResumeButton: tk.Button
        #[4] - Portfolio
    PortfolioButton: tk.Button
        #[5] - Help
    HelpButton: tk.Button

    def __init__(self):
        '''Builds and opens the main window of the application'''

        super().__init__() #initialize 

    #define variables:
        #TODO: choose a name
        self.appname = 'placeholder appname'

        #colours
        #TODO: finalize colors
        self.color_primary = '#55BDCA'
        self.color_primary_high = '#98FFFF'
        self.color_primary_desat = '#C8EFF9'
        self.color_secondary = '#022445'
        self.color_tertiary = '#F27D42'

        #assign variables
        self.title(self.appname)

        #configure window:
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        self.config(bg=self.color_secondary)
        self.geometry("1000x600")

        #assemble window
        self.dashborder()
    
    def dashborder(self):
        '''Builds everything inside the main window (and prompts the default menu to build itself)'''
        #1. create menu window #TODO
            #a) create menu frame #TODO
            #b) run menu_build() #TODO
                #i) construct menu objects #TODO
        #2. create menu navigation bar
            #a) create nav frame
            #b) run nav_build
                #i) create nav buttons 
        #3. build default menu
            #a) runs switchTo() with argument 1 (the default menu)
    
    #navmenu:
        self.navsection = tk.Frame(
            master=self,
            bg=self.color_primary,
        )
        self.navsection.grid(row=0,column=0,sticky='nsw') #nav section appears on far left of window
        self.navidx = -1
        self.nav_build(self.navsection)

    #open default menu
        self.switchTo(1)
    

    def nav_build(self, parent:tk.Frame):
        '''Builds the nav section'''
    #create buttons:
        self.SettingsButton = tk.Button(
            text='Settings',command=lambda:self.switchTo(0),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        self.ProjectsButton = tk.Button(
            text='Projects',command=lambda:self.switchTo(1),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        self.BadgesButton = tk.Button(
            text='Badges',command=lambda:self.switchTo(2),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        self.ResumeButton = tk.Button(
            text='Resume',command=lambda:self.switchTo(3),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        self.PortfolioButton = tk.Button(
            text='Portfolio',command=lambda:self.switchTo(4),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        self.HelpButton = tk.Button(
            text='Help',command=lambda:self.switchTo(5),
            master = parent,width=10,height=5,bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
        
        self.SettingsButton.grid()
        self.ProjectsButton.grid()
        self.BadgesButton.grid()
        self.ResumeButton.grid()
        self.PortfolioButton.grid()
        self.HelpButton.grid()
        
        
    def switchTo(self, idx:int):
        '''Handler for switching menu'''
            # 1. Abort if selected menu is the currently open menu
            # 2. Close currently opened menu (runs menu object's .teardown() method)
                # a) Adjust visuals of corresponding button to be deselected
            # 3. Update self.navidx to idx
            # 4. Open newly selected menu (runs menu object's .build() method)
                # a) Adjust visuals of corresponding button to be selected

        if idx==self.navidx: # if the menu clicked is the currently opened menu, do nothing
            return(idx)
        else:
            match self.navidx:
                case 0:
                    'Settings.teardown()' #TODO create object for Settings
                    self.SettingsButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
                case 1:
                    'Projects.teardown()' #TODO create object for Projects
                    self.ProjectsButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
                case 2:
                    'Badges.teardown()' #TODO create object for Badges
                    self.BadgesButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
                case 3:
                    'Resume.teardown()' #TODO create object for Resume
                    self.ResumeButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
                case 4:
                    'Portfolio.teardown()' #TODO create object for Portfolio
                    self.PortfolioButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)
                case 5:
                    'Help.teardown()' #TODO create object for Help
                    self.HelpButton.config(
                        bg=self.color_primary,fg=self.color_secondary,activebackground=self.color_primary,activeforeground=self.color_secondary,relief=tk.FLAT)

            match idx:
                case 0:
                    'Settings.build()' #TODO create object for Settings
                    self.SettingsButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
                case 1:
                    'Projects.build()' #TODO create object for Projects
                    self.ProjectsButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
                case 2:
                    'Badges.build()' #TODO create object for Badges
                    self.BadgesButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
                case 3:
                    'Resume.build()' #TODO create object for Resume
                    self.ResumeButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
                case 4:
                    'Portfolio.build()' #TODO create object for Portfolio
                    self.PortfolioButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
                case 5:
                    'Help.build()' #TODO create object for Help
                    self.HelpButton.config(
                        bg=self.color_secondary, fg=self.color_primary,activebackground=self.color_secondary,activeforeground=self.color_primary,relief=tk.FLAT)
            
            self.navidx = idx
            self.update_idletasks()
            

app = App()
app.mainloop()