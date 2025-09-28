# Features Proposal for Mining Digital Work Artifacts Project Option

**Team Number:** 20

**Team Members:**

- Branden Kennedy (42474551)
- Necmi Kaan Sapoglu (17014796)
- 
- 
- 
- 

## 1 Project Scope and Usage Scenario


## 2 Proposed Solution
Our solution is a desktop application that allows users to scan any files on their machine. This includes code, images, videos, documents, or other artifacts that the user chooses to have scanned. The system will extract useful information such as metadata and analytics. Users can select which folders, files, or file types to include in the scan, allowing them to exclude select file types. This gives the user control over their data. The system will calculate metrics such as file type distributions, timelines, contribution statistics, longest active projects, most commonly used programming languages, etc. The data that is crawled will be presented in clear tables and visual graphs. The system will also use incremental scanning to only process new or modified files. This will be done with a local database for fast queries and will be able to operate on major operating systems. The user can also export these summaries in CSV or PDF. By keeping the processing local, the system ensures data privacy. Compared to other teams, our application focuses on data privacy and detailed analytics. Other teams have shown that they may develop a web application that requires uploading data to a server. Our desktop solution keeps processing local, ensuring data privacy while still providing analytics and detailed reporting. 

## 3 Use Cases

Use Case 1: Scan Files/Folders

Primary actor: User

Description: User initiates a scan of selected folders or files to detect supported file types and extract relevant metadata.

Precondition: The application is installed and running. The user has selected folders or files.

Postcondition: Metadata about the scanned files is stored in the local database.

Main Scenario:

User selects folders or files to scan.

User clicks “Scan.”

The system identifies supported file types.

The system extracts metadata (file size, type, dates, contributions, etc.).

Metadata is stored in the local database.

Extensions:

User cancels the scan midway.

Unsupported file types are skipped.

System only scans newly modified files if an incremental scan is chosen.

Use Case 2: Exclude Files or Folders

Primary actor: User

Description: User specifies files or directories to be ignored during scanning.

Precondition: User has selected files or folders.

Postcondition: Excluded items are not processed during future scans.

Main Scenario:

User opens scan settings.

User selects files/folders to exclude.

User saves preferences.

System skips excluded items during the next scan.

Extensions:

User removes exclusions later.

System prompts if excluded folders overlap with previously included selections.

Use Case 3: View Analytics and Summaries

Primary actor: User

Description: User views project statistics in table or graph formats.

Precondition: At least one scan has been completed and data exists in the database.

Postcondition: Data is displayed as tables and/or visual graphs.

Main Scenario:

User navigates to the analytics dashboard.

System queries stored metadata.

System generates visualizations (file type distribution, activity timeline, contributions, etc.).

User views results.

Extensions:

User applies filters (time range, file type, project).

User customizes visualization styles.

Use Case 4: Export Reports

Primary actor: User

Description: User exports project summaries and analytics to external formats.

Precondition: User has generated analytics data.

Postcondition: A report is saved in the chosen format (CSV, PDF, or resume template).

Main Scenario:

User clicks “Export.”

User selects format (CSV, PDF, resume-style).

System generates the report.

System saves or shares the file locally.

Extensions:

Export fails due to missing permissions → system notifies user.

User cancels export before completion.

### UML Diagram:


## 4 Requirements, Testing, Requirement Verification

### Technology Stack:

### Test Framework:

| Requirement | Description | Test Cases | Who | H / M / E |  
| --- | --- | --- | --- | --- | 
| Short phrase or sentence | Description of the feature, the steps involved, the complexity of it, potential difficulties | <ul><li>test case 1</li><li>test case 2</li></ul> | name | Hard |