import json

KEYWORDS_PATH = "/Users/stephentaykor/Desktop/flipper_Simulation/Flipper_AI/usable_category_paths_fixed_final.txt"
PROGRESS_FILE = "/Users/stephentaykor/Desktop/flipper_Simulation/my_items_safe/progress.json"

# Load total keywords
with open(KEYWORDS_PATH, 'r') as f:
    total_keywords = len([line.strip() for line in f if line.strip()])

# Load progress
with open(PROGRESS_FILE, 'r') as f:
    progress = json.load(f)
completed = len(progress.get('done', {}))

remaining = total_keywords - completed
print(f"Total keywords: {total_keywords}")
print(f"Completed: {completed}")
print(f"Remaining: {remaining}")