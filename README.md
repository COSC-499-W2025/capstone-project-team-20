#  Team 20

## Team Contract
[Team Contract (Google Doc)](https://docs.google.com/document/d/1DcXkmHYj8U9HkEnPPMSvHPCUEKag1lkZ32FaHIsgTeI/edit?usp=sharing)

## Work Breakdown Structure

### Milestone #1 (October - December 7th)

![WBS Milestone 1](media/WBS_Milestone_1.jpg)

---

## System Architecture Diagram

![System Architecture Diagram](media/System_Architecture_Diagram.png)

This diagram shows how our system's components will be organized into layers, and the responsibility each layer has.

### Presentation Layer

The Presentation Layer manages interactions with the user. It allows the user to input a .ZIP folder containing their files and displays any summaries or reports that the user requests. 

### Application Layer

The Application Layer performs the system's main processing tasks. The Artifact Crawling component scans selected files, applies filters and gathers metadata. While the Export to Preferred Format component generates any report that the user requests and passes it up to the Presentation Layer.

### Communication Layer

The Communication Layer acts as a link between the Application Layer and the Database Layer. The Data Distribution component ensures that any relevant file data, metadata and any analysis the system produces is served to the Database Layer for storage. The Data Retrieval component passes any relevant stored data from previous scans to the Application Layer.

### Database Layer

The Database Layer provides persistent storage through the File Metadata DB, which collects the information that the system gathers about the user's files, as well as previously produced reports and summaries, and stores them for later use. 



## DFD Level 1

![Level 1 DFD](media/DFD_Level_1.png)

## Data Flow Overview

- User initiates the workflow by providing consent and uploading a project zip file.

- Prompt for Consent captures user permission before any file processing begins, recording consent for privacy compliance.

- Load Zip receives the zip file path and extracts its contents, identifying the root folder structure for analysis.

- Project Analyzer examines the extracted project data, parsing file structures, dependencies, and project characteristics.

- Skill Assessment evaluates the project data to identify technical skills demonstrated, generate insights about code quality and complexity, calculate an overall project score, and award achievement badges.

- Display Stored Analysis presents the complete analysis results and skill summary back to the user. Users can also request previously stored analyses from the database.

- Database serves as the central data store, persisting user configurations as well as project data and analysis results for future retrieval and comparison.
