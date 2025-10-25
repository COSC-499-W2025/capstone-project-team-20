from datetime import datetime
import json

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
    
    def extract_metadata(self):
        files = self.collect_all_files()
        if len(files) == 0:
            print("No files in this project tree!")
            return None
        
        timestamps = []
        sizes = []

        for f in files:
            if f.last_modified is not None:
                timestamps.append(f.last_modified)
            
            if f.size is not None:
                sizes.append(f.size())

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
            "total files: ": total_files,
            "total size in kb: ": round(total_size/ 1024, 2),
            "average file size in kb:": average_file_size_kb,
            "start date: ": earliest.strftime("%Y-%m-%d"),
            "end date: ": latest.strftime("%Y-%m-%d"),
            "duration in days: ": duration_days
        }

        print("\n Project metadata summary: ")
        print(json.dumps(summary, indent=2))