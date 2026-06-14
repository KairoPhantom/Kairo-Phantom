#!/usr/bin/env python3
"""
eval_integrity_guard.py - Kairo Phantom CI integrity guard for evaluation scripts.

Fails the build when an evaluation script:
  (1) uses random.* (or numpy.random.*) - which can be used to FABRICATE results, or
  (2) intercepts / mocks the model call so call_model() / query_ollama() returns
      canned output instead of hitting the real backend.

This protects against two regressions caught in audit:
  - B-15: eval_model.py fabricated base-vs-fine-tuned pass rates with random.random()
  - eval_schema_compliance.py historically short-circuited call_model() with mock JSON
           (later remediated; this guard keeps it from coming back)

Usage:
  python scripts/ci/eval_integrity_guard.py
  python scripts/ci/eval_integrity_guard.py --paths scripts/training/eval_model.py
  python scripts/ci/eval_integrity_guard.py --list        # show which files are in scope

Exit codes: 0 = clean | 1 = violations found | 2 = guard error.

Escape hatch: a *single* line may opt out of the random ban with an inline pragma
that MUST carry a justification, e.g.:
    rows = random.sample(CASES, k=5)   # ci-guard:allow-random reason=seeded prompt shuffle, not scoring
The guard prints every allowance it honored so reviewers can audit them.
"""
from __future__ import annotations

import argparse
import ast
import glob
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# --- Configuration -----------------------------------------------------------

# Glob patterns (relative to repo root) that define an "evaluation script".
DEFAULT_EVAL_GLOBS: List[str] = [
    "scripts/eval_*.py",
    "scripts/**/eval_*.py",
    "scripts/**/*_eval.py",
    "scripts/training/eval_model.py",
    "**/benchmarks/**/*.py",
]

# Functions that MUST perform a real backend call (no canned returns).
MODEL_CALL_FUNCS = {
    "call_model", "query_ollama", "query_model", "query_litellm", "run_inference",
}

# Substrings that signal a genuine outbound request inside a model-call function.
NETWORK_MARKERS = (
    "urlopen", "urllib.request", "requests.", "httpx.", "http.client",
    "openai", "litellm", "chat.completions", "/v1/chat/completions",
    "localhost:11434", "localhost:4000", "127.0.0.1", "socket.",
)

# Markers that strongly indicate hard-coded interception of specific prompts.
MOCK_MARKERS = (
    "MOCK", "mock_response", "FAKE", "stub_response", "canned",
    "KairoDocWriter", "KairoExcelWriter", "KairoPptxWriter",
)

BANNED_RANDOM_ROOTS = {"random"}                 # stdlib `random`
BANNED_RANDOM_NUMPY = {"numpy", "np"}            # `numpy.random` / `np.random`
ALLOW_PRAGMA = "ci-guard:allow-random"


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  [{self.rule}]  {self.message}"


# --- Helpers -----------------------------------------------------------------

def dotted_name(node: ast.AST) -> Optional[str]:
    """Return the dotted name for a Name/Attribute chain, else None."""
    parts: List[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def line_has_allow_pragma(src_lines: List[str], lineno: int) -> Optional[str]:
    """Return the justification text if the line opts out, else None."""
    if 1 <= lineno <= len(src_lines):
        text = src_lines[lineno - 1]
        if ALLOW_PRAGMA in text:
            after = text.split(ALLOW_PRAGMA, 1)[1].strip()
            return after or "(no reason given)"
    return None


# --- Checks ------------------------------------------------------------------

def check_random_usage(tree: ast.AST, path: str, src_lines: List[str],
                       allowances: List[str]) -> List[Finding]:
    findings: List[Finding] = []
    import_findings: List[Finding] = []  # Collected separately — may be suppressed
    usage_violations = 0  # Count of raw (non-pragma'd) random usages

    for node in ast.walk(tree):
        # import random  /  import numpy.random
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if alias.name in BANNED_RANDOM_ROOTS or alias.name == "random" \
                        or (root in BANNED_RANDOM_NUMPY and alias.name.endswith(".random")):
                    # Check if the import line itself carries the pragma
                    reason = line_has_allow_pragma(src_lines, node.lineno)
                    if reason is not None:
                        allowances.append(
                            f"{path}:{node.lineno}  honored {ALLOW_PRAGMA} -> {reason}")
                    else:
                        import_findings.append(Finding(path, node.lineno, "no-random-import",
                            f"eval scripts must not import '{alias.name}'"))
        # from random import ...  /  from numpy.random import ...
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in BANNED_RANDOM_ROOTS or mod.endswith("numpy.random") or mod == "numpy.random":
                reason = line_has_allow_pragma(src_lines, node.lineno)
                if reason is not None:
                    allowances.append(
                        f"{path}:{node.lineno}  honored {ALLOW_PRAGMA} -> {reason}")
                else:
                    import_findings.append(Finding(path, node.lineno, "no-random-import",
                        f"eval scripts must not import from '{mod}'"))
        # random.<x>(...)  /  numpy.random.<x>  /  np.random.<x>
        elif isinstance(node, ast.Attribute):
            name = dotted_name(node)
            if not name:
                continue
            head = name.split(".")
            hit = (head[0] in BANNED_RANDOM_ROOTS) or \
                  (len(head) >= 2 and head[0] in BANNED_RANDOM_NUMPY and head[1] == "random")
            if hit:
                reason = line_has_allow_pragma(src_lines, node.lineno)
                if reason is not None:
                    allowances.append(f"{path}:{node.lineno}  honored {ALLOW_PRAGMA} -> {reason}")
                else:
                    usage_violations += 1
                    findings.append(Finding(path, node.lineno, "no-random-usage",
                        f"'{name}(...)' in an eval script can fabricate results; "
                        f"use real model output or add '{ALLOW_PRAGMA} reason=...' if truly benign"))

    # Transitively suppress import findings if ALL usages were covered by pragmas.
    # Rationale: `ci-guard:allow-random` on every usage site proves the import is
    # benign (e.g. `random.sample` for prompt shuffling). The spec intends this case
    # to exit 0 (EVAL_INTEGRITY_GUARD.md §8 allowed_shuffle fixture).
    if import_findings and usage_violations == 0 and any(ALLOW_PRAGMA in a for a in allowances):
        for f in import_findings:
            allowances.append(
                f"{f.path}:{f.line}  [{f.rule}] suppressed — all usages carry {ALLOW_PRAGMA} pragma")
    else:
        findings.extend(import_findings)

    return findings



def check_model_call_integrity(tree: ast.AST, path: str) -> List[Finding]:
    findings: List[Finding] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in MODEL_CALL_FUNCS:
            continue

        segment = ast.get_source_segment_safe(node)
        net_line = first_network_line(node)
        has_network = net_line is not None

        if not has_network:
            findings.append(Finding(path, node.lineno, "call-must-hit-backend",
                f"'{node.name}()' performs no real backend request "
                f"(expected one of: {', '.join(sorted(set(m.strip('.') for m in NETWORK_MARKERS)))})"))

        # Mock markers anywhere in the function body.
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if any(m in sub.value for m in MOCK_MARKERS):
                    findings.append(Finding(path, getattr(sub, "lineno", node.lineno),
                        "no-mock-interception",
                        f"'{node.name}()' references a mock/interception marker in a string literal"))
                    break

        # A constant return that fires BEFORE any real network call = interception.
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and is_constant_payload(sub.value):
                if (net_line is None) or (sub.lineno < net_line):
                    findings.append(Finding(path, sub.lineno, "no-mock-interception",
                        f"'{node.name}()' returns a hard-coded payload before any backend call "
                        f"- canned/intercepted responses are banned in eval"))
    return findings


def is_constant_payload(value: Optional[ast.AST]) -> bool:
    """True if a return value is a literal string/dict/list (a canned response)."""
    if value is None:
        return False
    if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value.strip():
        return True
    if isinstance(value, (ast.Dict, ast.List, ast.Tuple)):
        return True
    return False


def first_network_line(func: ast.AST) -> Optional[int]:
    """Lowest line number at which a network marker appears inside the function."""
    best: Optional[int] = None
    for sub in ast.walk(func):
        text = None
        if isinstance(sub, (ast.Attribute, ast.Name)):
            text = dotted_name(sub)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            text = sub.value
        if not text:
            continue
        if any(m in text for m in NETWORK_MARKERS):
            ln = getattr(sub, "lineno", None)
            if ln is not None and (best is None or ln < best):
                best = ln
    return best


# get_source_segment can return None on some nodes; wrap it safely.
def _safe_segment(node: ast.AST) -> str:  # pragma: no cover - tiny shim
    try:
        return ast.get_source_segment(_SOURCE_CACHE.get(id(node), ""), node) or ""
    except Exception:
        return ""


ast.get_source_segment_safe = _safe_segment  # type: ignore[attr-defined]
_SOURCE_CACHE: dict = {}


# --- Discovery + driver ------------------------------------------------------

def discover(root: Path, globs: List[str]) -> List[Path]:
    seen = {}
    for pattern in globs:
        for match in glob.glob(str(root / pattern), recursive=True):
            p = Path(match)
            if p.suffix == ".py" and p.is_file():
                resolved = p.resolve()
                p_str = resolved.as_posix()
                # Exclude this guard script itself and any test scripts under scripts/ci/tests/
                if "scripts/ci/eval_integrity_guard.py" in p_str or "scripts/ci/tests" in p_str:
                    continue
                seen[resolved] = p
    return sorted(seen.values())


def check_security_violations(src: str, path: str) -> List[Finding]:
    if "eval_integrity_guard.py" in path:
        return []
    import re
    findings: List[Finding] = []
    banned = [
        (r"\beval\(", "no-eval", "Use of eval() is banned"),
        (r"\bexec\(", "no-exec", "Use of exec() is banned"),
        (r"\.system\(", "no-os-system", "Use of system() is banned"),
        (r"subprocess\.Popen\(", "no-popen", "Use of Popen() is banned"),
        (r"\.\./\.\./\.\.", "no-path-traversal", "Relative path traversal is banned"),
        (r"/etc/(passwd|shadow)", "no-path-traversal", "Accessing system files is banned"),
        (r"/absolute/path", "no-abs-path", "Absolute path usage is banned"),
        (r"(API_KEY|GITHUB_TOKEN|password)\s*=\s*['\"].+['\"]", "no-secrets", "Hardcoded secrets are banned"),
    ]
    lines = src.splitlines()
    for idx, line in enumerate(lines, 1):
        for pattern, rule, msg in banned:
            if re.search(pattern, line):
                findings.append(Finding(path, idx, rule, msg))
    return findings


def scan_file(path: Path, root: Path) -> (List[Finding], List[str]):
    rel = str(path.relative_to(root)) if root in path.parents or path == root else str(path)
    src = path.read_text(encoding="utf-8")
    src_lines = src.splitlines()
    tree = ast.parse(src, filename=rel)
    allowances: List[str] = []
    findings = check_random_usage(tree, rel, src_lines, allowances)
    findings += check_model_call_integrity(tree, rel)
    findings += check_security_violations(src, rel)
    return findings, allowances


def check_ci_workflow_integrity(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    workflow_files = [
        root / ".github" / "workflows" / "ci.yml",
        root / ".github" / "workflows" / "eval-integrity.yml",
    ]
    for wf in workflow_files:
        if not wf.is_file():
            continue
        rel = str(wf.relative_to(root))
        try:
            content = wf.read_text(encoding="utf-8")
            for line_idx, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                part_before_comment = line.split("#", 1)[0]
                if "|| true" in part_before_comment:
                    findings.append(Finding(rel, line_idx, "no-ci-bypass",
                        "CI steps must not bypass failures using '|| true'"))
                if "continue-on-error: true" in part_before_comment:
                    findings.append(Finding(rel, line_idx, "no-ci-bypass",
                        "CI steps must not bypass failures using 'continue-on-error: true'"))
        except Exception as e:
            findings.append(Finding(rel, 1, "ci-read-error", f"Failed to check workflow file: {e}"))
    return findings


def check_facts_file_integrity(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    facts_file = root / "Kairo.facts"
    if not facts_file.is_file():
        return findings
    rel = str(facts_file.relative_to(root))
    try:
        content = facts_file.read_text(encoding="utf-8")
        current_fact_type = ""
        for line_idx, line in enumerate(content.splitlines(), 1):
            line_str = line.strip()
            if line_str.startswith("@implemented:"):
                current_fact_type = "implemented"
            elif line_str.startswith("@spec:"):
                current_fact_type = "spec"
            elif line_str.startswith("@draft:"):
                current_fact_type = "draft"
            elif line_str.startswith("command:") and current_fact_type == "implemented":
                cmd_str = line_str.split("command:", 1)[1].strip()
                lower = cmd_str.lower()
                is_vacuous = False
                if "--version" in lower or "-V" in cmd_str:
                    is_vacuous = True
                else:
                    for word in cmd_str.split():
                        w = "".join(c for c in word if c.isalnum())
                        if w == "true" or w == "echo":
                            is_vacuous = True
                            break
                if is_vacuous or not cmd_str:
                    findings.append(Finding(rel, line_idx, "no-vacuous-facts",
                        f"Vacuous fact verification command not allowed: '{cmd_str}'"))
    except Exception as e:
        findings.append(Finding(rel, 1, "facts-read-error", f"Failed to check facts file: {e}"))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Kairo eval integrity guard")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--paths", nargs="*", help="explicit files to scan (overrides globs)")
    ap.add_argument("--list", action="store_true", help="list in-scope files and exit")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = discover(root, DEFAULT_EVAL_GLOBS)

    if args.list:
        for t in targets:
            print(t)
        return 0

    if not targets:
        print("eval-integrity-guard: no evaluation scripts matched; nothing to check.")
        return 0

    all_findings: List[Finding] = []
    all_allowances: List[str] = []
    for t in targets:
        try:
            findings, allowances = scan_file(t, root)
        except SyntaxError as e:
            print(f"eval-integrity-guard: ERROR parsing {t}: {e}", file=sys.stderr)
            return 2
        all_findings.extend(findings)
        all_allowances.extend(allowances)

    all_findings.extend(check_ci_workflow_integrity(root))
    all_findings.extend(check_facts_file_integrity(root))

    print(f"eval-integrity-guard: scanned {len(targets)} eval script(s).")
    for a in all_allowances:
        print(f"  ALLOW  {a}")

    if not all_findings:
        print("eval-integrity-guard: PASS - no fabricated metrics or mock interception found.")
        return 0

    print(f"\neval-integrity-guard: FAIL - {len(all_findings)} violation(s):\n", file=sys.stderr)
    for f in sorted(all_findings, key=lambda x: (x.path, x.line)):
        print(f"  {f}", file=sys.stderr)
    print("\nFix: eval scripts must derive pass/fail from real model output, and")
    print("call_model()/query_ollama() must hit the live backend (no canned returns).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
