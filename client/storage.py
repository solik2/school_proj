from pathlib import Path

def ensure_storage_dir(storage_dir: Path):
    storage_dir.mkdir(parents=True, exist_ok=True)

def validate_file_path(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
