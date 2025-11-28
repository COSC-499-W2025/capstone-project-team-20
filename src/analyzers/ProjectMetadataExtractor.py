from datetime import datetime
import json, subprocess
from pathlib import Path
from typing import Dict, Optional, List


from src.FileCategorizer import FileCategorizer


class ProjectMetadataExtractor:
   @classmethod
   def from_subfolder(cls, root_folder, subfolder_path: str):
       """
       Build a ProjectMetadataExtractor from a subfolder of the ZIP-parsed tree.
       `subfolder_path` is something like: 'cosc_304 repository' or 'Project/'
       """


       parts = subfolder_path.strip("/").split("/")


       node = root_folder
       for part in parts:
           found = None
           for sub in node.subdir:
               if sub.name == part:
                   found = sub
                   break


           if found is None:
               raise ValueError(f"Subfolder '{subfolder_path}' not found inside ZIP tree.")
           node = found


       return cls(node)




   def __init__(self, root_folder):
       self.root = root_folder
       self.categorizer = FileCategorizer()
  
   def collect_all_files(self):
       """Traverses project folder tree and collects all file objects., files are NOT (!!!) ignored here
       Raw ProjectFile objects from ZipParser
       Ignored files will be filtered later during categorization
       """
       all_files = []
       stack = [self.root]


       while stack:
           folder = stack.pop()
           all_files.extend(folder.children)
           for sub in folder.subdir:
               stack.append(sub)


       return all_files
  
   def compute_time_and_size_summary(self, files) -> Optional[Dict]:
       """Compute file size and file date for a list of files"""
       timestamps = []
       sizes = []


       for f in files:
           if f.last_modified is not None:
               timestamps.append(f.last_modified)
          
           if f.size is not None:
               sizes.append(f.size)


       if not timestamps:
           print("No valid timestamps.")
           return None
      
       earliest = min(timestamps)
       latest = max(timestamps)


       duration_days = (latest - earliest).days
       total_size = sum(sizes)
       total_files = len(files)
      
       avg_kb = round((total_size/ max(total_files, 1)) / 1024, 2)
     
       return {
           "total_files": total_files,
           "total_size_kb": round(total_size / 1024, 2),
           "total_size_mb": round(total_size / (1024 * 1024), 2),
           "average_file_size_kb": avg_kb,
           "start_date": earliest.strftime("%Y-%m-%d"),
           "end_date": latest.strftime("%Y-%m-%d"),
           "duration_days": duration_days
       }
  
   def compute_category_summary(self, files: List) -> Dict[str, Dict[str, float]]:
       """Builds list of dictionaries suitable for FileCategorizer
       Uses **relative paths from inside the ZIP**
       """
       categorized_input = []
       for f in files:
           rel_path = f.full_path


           categorized_input.append({
               "path": rel_path,
               "language": getattr(f, "language", "Unknown")
           })


       return self.categorizer.compute_metrics(categorized_input)
   
   def _get_git_dates(self, repo_path: str):
    """
    Extracts project start/end dates from real Git history.
    Returns (earliest_datetime, latest_datetime) or None if Git fails.
    """
    try:
        # earliest commit
        first = subprocess.check_output(
            ["git", "log", "--reverse", "--pretty=format:%ad", "--date=short"],
            cwd=repo_path
        ).decode().splitlines()[0]

        # latest commit
        last = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%ad", "--date=short"],
            cwd=repo_path
        ).decode().strip()

        first_dt = datetime.strptime(first, "%Y-%m-%d")
        last_dt = datetime.strptime(last, "%Y-%m-%d")

        return first_dt, last_dt
    except:
        return None
  
   def extract_metadata(self, repo_path=None):
       """Runs metadata + category analysis for a project
       Ignores are applied during categorization.
       """
       all_files = self.collect_all_files()
       if not all_files:
           print("No files in this project tree")
           return None
      
       summary = self.compute_time_and_size_summary(all_files)
       category_summary = self.compute_category_summary(all_files)

       # Git history override for proper dates
       if repo_path:
           git_dir = Path(repo_path) / ".git"
           if git_dir.exists():
               git_dates = self._get_git_dates(repo_path)
               if git_dates:
                   earliest, latest = git_dates
                   duration = (latest - earliest).days

                   summary["start date"] = earliest.strftime("%Y-%m-%d")
                   summary["end_date"] = latest.strftime("%Y-%m-%d")
                   summary["duration_days"] = duration

       full_summary = {
           "project_metadata": summary,
           "category_summary": category_summary
       }


       if full_summary:
           print("\n===== Project metadata summary: =====")
           print(json.dumps(full_summary, indent=2))
       return full_summary