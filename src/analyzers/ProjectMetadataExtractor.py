from datetime import datetime
import json
from typing import Dict, Optional, List

from src.FileCategorizer import FileCategorizer

class ProjectMetadataExtractor:

    def __init__(self, root_folder):
        self.root = root_folder
        self.categorizer = FileCategorizer()
    
    def collect_all_files(self):
        """Traverses project folder tree and collects all file objects."""
        all_files = []
        folder_to_check = [self.root]

        while len(folder_to_check) > 0:
            current_folder = folder_to_check.pop()
            for file in current_folder.children:
                all_files.append(file)
            for sub in current_folder.subdir:
                folder_to_check.append(sub)

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

        if len(timestamps) == 0:
            print("No valid timestamps!!")

        if not timestamps:
            print("No valid timestamps.")
            return None
        
        earliest = min(timestamps)
        latest = max(timestamps)

        duration_days = (latest - earliest).days
        total_size = sum(sizes)
        total_files = len(files)
        average_file_size_kb = 0

        if total_files > 0:
            average_file_size_kb = round((total_size/total_files)/1024, 2) if total_files else 0

        summary = {
            "total_files:": total_files,
            "total_size_kb:": round(total_size / 1024, 2),
            "total_size_mb:": round(total_size/ (1024*1024), 2),
            "average_file_size_kb:": round(average_file_size_kb, 2),
            "start_date:": earliest.strftime("%Y-%m-%d"),
            "end_date:": latest.strftime("%Y-%m-%d"),
            "duration_days:": duration_days
        }
        return summary
    
    def compute_category_summary(self, files: List) -> Dict[str, Dict[str, float]]:
        """Classify files into categories and compute contribution metrics using FileCategorizer"""
        files_for_categorization = []
        for f in files:
            files_for_categorization.append({
                "path": f.file_name if hasattr(f, "file_name") else f.name,
                "language": getattr(f, "language", "Unknown")
            })
        return self.categorizer.compute_metrics(files_for_categorization)
    
    def extract_metadata(self):
        """Runs all metadata and category analysis for this project"""
        self.files = self.collect_all_files()
        if not self.files:
            print("No files in this project tree")
            return None
        
        summary = self.compute_time_and_size_summary(self.files)
        category_summary = self.compute_category_summary(self.files)

        full_summary = {
            "project_metadata": summary,
            "category_summary": category_summary
        }

        if full_summary:
            print("\n===== Project metadata summary: =====")
            print(json.dumps(full_summary, indent=2))
        return full_summary