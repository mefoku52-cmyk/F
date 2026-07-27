import hashlib
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
TEXT_LIKE_EXTENSIONS = {
    ".py", ".kt", ".java", ".xml", ".md", ".txt", ".json", ".yaml", ".yml",
    ".gradle", ".kts", ".html", ".css", ".js", ".ts",
}


class FilesystemPlugin(Plugin):
    @property
    def name(self) -> str:
        return "filesystem"

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings = []
        total_size = sum(f.size for f in files)
        by_extension: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
        for f in files:
            ext = f.ext or "(bez prípony)"
            by_extension[ext]["count"] += 1
            by_extension[ext]["size"] += f.size

        # Prázdne súbory
        empty_files = [f.rel_path for f in files if f.size == 0]
        for path in empty_files:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.LOW,
                message=f"Prázdny súbor: {path}",
                location=path,
                confidence=1.0,
            ))

        # Duplicity
        duplicates = self._find_duplicates(files)
        for group in duplicates:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.MEDIUM,
                message=f"Duplicitné súbory: {', '.join(group[:3])}{'...' if len(group) > 3 else ''}",
                location=group[0],
                confidence=0.9,
                metadata={"duplicate_group": group},
            ))

        # Orphaned images
        orphaned = self._find_orphaned_images(files)
        for path in orphaned:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.INFO,
                message=f"Osamelý obrázok: {path}",
                location=path,
                confidence=0.6,
            ))

        return findings

    def _find_duplicates(self, files: List[FileInfo]) -> List[List[str]]:
        by_size: Dict[int, List[FileInfo]] = defaultdict(list)
        for f in files:
            if f.size == 0:
                continue
            by_size[f.size].append(f)

        duplicate_groups: List[List[str]] = []
        for size, candidates in by_size.items():
            if len(candidates) < 2:
                continue
            hashes: Dict[str, List[str]] = defaultdict(list)
            for f in candidates:
                digest = self._hash_file_chunked(f.path)
                if digest is not None:
                    hashes[digest].append(f.rel_path)
            for paths in hashes.values():
                if len(paths) > 1:
                    duplicate_groups.append(paths)
        return duplicate_groups

    @staticmethod
    def _hash_file_chunked(path: str, chunk_size: int = 1024 * 1024) -> Optional[str]:
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as fh:
                while True:
                    chunk = fh.read(chunk_size)
                    if not chunk:
                        break
                    sha256.update(chunk)
        except OSError:
            return None
        return sha256.hexdigest()

    def _find_orphaned_images(self, files: List[FileInfo]) -> List[str]:
        images = [f for f in files if f.ext in IMAGE_EXTENSIONS]
        if not images:
            return []
        text_files = [f for f in files if f.ext in TEXT_LIKE_EXTENSIONS]
        haystack_parts = []
        for f in text_files:
            try:
                with open(f.path, "r", encoding="utf-8", errors="ignore") as fh:
                    haystack_parts.append(fh.read())
            except OSError:
                continue
        haystack = "\n".join(haystack_parts)
        orphaned = []
        for img in images:
            stem = os.path.splitext(os.path.basename(img.path))[0]
            if stem and stem not in haystack:
                orphaned.append(img.rel_path)
        return orphaned
