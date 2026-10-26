"""Work with paths and save structured data as JSON."""

import json
from pathlib import Path

data = {"topic": "Python", "completed": False}
output_path = Path("learning_progress.json")

output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
loaded_data = json.loads(output_path.read_text(encoding="utf-8"))
print("Saved and loaded:", loaded_data)

"""
Exercises:
1. Write a short note to a text file, then read and print it.
2. Save a list of completed lessons as JSON and load it back.
3. Check whether a file exists before trying to read it.
4. Read a CSV file using the standard-library `csv` module and summarize a
   column.

The example creates learning_progress.json in the current working directory.
"""
