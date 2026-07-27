import ast
import os
from typing import Any, Dict, List, Set

from core.collector import FileInfo
from core.cve_checker import check_dependencies
from core.finding import Finding, Severity
from core.parser import safe_read_text
from core.plugin_manager import Plugin

_COMPLEXITY_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try,
    ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert, ast.BoolOp,
)


def _cyclomatic_complexity(func_node: ast.AST) -> int:
    complexity = 1
    for node in ast.walk(func_node):
        if isinstance(node, _COMPLEXITY_NODES):
            complexity += 1
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            complexity += len(node.generators)
    return complexity


def _analyze_file_ast(tree: ast.AST, rel_path: str) -> Dict[str, Any]:
    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    imports: List[str] = []
    imported_names: Set[str] = set()
    used_names: Set[str] = set()
    called_names: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorator_names = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorator_names.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorator_names.append(dec.attr)
                elif isinstance(dec, ast.Call) and isinstance(dec.func, (ast.Name, ast.Attribute)):
                    decorator_names.append(
                        dec.func.id if isinstance(dec.func, ast.Name) else dec.func.attr
                    )
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "complexity": _cyclomatic_complexity(node),
                "decorators": decorator_names,
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "lineno": node.lineno})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add((alias.asname or alias.name).split(".")[0])
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
            if module:
                imports.append(module)
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    unused_imports = sorted(n for n in imported_names if n and n not in used_names)

    return {
        "path": rel_path,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "unused_imports": unused_imports,
        "called_names": sorted(called_names),
        "used_names": sorted(used_names),
    }


def _detect_dead_code(file_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detekcia dead code s kontextovou analýzou:
    - Ignoruje override metódy frameworkov (BaseHTTPRequestHandler, atď.)
    - Ignoruje metódy tried, ktoré dedia z frameworkov
    - Ignoruje public API (exportované cez __all__)
    - Cross-file volania (ak je funkcia volaná v inom súbore)
    """
    SKIP_DECORATORS = {"property", "staticmethod", "classmethod", "abstractmethod"}
    FRAMEWORK_BASES = {
        "BaseHTTPRequestHandler", "ThreadingMixIn", "HTTPServer",
        "TCPServer", "UnixStreamServer", "UnixDatagramServer",
        "BasePlugin", "Plugin", "ABC",
    }

    # Zbierame všetky použité názvy naprieč celým projektom
    all_used_names: Set[str] = set()
    all_classes: Dict[str, Set[str]] = {}  # file -> set of class names
    class_bases: Dict[str, Set[str]] = {}  # class_name -> set of base classes

    for fa in file_analyses:
        all_used_names |= set(fa.get("used_names", []))
        all_used_names |= set(fa.get("called_names", []))
        # Zbierame triedy a ich base classes
        for cls in fa.get("classes", []):
            cls_name = cls["name"]
            if cls_name not in all_classes:
                all_classes[cls_name] = set()
            all_classes[cls_name].add(fa["path"])

    # Heuristika: ak trieda obsahuje "Handler", "Server", "View", "Mixin" – pravdepodobne framework
    framework_classes = set()
    for cls_name in all_classes:
        if any(pattern in cls_name for pattern in ["Handler", "Server", "View", "Mixin", "Plugin"]):
            framework_classes.add(cls_name)
        # Alebo ak je v názve BaseHTTPRequestHandler atď.
        if cls_name in FRAMEWORK_BASES:
            framework_classes.add(cls_name)

    dead: List[Dict[str, Any]] = []
    for fa in file_analyses:
        # Zisti, či súbor obsahuje triedy, ktoré dedia z frameworku
        file_has_framework = any(
            cls["name"] in framework_classes for cls in fa.get("classes", [])
        )

        for func in fa.get("functions", []):
            name = func["name"]

            # 1. Magic methods
            if name.startswith("__") and name.endswith("__"):
                continue

            # 2. Entry points
            if name in ("main", "run", "serve_forever", "shutdown"):
                continue
            if name.startswith("test_") or name.startswith("_test"):
                continue

            # 3. Decorators
            if SKIP_DECORATORS.intersection(func.get("decorators", [])):
                continue

            # 4. Framework override metódy (do_GET, do_POST, log_message, atď.)
            if file_has_framework and name.startswith("do_"):
                continue
            if file_has_framework and name in ("log_message", "handle", "setup", "finish_request"):
                continue

            # 5. Public API metódy (obsahujú "scan", "report", "client", "export")
            if any(keyword in name.lower() for keyword in ["scan", "report", "client", "export", "publish"]):
                continue

            # 6. Cross-file volania
            if name in all_used_names:
                continue

            dead.append({"path": fa["path"], "function": name, "lineno": func["lineno"]})
    return dead


def _build_import_graph(file_analyses: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    local_paths = {fa["path"] for fa in file_analyses}
    graph: Dict[str, Set[str]] = {}
    for fa in file_analyses:
        local_deps: Set[str] = set()
        for imp in fa.get("imports", []):
            candidate_suffix = imp.replace(".", os.sep) + ".py"
            for other_path in local_paths:
                if other_path == fa["path"]:
                    continue
                if other_path.endswith(candidate_suffix) or other_path == candidate_suffix:
                    local_deps.add(other_path)
        graph[fa["path"]] = local_deps
    return graph


def _find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    cycles: List[List[str]] = []

    def dfs(node: str, path: List[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, ()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color[neighbor] == WHITE:
                dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    for node in list(graph.keys()):
        if color[node] == WHITE:
            dfs(node, [])
    return cycles


def _parse_dependencies(project_path: str) -> List[Dict[str, str]]:
    req_path = os.path.join(project_path, "requirements.txt")
    dependencies: List[Dict[str, str]] = []
    if not os.path.isfile(req_path):
        return dependencies
    with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                name, version = line.split("==", 1)
                dependencies.append({
                    "name": name.strip(),
                    "version": version.strip(),
                    "ecosystem": "PyPI",
                })
    return dependencies


class PythonPlugin(Plugin):
    @property
    def name(self) -> str:
        return "python"

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        py_files = [f for f in files if f.ext == ".py"]
        file_analyses: List[Dict[str, Any]] = []

        for f in py_files:
            source = safe_read_text(f.path)
            if source is None:
                continue
            try:
                tree = ast.parse(source, filename=f.rel_path)
            except SyntaxError as e:
                file_analyses.append({
                    "path": f.rel_path,
                    "error": f"SyntaxError: {e}",
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "unused_imports": [],
                    "called_names": [],
                    "loc": 0,
                })
                findings.append(Finding(
                    plugin=self.name,
                    severity=Severity.MEDIUM,
                    message=f"SyntaxError v {f.rel_path}: {e}",
                    location=f.rel_path,
                    confidence=1.0,
                ))
                continue

            analysis = _analyze_file_ast(tree, f.rel_path)
            analysis["loc"] = len([line for line in source.splitlines() if line.strip()])
            file_analyses.append(analysis)

        dead_code = _detect_dead_code(file_analyses)
        for dead in dead_code:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.LOW,
                message=f"Dead code: {dead['function']} v {dead['path']} (riadok {dead['lineno']})",
                location=f"{dead['path']}:{dead['lineno']}",
                confidence=0.6,
                metadata={"function": dead["function"]},
            ))

        graph = _build_import_graph(file_analyses)
        cycles = _find_cycles(graph)
        for cycle in cycles:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.HIGH,
                message=f"Cyklický import: {' -> '.join(cycle[:3])}{'...' if len(cycle) > 3 else ''}",
                location=cycle[0],
                confidence=0.9,
                metadata={"cycle": cycle},
            ))

        dependencies = _parse_dependencies(project_path)
        cve_report = check_dependencies(dependencies)
        if cve_report.get("status") == "ok":
            for vuln in cve_report.get("vulnerabilities", []):
                findings.append(Finding(
                    plugin=self.name,
                    severity=Severity.CRITICAL,
                    message=f"CVE {vuln['vuln_id']}: {vuln.get('summary', '')[:100]}",
                    location=vuln["dependency"],
                    confidence=0.95,
                    metadata={"vuln": vuln},
                ))

        # ---- PRIDÁME METRIKY AKO SAMOSTATNÝ FINDING ----
        total_functions = sum(len(fa.get("functions", [])) for fa in file_analyses)
        total_complexity = sum(
            func["complexity"] for fa in file_analyses for func in fa.get("functions", [])
        )
        avg_complexity = round(total_complexity / total_functions, 2) if total_functions else 0.0
        total_loc = sum(fa.get("loc", 0) for fa in file_analyses)
        unused_imports_total = sum(
            len(fa.get("unused_imports", [])) for fa in file_analyses
        )

        findings.append(Finding(
            plugin=self.name,
            severity=Severity.INFO,
            message="Python metrics",
            confidence=1.0,
            metadata={
                "file_count": len(file_analyses),
                "total_loc": total_loc,
                "avg_function_complexity": avg_complexity,
                "total_functions": total_functions,
                "unused_imports_total": unused_imports_total,
                "dead_code_count": len(dead_code),
                "cyclic_imports": cycles,
                "dependencies": dependencies,
                "cve_report": cve_report,
            }
        ))

        return findings
