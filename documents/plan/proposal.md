# Features Proposal for Mining Digital Work Artifacts Project Option

**Team Number:** 20

**Team Members:**

- Branden Kennedy (42474551)
- Necmi Kaan Sapoglu (17014796)
- Sven Annist (42486720)
- Joy Musiel-Henseleit (16289167)
- Lex Nash (84668540)
- Dylan Alexander (16394025)

## 1 Project Scope and Usage Scenario
The intended users are those who use their computer to create/store files from creative or professional activities, and that wish to gather information and view metrics on their activities over time. Some such users may include graduating students or early professionals wishing to improve or update their resume. Upon starting the program, the user will be presented with options to select a starting directory, and exclude certain directories or files if they do not wish for their entire computer to be searched. Upon starting the search, the program will analyze all files in its search area compiling information on each based on their metadata. Upon completion, the user will be presented with various metrics organized by file type containing information on individual projects. The user can then choose to export these metrics into a single file.

## 2 Proposed Solution
Our solution is a desktop application that allows users to scan any files on their machine. This includes code, images, videos, documents, or other artifacts that the user chooses to have scanned. The system will extract useful information such as metadata and analytics. Users can select which folders, files, or file types to include in the scan, allowing them to exclude select file types. This gives the user control over their data. The system will calculate metrics such as file type distributions, timelines, contribution statistics, longest active projects, most commonly used programming languages, etc. The data that is crawled will be presented in clear tables and visual graphs. The system will also use incremental scanning to only process new or modified files. This will be done with a local database for fast queries and will be able to operate on major operating systems. The user can also export these summaries in CSV or PDF. By keeping the processing local, the system ensures data privacy. Compared to other teams, our application focuses on data privacy and detailed analytics. Other teams have shown that they may develop a web application that requires uploading data to a server. Our desktop solution keeps processing local, ensuring data privacy while still providing analytics and detailed reporting.

## 3 Use Cases

### Use Case 1: Scan Files/Folders

**Primary actor:** User

**Description:** User initiates a scan of selected folders or files to detect supported file types and extract relevant metadata.

**Precondition:** The application is installed and running. The user has selected folders or files.

**Postcondition:** Metadata about the scanned files is stored in the local database.

**Main Scenario:**

1. User selects folders or files to scan.
2. User clicks “Scan.”
3. The system identifies supported file types.
4. The system extracts metadata (file size, type, dates, contributions, etc.).
5. Metadata is stored in the local database.

**Extensions:**

- User cancels the scan midway.
- Unsupported file types are skipped.
- System only scans newly modified files if an incremental scan is chosen.

---

### Use Case 2: Exclude Files or Folders

**Primary actor:** User

**Description:** User specifies files or directories to be ignored during scanning.

**Precondition:** User has selected files or folders.

**Postcondition:** Excluded items are not processed during future scans.

**Main Scenario:**

1. User opens scan settings.
2. User selects files/folders to exclude.
3. User saves preferences.
4. System skips excluded items during the next scan.

**Extensions:**

- User removes exclusions later.
- System prompts if excluded folders overlap with previously included selections.

---

### Use Case 3: View Analytics and Summaries

**Primary actor:** User

**Description:** User views project statistics in table or graph formats.

**Precondition:** At least one scan has been completed and data exists in the database.

**Postcondition:** Data is displayed as tables and/or visual graphs.

**Main Scenario:**

1. User navigates to the analytics dashboard.
2. System queries stored metadata.
3. System generates visualizations (file type distribution, activity timeline, contributions, etc.).
4. User views results.

**Extensions:**

- User applies filters (time range, file type, project).
- User customizes visualization styles.

---

### Use Case 4: Export Reports

**Primary actor:** User

**Description:** User exports project summaries and analytics to external formats.

**Precondition:** User has generated analytics data.

**Postcondition:** A report is saved in the chosen format (CSV, PDF, or resume template).

**Main Scenario:**

1. User clicks “Export.”
2. User selects format (CSV, PDF, resume-style).
3. System generates the report.
4. System saves or shares the file locally.

**Extensions:**

- Export fails due to missing permissions → system notifies user.
- User cancels export before completion.

---

### UML Diagram:
<img src="./umlUseCaseDiagram.png" alt="UML Use Case Diagram" width="50%" />

## 4 Requirements, Testing, Requirement Verification

### Technology Stack:

### Test Framework:

| Requirement | Description | Test Cases | Who | H / M / E |  
| --- | --- | --- | --- | --- | 
| Select folders/files to scan | An interface allows users to specify files, folders, or artifacts to include in the scan. Complexity: handling multiple file formats and updating scan configurations accordingly. Potential difficulties include ensuring that user selections are saved and reflected in scans. | Positive Test Cases <ul><li>test_select_single_folder(): Create test folder with 5 different file types (.py, .js, .java, .txt, .md), select folder via dialog, verify all 5 files appear in selection list</li><li>test_select_multiple_folders(): Select 3 separate project folders, verify all folder paths are stored and total file count matches expected sum</li><li>test_select_individual_files(): Select 4 individual files of different types, verify only selected files appear in scan queue, not entire parent folders</li><li>test_select_nested_directory(): Select root folder containing 3 levels of subdirectories, verify all nested files are discovered and counted correctly</li></ul> Negative Test Cases <ul><li>test_select_nonexistent_path(): Attempt to select a nonexistent filepath, verify error message displayed and selection rejected</li><li>test_select_no_permissions(): Select folder without read permissions, verify graceful error handling and user notification</li><li>test_select_empty_folder(): Select completely empty folder, verify system handles gracefully with error message</ul>| . | E |
| Exclude folders/files from scanning | Prior to scanning, users will be able to specify files and folders to exclude. Complexity: maintaining exclusion to nested directories. Potential difficulties include performance with complex exclusion rules, and accurately updating exclusions lists. | Positive Test Cases <ul><li>test_exclude_file_types(): Exclude ".log" files, scan folder with mixed files, verify 0 log files in results</li><li>test_exclude_folders(): Exclude "node_modules" and ".git" folders, verify these folders completely skipped during scan</li><li>test_exclusion_persistence(): Set exclusions, restart app, verify exclusion rules still active and applied to new scans</li></ul> Negative Test Cases <ul><li>test_exclude_nonexistent_folder(): Add non-existent folder to exclusions, verify no errors occur during scan</li><li>test_conflicting_rules(): Include "/project" but exclude "/project/src", verify conflict resolution </li><li>test_overlapping_exclusions(): Exclude a folder and one of its subfolders separately, verify the system correctly skips all excluded files without errors| . | M |
| Scan and detect file types | The system scans and identifies supported file types. Complexities: handling large directories and multiple file formats. Potential difficulties include handling of unsupported files and performance with large datasets. | Positive Test Cases <ul><li>test_detect_common_extensions(): Scan folder with .py, .js, .java, .cpp files, verify each detected with correct language classification</li><li>test_large_directory_performance(): Scan directory with large amount of files, verify all files processed</li><li>test_language_detection_accuracy(): Scan mixed codebase, verify Python files detected as "Python", JavaScript as "JavaScript", etc.</li></ul> Negative Test Cases <ul><li>test_corrupted_file_handling(): Include corrupted binary file in scan, verify system skips gracefully without crashing</li><li>test_misleading_extensions(): Create .txt file containing Python code, verify system detects actual content type vs. extension</li><li>test_zero_byte_files(): Scan folder containing empty files, verify they're logged but don't cause errors</li><li>test_special_character_filenames(): Scan files with names containing unicode, spaces, and special chars, verify all processed correctly</li></ul> | . | H |
| Skip excluded files/folders | The system will ensure items marked for exclusion are skipped in all scans. Complexity: ensuring consistency when skipping across nested directories and incremental scans. Potential difficulties include identifying overlapping inclusion/exclusion rules. | Positive Test Cases <ul><li>test_skip_excluded_folders(): Exclude "/project/build", scan "/project", verify 0 files from build folder in results</li><li>test_exclusion_after_restart(): Set exclusions, restart application, run scan, verify exclusions still actively filtering files</li><li>test_nested_exclusion_accuracy(): Exclude "/src/tests" within included "/src", verify only test files skipped, other src files included</li></ul> Negative Test Cases <ul><li>test_renamed_excluded_folder(): Exclude "old_name" folder, rename to "new_name", verify exclusion rule no longer applies to renamed folder</li><li>test_inclusion_overrides_exclusion(): Include specific file that matches exclusion pattern, verify file is included (test rule precedence)</li><li>test_locked_file_exclusion(): Attempt to exclude currently running/locked file, verify exclusion still works on next scan</li></ul> | . | M |
| Extract metadata | The system will extract file metadata such as creation/modification date, size, language usage, contributions. Complexity: parsing various file types, extracting, and aggregating meaningful metrics. Potential difficulties include handling corrupted files. | Positive Test Cases <ul><li>test_basic_metadata_extraction(): Scan test folder, verify each file has size, creation_date, modified_date, and file_type extracted</li><li>test_git_contribution_parsing(): Scan git repository, verify author names, commit counts, and date ranges extracted for each file</li><li>test_code_metrics_calculation(): Scan Python project, verify lines_of_code, comment_ratio, and complexity_score calculated per file</li><li>test_document_metadata_extraction(): Scan Word/PDF documents, verify author, title, creation_date extracted from document properties</li></ul> Negative Test Cases <ul><li>test_corrupted_file_metadata(): Include corrupted .docx file, verify system extracts available metadata and logs corruption gracefully</li><li>test_missing_timestamp_files(): Process files with missing/invalid timestamps, verify system uses file system defaults without errors</li><li>test_permission_denied_metadata(): Attempt metadata extraction on read-protected file, verify graceful handling and error logging</li></ul> | . | H |
| Store metadata in local database | The system will save extracted metadata for querying, filtering, and reporting. Complexity: database schema design, efficient storage of data. Potential difficulties include handling large volumes of data and ensuring data integrity. | Positive Test Cases <ul><li>test_bulk_metadata_storage(): Store metadata for large number of files, verify all records saved correctly and database size reasonable</li><li>test_referential_integrity(): Store file metadata with project references, verify foreign key constraints maintained across related tables</li><li>test_database_query_performance(): Query stored metadata for large number of files by various criteria, verify queries complete within reasonable timeframe</li></ul> Negative Test Cases <ul><li>test_database_corruption_recovery(): Mock database file corruption, verify system detects issue and rebuilds/recovers automatically</li><li>test_insufficient_disk_space(): Mock full disk space, attempt metadata storage, verify graceful degradation and user notification</li><li>test_invalid_data_storage(): Attempt to store malformed metadata (null values, wrong types), verify validation and error handling</li></ul>| . | M |
| Incremental scanning | The system will only process new or modified files on subsequent scans. Complexity: accurately tracking file changes and comparing this with previously scanned metadata. Potential difficulties include detecting modifications such as renamed or moved files.  | Positive Test Cases <ul><li>test_skip_unchanged_files(): Run scan twice on same folder, verify second scan processes 0 files</li><li>test_detect_new_files(): Add 10 new files between scans, verify only new files processed on second scan</li><li>test_detect_modified_files(): Modify 3 existing files' content, verify only those 3 files re-processed on next incremental scan</li><li>test_handle_moved_files(): Move files within scan directory, verify files detected at new location without full re-processing</li></ul> Negative Test Cases <ul><li>test_file_modified_during_scan(): Modify file while scan in progress, verify system handles gracefully without corruption</li><li>test_file_renamed_between_scans(): Rename files between scans, verify system treats as new file</li></ul>| . | H |
| Calculate metrics | The system will compute meaningful metrics such as file type distributions, activity timelines, and commonly used programming languages. Complexity: determining what metadata to aggregate based on files scanned, efficiently aggregating metadata and ensuring accurate calculations. Potential difficulties: handling incomplete or missing data, performance during aggregation of large datasets. | <ul><li>1</li><li>2</li></ul> | . | M |
| Display summary in tables/graphs | The system will provide users with a visual display of metrics. Complexity: ensuring tables and charts are rendered accurately and the UI is responsive. Potential difficulties: handling large datasets and ensuring the UI does not freeze or lag, ensuring clarity and legibility in graph labels and scaling for user accessibility. | <ul><li>1</li><li>2</li></ul> | . | E |
| Search/filter metadata | This feature enables users to query metadata by type, date, size, contributions, etc. Complexity: ensuring the filtering logic is efficient. Potential difficulties: handling invalid queries and providing support for combining filters. | <ul><li>1</li><li>2</li></ul> | . | M |
| Export metadata summaries | The system will allow exporting summaries to CSV and PDF formats. Complexity: correctly implementing consistent data outputs across different file types as well as integrating export libraries. Potential difficulties: handling large exports and ensuring proper formatting. | <ul><li>1</li><li>2</li></ul> | . | E |
| Export reports in templates for resumes/portfolios | The system will provide pre-designed templates to generate reports with extracted metadata. Complexity: correctly applying structured templates to dynamic data, formatting data correctly. Potential difficulties: handling incomplete datasets or incompatibilities with templates and data to display. | <ul><li>1</li><li>2</li></ul> | . | M |
