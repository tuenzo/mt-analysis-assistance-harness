from pathlib import Path
from .manifest import compute_file_checksum


def scan_directory(workspace_path: Path) -> list[dict]:
    results = []
    for dir_key in ["data/raw", "data/processed", "scripts", "artifacts"]:
        dir_path = workspace_path / dir_key
        if not dir_path.exists():
            continue
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                results.append({
                    "path": str(file_path.relative_to(workspace_path)),
                    "checksum": compute_file_checksum(file_path)
                })
    return results
