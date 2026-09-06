import os
from pathlib import Path


def list_files(path=""):

    path = Path(path or Path.cwd())
    print(f"📁 {path}\n")

    entries = sorted(os.scandir(path), key=lambda e: (e.is_dir(), e.name.lower()))
    for entry in entries:
        if entry.is_dir():
            n_children = len(os.listdir(entry.path))
            print(f"  📁 {entry.name}/  ({n_children} items)")
        else:
            size = entry.stat().st_size
            if size >= 1_048_576:
                size_str = f"{size / 1_048_576:.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"  📄 {entry.name}  ({size_str})")

if __name__ == "__main__":
    list_files()