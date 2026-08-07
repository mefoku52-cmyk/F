import os
import fnmatch
from dataclasses import dataclass, asdict
from typing import List, Optional, Set, Dict, Any


@dataclass
class FileInfo:
    path: str
    rel_path: str
    size: int
    ext: str
    mtime: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def collect_files(
    root: str,
    exclude_dirs: Optional[Set[str]] = None,
    include_patterns: Optional[Set[str]] = None,
) -> List[FileInfo]:
    if exclude_dirs is None:
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
            ".gradle",
            "build",
            ".idea",
            ".pytest_cache",
            "dist",
            "*.egg-info",
            "forensicsuite_report",
            "forensicsuite_cache",
        }

    results: List[FileInfo] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_dirs)
        ]
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            try:
                stat = os.stat(full_path)
            except OSError:
                continue
            rel_path = os.path.relpath(full_path, root)
            ext = os.path.splitext(filename)[1].lower()
            if include_patterns:
                if not any(fnmatch.fnmatch(filename, pat) for pat in include_patterns):
                    continue
            results.append(
                FileInfo(
                    path=full_path,
                    rel_path=rel_path,
                    size=stat.st_size,
                    ext=ext,
                    mtime=stat.st_mtime,
                )
            )
    return results
