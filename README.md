[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510301&assignment_repo_type=AssignmentRepo)
# Project-Starter
Please use the provided folder structure for your project. You are free to organize any additional internal folder structure as required by the project. 

```
.
├── docs                    # Documentation files
│   ├── contract            # Team contract
│   ├── proposal            # Project proposal 
│   ├── design              # UI mocks
│   ├── minutes             # Minutes from team meetings
│   ├── logs                # Team and individual Logs
│   └── ...          
├── src                     # Source files (alternatively `app`)
├── tests                   # Automated tests 
├── utils                   # Utility files
└── README.md
```

Please use a branching workflow, and once an item is ready, do remember to issue a PR, review, and merge it into the master branch.
Be sure to keep your docs and README.md up-to-date.


DFD Level 1:

https://lucid.app/lucidchart/13a08813-0a92-4798-84d0-2930be2d6aab/edit?page=0_0&invitationId=inv_bf1a126c-f925-4868-bae1-2bdfacdd4bf7#

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