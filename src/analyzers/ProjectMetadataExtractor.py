from datetime import datetime
import json
from typing import Dict, Optional, List

class ProjectMetadataExtractor:

    def __init__(self, root_folder):
        self.root = root_folder
    
    def collect_all_files(self):
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

        earliest = min(timestamps)
        latest = max(timestamps)

        duration_days = (latest - earliest).days
        total_size = sum(sizes)
        total_files = len(files)
        average_file_size_kb = 0

        if total_files > 0:
            average_file_size_kb = round(total_size/total_files)/1024

        summary = {
            "total_files: ": total_files,
            "total_size_kb: ": round(total_size/ 1024, 2),
            "total_size_mb: ": round(total_size/ (1024*1024), 2),
            "average_file_size_kb: ": round(average_file_size_kb, 2),
            "start_date: ": earliest.strftime("%Y-%m-%d"),
            "end_date: ": latest.strftime("%Y-%m-%d"),
            "duration_days: ": duration_days
        }
    
    def extract_metadata(self):
        files = self.collect_all_files()
        if len(files) == 0:
            print("No files in this project tree!")
            return None
        
        summary = self.compute_time_and_size_summary(files)
        if summary:
            print("\nProject metadata summary: ")
            print(json.dumps(summary, indent=2))
        return summary