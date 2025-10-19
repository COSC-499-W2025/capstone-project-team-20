#  Team 20

## Work Breakdown Structure

### Milestone #1 (October - December 7th)

---

| Number | Description |
|--------|-------------|
| **1.0** | **Project Management and Planning** |
| 1.1 | Requirements and Use Cases |
| 1.2 | System Architecture |
| 1.3 | Team Collaboration and Plan |
| 1.4 | Initial Project Setup |
| 1.5 | Docker Containerization |

---

| Number | Description |
|--------|-------------|
| **2.0** | **Folder Intake and Exclusion System** |
| 2.1 | Zip Folder Intake |
| 2.2 | Exclusion Logic |
| 2.3 | Request for Consent |

---

| Number | Description |
|--------|-------------|
| **3.0** | **File Scanning Engine** |
| 3.1 | Zip Folder Parsing |
| 3.2 | Project Tree Generation |
| 3.3 | Error Handling for Disallowed File Types |
| 3.4 | File Type, Framework and Language Detection |
| 3.5 | Collaborative Project Detection |
| 3.6 | Exclusion of Previously Scanned Files |
| 3.7 | Progress Tracking and Cancellation |

---

| Number | Description |
|--------|-------------|
| **4.0** | **Incremental Scanning System** |
| 4.1 | File Change Detection |
| 4.2 | File Timestamp Comparison |
| 4.3 | Identification of New Files |
| 4.4 | Individual Contribution Extractor |

---

| Number | Description |
|--------|-------------|
| **5.0** | **Metadata Extraction** |
| 5.1 | Basic File Metadata Extraction |
| 5.2 | Extraction of Code Metrics |
| 5.3 | Git Repository Integration |
| 5.4 | Advanced Metadata Aggregation |

---

| Number | Description |
|--------|-------------|
| **6.0** | **Analytics Generation** |
| 6.1 | Key Skill Identification |
| 6.2 | Calculation of Creative Metrics |
| 6.3 | Project Importance Ranking |
| 6.4 | Timeline Building for Projects and Skills |
| 6.5 | Highlight Key Individual Contributions |
| 6.6 | Summary of Key Projects |

---

| Number | Description |
|--------|-------------|
| **7.0** | **Database Management** |
| 7.1 | Local Storage Framework |
| 7.2 | Storage of Project Information and User Configurations |
| 7.3 | Retrieval of Previously Generated Portfolio and Resumé Items |
| 7.4 | Deletion of Previously Generated Insights |
| 7.5 | Query Optimization and Schema Design |

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

[lucidchart](https://lucid.app/lucidchart/13a08813-0a92-4798-84d0-2930be2d6aab/edit?page=0_0&invitationId=inv_bf1a126c-f925-4868-bae1-2bdfacdd4bf7#)

![Level 1 DFD](media/DFD_Level_1.png)

This diagram shows how data moves through the system — from user actions to file analysis and reporting.

- User selects files, sets filters, and generates reports.

- Permission & Privacy Logic ensures user consent before processing data.

- File Selection and Exclude Logic handle which files are included or ignored.

- Validation & Scan Logic check and scan files to collect type, size, and metadata.

- The Database stores all scanned data for later use.

- Filter and Aggregation Logic organize and summarize the data.

- User Analytics calculates metrics and insights.

- Display Logic shows charts, tables, and summaries.

- Finally, the user can Generate Reports and export them as PDF or CSV.