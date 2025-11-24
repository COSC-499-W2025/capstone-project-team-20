## Week 3: Sep 14-21

### Tasks worked on:
![Svens Tasks for W3](./imagesForSvenLogs/w3.png)

## Weekly Goals Recap:

This week, our team focused on defining requirements for the project and created a rough draft of initial thoughts to which we refined after discussions with the other teams in class to include things that were in our blindspot initially.

## Week 4: Sep 21-28

### Tasks worked on:
![Svens tasks for w4](./imagesForSvenLogs/w4.png)

## Weekly Goals Recap:

This week, our team made a diagram of our system architecture & shared them with various other teams to get feedback on our design and lean from what other teams are doing to refine our ideas. Additionally, we've been developing our project proposal. As of now we've outlined a proposed solution in addition to several use cases along with the correspondent UML use case diagram which I constructed. We will be working on outlining our workload distribution.


## Week 5: Sep 28-Oct 05

### Tasks worked on:
![Svens Tasks for W5](./imagesForSvenLogs/w5.png)

## Weekly Goals Recap:
This week, our team constructed level 0 & 1 DFD Diagrams to display and compare our data flows with other teams and then improve upon our own based on what we saw other teams ideas (specifically teams 2,6,10); specifics about these teams has been completed in the DFD lvl 1 assignment. With this information we will work on finalizing our requirements and design elements and make a WBS to hopefully get going with development soon.

## Week 6: Oct 05-Oct 12

### Tasks worked on:
![Svens Tasks for W6](./imagesForSvenLogs/w6.png)


## Weekly Goals Recap:
This week, our team worked on adding issues to our project board in accordance with milestone 1 along with respective assignments aswell as polishing up our level 1 DFD and adding it to the repository proper. Additionally, we initialized the base of the repository; I specifically worked on getting our docker container up and running ([Associated PR](https://github.com/COSC-499-W2025/capstone-project-team-20/pull/63))

## Week 7: Oct 12-Oct 19

### Tasks worked on:
![Svens Tasks for W6](./imagesForSvenLogs/w7.png)


### Weekly Goals Recap:
This week, our team finalized the WBS for Milestone 1, converted it into prioritized GitHub issues on the project board, and did minor repo housekeeping; I implemented the ProjectFile node and its tests ([PR #85](https://github.com/COSC-499-W2025/capstone-project-team-20/pull/85)) to support the upcoming ZipParser, extracting core metadata (name, size, type, last modified) from ZipInfo and maintaining a parent reference for tree integration; next week we plan to wire ProjectFile into an initial ZIP parsing flow, further break down parser tasks and test targets


## Week 8: Oct 19-Oct 26

### Tasks worked on:
![Svens Tasks for W8](./imagesForSvenLogs/w8.png)

## Weekly Goals Recap:

This week, My main focus was on distinguishing individual projects from collaborative projects as outlined in [Issue #47](https://github.com/COSC-499-W2025/capstone-project-team-20/issue/47) which were resolved in [Pull #101](https://github.com/COSC-499-W2025/capstone-project-team-20/pull/101). This will become a generalist feature once we integrate document handling but for the moment I handled git based authorships gathered from any projects "/.git" directory to inventory the authors for the purpose of deliniating individual commits from the rest of the team who collaborated. I plan on integrating our new database scheme into this so that we can store these results for persistent storage.


### New Issues:
I also created some new issues this week in response to teammate feedback and future development goals
- [Issue #113](https://github.com/COSC-499-W2025/capstone-project-team-20/issues/113)
- [Issue #123](https://github.com/COSC-499-W2025/capstone-project-team-20/issues/123)
- [Issue #124](https://github.com/COSC-499-W2025/capstone-project-team-20/issues/124)


### Code Reviews:

- **PR #93 - Refactor ConfigManager to inherit from StorageManager (Dylan)**: Reviewed architectural refactoring that improves code reusability and maintains separation of concerns within the system.
- **PR #110 - Tests for ZipParser (Lex)** : Reviewed comprehensive test coverage for the ZipParser component, ensuring proper validation and error handling mechanisms.
- **PR #122 - ZipParser Directory BugFix (Lex)** : In PR #110 I mentioned a potential edge case with directory naming within the zip which has been resolved with this PR

### Problems Encountered:

Due to it being the midterm season I've had to divert my attention at times to other classes to study, but otherwise no real issues.

### Looking Ahead:

As I said, I am planning on addressing some minor refactorization in the new ``GitRepoAnalyzer`` class I created this week along with working on our plaintext handling. I would also like if we could get some kind of frontend attached to the application soon so that we can display these statistical findings so I'd like to get going with that hopefully soon.

## Week 9: Oct 26th-Nov 2nd

### Tasks worked on:
**N/A** Evaluations were not available as they shut down early accidentally

### Weekly Goals Recap:
This week, my primary focus was on implementing a robust document handling system as outlined in **Issue #124**. The objective was to create a flexible and modular tool for extracting plaintext content from common document formats (`.txt`, `.pdf`, `.docx`). The development process involved several architectural refinements to ensure the system was decoupled, testable, and aligned with future development goals.

The final implementation centers on a new `DocumentScraper` module, which orchestrates the extraction process by traversing a directory of files. The core logic is now integrated directly into the main application workflow, where `main.py` calls `ZipParser` to extract a user-provided archive into a temporary directory, and then passes that directory to the `DocumentScraper` for processing. This provides a centralized yet modular approach, with the extracted text aggregated into a lookup table for future use with analytical tools or LLM pipelines.

### New Issues:
I also created a new issue this week to address the user experience of file input, as handling zip files exclusively can be cumbersome for testing and for the end-user.
*   **Issue #151**: Expand accepted input to unzipped files and folders

### Code Reviews:
*   **PR #144 - Concrete Implementation of Language Detector (dylanstephenalexander)**: Reviewed the successful merge of a new language detection feature, enhancing the project's analytical capabilities.
*   **PR #140 - Refactor StorageManager get_all() to return a Generator (dylanstephenalexander)**: Reviewed an open pull request aimed at optimizing memory usage by refactoring `get_all()` to use a generator, which is particularly useful for handling large datasets.

### Problems Encountered:
No significant problems were encountered this week. Development proceeded smoothly, with the main challenge being the iterative refinement of the system's architecture to find the optimal balance between integration and modularity.

### Looking Ahead:
With the foundation for document handling now in place, the immediate next step is to address **Issue #151** by expanding the application's input handling to accept direct file and folder paths. Following that, I plan to explore how to best utilize the aggregated text from the `DocumentScraper`, either by piping it into a stylistic analysis tool or an LLM for deeper insights. I also plan to expand the `document_handler` to support a wider range of file types as needed.


## Week 11: Nov 10th-Nov 16th

### Tasks worked on:
**PR #168 - Refactor and attach code analysis to storage**: Completed comprehensive architectural refactoring of the Git repository analysis workflow, extracting larger methods from `GitRepoAnalyzer` into a utility class `RepoFinder.py`. Repositioned `GitRepoAnalyzer` as a central orchestrator managing the entire find-analyze-persist lifecycle, reducing complexity in `main.py`. Implemented an "upsert" (update/insert) mechanism in `ProjectManager` to prevent duplicate project records in the database. Resolved a `NameError` in PDF document scraping logic by correcting `pypdf` library usage.

_Due to the peer eval window closing on the 9th, I was not able to get a screenshot in time_

### Weekly Goals Recap:
The primary focus this week was on improving the architectural integrity of the codebase through strategic refactoring. The refactoring effort consolidated responsibilities into appropriately scoped modules, transforming `GitRepoAnalyzer` from a monolithic implementation into a clean orchestrator pattern. This separation of concerns enhances testability and maintainability while ensuring the application's data persistence layer remains consistent and free of duplicate entries.

Architectural improvements included replacing flawed integration tests with focused unit tests utilizing `unittest.mock` for component isolation, while retaining real repository fixtures for core Git analysis validation. The implementation addresses issues #113 and #123.

### Code Reviews:
*   **PR #169 - ProgressBar x ZipParser (Lex)**: Reviewed user experience enhancement that introduces a progress bar to the ZipParser extraction process alongside print formatting improvements for a smoother user experience, closing issue #160.

### Problems Encountered:
Initial integration tests were failing due to architectural limitations in the original design. The refactoring addressed these limitations by decomposing monolithic methods and establishing clearer component boundaries, enabling more robust and isolated unit testing.

### Looking Ahead:
With the architectural foundation now solidified through improved separation of concerns and the upsert mechanism preventing data inconsistencies, the next phase will focus on expanding the application's capabilities while maintaining the established modularity and testability standards.

## Week 12: Nov 17th-Nov 24th

### Tasks worked on:
![Svens Tasks for W12](./imagesForSvenLogs/w12.png)

### Weekly Goals Recap:
This week, I completed two significant feature implementations that enhance the application's Git repository analysis capabilities. **PR #208** introduced user selection and configuration functionality, enabling users to identify themselves from a repository's commit history and persist their selection across sessions using the `ConfigManager`. This feature prompts users to select their username(s) from discovered Git authors and stores the selection for future analyses, streamlining the workflow for returning users.

**PR #209** built upon this foundation by implementing contribution aggregation and share calculation based on lines of code (LOC). The new `ContributionAnalyzer` module performs comprehensive Git repository analysis, tracking per-author statistics including lines added/deleted, commit counts, files touched, and categorizing contributions by type (code, tests, documentation). The system aggregates selected users' contributions and calculates their proportional share relative to the entire project, with results displayed through a formatted presentation layer. Both implementations maintain strict separation of concerns, with `ProjectAnalyzer` orchestrating the workflow, `ContributionAnalyzer` handling Git analysis, and `ConfigManager` managing persistent configuration.


### New Issues:
Created several issues to address architectural improvements and user experience enhancements:
*   **Issue #198**: Refactor username selection workflow to improve user experience
*   **Issue #199**: Implement contribution visualization and export functionality
*   **Issue #213**: Enhance contribution categorization heuristics
*   **Issue #214**: Add support for contribution analysis across multiple repositories

### Code Reviews:
*   **PR #206 - Feature/code metrics analyzer (Kaan)**: Reviewed comprehensive code metrics analysis implementation that tracks complexity, maintainability, and code quality indicators across the codebase.
*   **PR #201 - fix: make load_zip more robust (Dylan)**: Reviewed improvements to ZIP file loading that enhance input validation and error handling for malformed or edge-case archive structures.
*   **PR #196 - Filter Unwanted Files in ZipParser Tree Generation (Dylan)**: Reviewed refinements to the ZipParser that implement intelligent filtering to exclude system metadata and unwanted files from the parsed tree structure.
*   **PR #172 - Add core skill domain models and patterns (Kaan)**: Reviewed foundational domain modeling work establishing skill detection patterns and core data structures for the skill analysis subsystem.

### Problems Encountered:
Encountered merge conflicts when integrating test suites due to concurrent development on `main` branch. The conflicts arose from new `clean_path()` tests added to `main` that tested functionality outside the scope of the username selection feature branch. Other than that no real issues with development.

### Looking Ahead:
With the core contribution analysis infrastructure now established, next week's focus will shift toward finalizing the user-facing output report and implementing export functionality to address Issue #199. I also plan to tackle **Issue #151** by expanding the application's input handling to accept direct file and folder paths in addition to ZIP archives, improving the development and testing workflow. Following these user experience enhancements, I intend to explore more sophisticated contribution visualization options and consider implementing the multi-repository analysis capabilities outlined in Issue #214.
