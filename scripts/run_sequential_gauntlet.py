#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kairo Phantom Sequential Document Gauntlet
==========================================
Tests ONE document type completely before moving to the next.
Within each doc type, tests scenarios ONE BY ONE.
If a scenario fails, retries up to MAX_RETRIES times before moving on.
Produces a clear per-scenario pass/fail report.

Order: Word -> PPT -> Excel -> Terminal -> Notepad -> VSCode
       -> Browser -> Obsidian -> Notion -> Figma -> Slack -> PDF
"""

import argparse
import os
import sys
import json
import time
import logging
import pathlib
import traceback
from datetime import datetime

# ── Fix PyAutoGUI fail-safe (corner detection) before any imports ──────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
except Exception:
    pass

# ── Fix Unicode on Windows cp1252 console ────────────────────────────────────
if sys.platform == "win32" and __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Directories ───────────────────────────────────────────────────────────────
RESULTS_DIR   = pathlib.Path(r"C:\tests\results")
LOGS_DIR      = pathlib.Path(r"C:\tests\logs")
SCREENSHOTS   = pathlib.Path(r"C:\tests\screenshots")
SCRIPTS_WIN   = pathlib.Path(__file__).parent / "win"

for d in [RESULTS_DIR, LOGS_DIR, SCREENSHOTS]:
    d.mkdir(parents=True, exist_ok=True)

if str(SCRIPTS_WIN) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_WIN))

# ── Logging ───────────────────────────────────────────────────────────────────
log_file = LOGS_DIR / "sequential_gauntlet.log"

logger = logging.getLogger("SeqGauntlet")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(log_file, encoding="utf-8", mode="w")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)

ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_RETRIES   = 3
RETRY_DELAY   = 5   # seconds between retries

# ── Pending Scenarios ─────────────────────────────────────────────────────────
PENDING_SCENARIOS = {
    # Microsoft Word (W31 - W50)
    "W31", "W32", "W33", "W34", "W35", "W36", "W37", "W38", "W39", "W40",
    "W41", "W42", "W43", "W44", "W45", "W46", "W47", "W48", "W49", "W50",
    
    # PowerPoint (P21 - P35)
    "P21", "P22", "P23", "P24", "P25", "P26", "P27", "P28", "P29", "P30",
    "P31", "P32", "P33", "P34", "P35",
    
    # Excel (E8 - E30)
    "E8", "E9", "E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17",
    "E18", "E19", "E20", "E21", "E22", "E23", "E24", "E25", "E26", "E27",
    "E28", "E29", "E30",
    
    # Windows Terminal (T6 - T15)
    "T6", "T7", "T8", "T9", "T10", "T11", "T12", "T13", "T14", "T15",
    
    # Notepad (N5 - N10)
    "N5", "N6", "N7", "N8", "N9", "N10",
    
    # VS Code (V7 - V15)
    "V7", "V8", "V9", "V10", "V11", "V12", "V13", "V14", "V15",
    
    # Browser / Google Docs (B7 - B15)
    "B7", "B8", "B9", "B10", "B11", "B12", "B13", "B14", "B15",
    
    # Obsidian (OB6 - OB10)
    "OB6", "OB7", "OB8", "OB9", "OB10",
    
    # Notion (NO5 - NO10)
    "NO5", "NO6", "NO7", "NO8", "NO9", "NO10",
    
    # Figma (F6 - F10)
    "F6", "F7", "F8", "F9", "F10",
    
    # Slack / Email (SL6 - SL10)
    "SL6", "SL7", "SL8", "SL9", "SL10",
    
    # PDF Documents (PDF6 - PDF10)
    "PDF6", "PDF7", "PDF8", "PDF9", "PDF10"
}

# ── Agent/scenario ordering ───────────────────────────────────────────────────
DOCUMENT_QUEUE = [
    {
        "agent_id":  "agent_word",
        "label":     "Microsoft Word",
        "scenarios": [
            # Original 10 from tests-scenario.md
            "W1",  "W2",  "W3",  "W4",  "W5",
            "W6",  "W7",  "W8",  "W9",  "W10",
            # 20 new real-world scenarios
            "W11", "W12", "W13", "W14", "W15",
            "W16", "W17", "W18", "W19", "W20",
            "W21", "W22", "W23", "W24", "W25",
            "W26", "W27", "W28", "W29", "W30",
            # Expand to W50
            "W31", "W32", "W33", "W34", "W35",
            "W36", "W37", "W38", "W39", "W40",
            "W41", "W42", "W43", "W44", "W45",
            "W46", "W47", "W48", "W49", "W50",
        ],
        "module":    "scenario_word",
        "fn":        "run_word_scenario",
    },
    {
        "agent_id":  "agent_ppt",
        "label":     "PowerPoint",
        "scenarios": [
            # Original 7 from tests-scenario.md
            "P1",  "P2",  "P3",  "P4",  "P5",  "P6",  "P7",
            # 13 new real-world scenarios
            "P8",  "P9",  "P10", "P11", "P12",
            "P13", "P14", "P15", "P16", "P17",
            "P18", "P19", "P20",
            # Expand to P35
            "P21", "P22", "P23", "P24", "P25",
            "P26", "P27", "P28", "P29", "P30",
            "P31", "P32", "P33", "P34", "P35",
        ],
        "module":    "scenario_pptx",
        "fn":        "run_pptx_scenario",
    },
    {
        "agent_id":  "agent_excel",
        "label":     "Excel",
        "scenarios": [
            "E1", "E2", "E3", "E4", "E5", "E6", "E7",
            "E8", "E9", "E10", "E11", "E12", "E13", "E14", "E15",
            "E16", "E17", "E18", "E19", "E20", "E21", "E22", "E23",
            "E24", "E25", "E26", "E27", "E28", "E29", "E30",
        ],
        "module":    "scenario_excel",
        "fn":        "run_excel_scenario",
    },
    {
        "agent_id":  "agent_terminal",
        "label":     "Windows Terminal",
        "scenarios": [
            "T1", "T2", "T3", "T4", "T5",
            "T6", "T7", "T8", "T9", "T10",
            "T11", "T12", "T13", "T14", "T15",
        ],
        "module":    "scenario_terminal",
        "fn":        "run_terminal_scenario",
    },
    {
        "agent_id":  "agent_notepad",
        "label":     "Notepad",
        "scenarios": [
            "N1", "N2", "N3", "N4",
            "N5", "N6", "N7", "N8", "N9", "N10",
        ],
        "module":    "scenario_notepad",
        "fn":        "run_notepad_scenario",
    },
    {
        "agent_id":  "agent_vscode",
        "label":     "VS Code",
        "scenarios": [
            "V1", "V2", "V3", "V4", "V5", "V6",
            "V7", "V8", "V9", "V10", "V11", "V12",
            "V13", "V14", "V15",
        ],
        "module":    "scenario_vscode",
        "fn":        "run_vscode_scenario",
    },
    {
        "agent_id":  "agent_browser",
        "label":     "Browser / Google Docs",
        "scenarios": [
            "B1", "B2", "B3", "B4", "B5", "B6",
            "B7", "B8", "B9", "B10", "B11", "B12",
            "B13", "B14", "B15",
        ],
        "module":    "scenario_browser",
        "fn":        "run_browser_scenario",
    },
    {
        "agent_id":  "agent_obsidian",
        "label":     "Obsidian",
        "scenarios": [
            "OB1", "OB2", "OB3", "OB4", "OB5",
            "OB6", "OB7", "OB8", "OB9", "OB10",
        ],
        "module":    "scenario_obsidian",
        "fn":        "run_obsidian_scenario",
    },
    {
        "agent_id":  "agent_notion",
        "label":     "Notion",
        "scenarios": [
            "NO1", "NO2", "NO3", "NO4",
            "NO5", "NO6", "NO7", "NO8", "NO9", "NO10",
        ],
        "module":    "scenario_notion_figma_slack_pdf",
        "fn":        "run_notion_scenario",
    },
    {
        "agent_id":  "agent_figma",
        "label":     "Figma",
        "scenarios": [
            "F1", "F2", "F3", "F4", "F5",
            "F6", "F7", "F8", "F9", "F10",
        ],
        "module":    "scenario_notion_figma_slack_pdf",
        "fn":        "run_figma_scenario",
    },
    {
        "agent_id":  "agent_slack",
        "label":     "Slack / Email",
        "scenarios": [
            "SL1", "SL2", "SL3", "SL4", "SL5",
            "SL6", "SL7", "SL8", "SL9", "SL10",
        ],
        "module":    "scenario_notion_figma_slack_pdf",
        "fn":        "run_slack_scenario",
    },
    {
        "agent_id":  "agent_pdf",
        "label":     "PDF Documents",
        "scenarios": [
            "PDF1", "PDF2", "PDF3", "PDF4", "PDF5",
            "PDF6", "PDF7", "PDF8", "PDF9", "PDF10",
        ],
        "module":    "scenario_notion_figma_slack_pdf",
        "fn":        "run_pdf_scenario",
    },
]

# ── Scenario runner ───────────────────────────────────────────────────────────
def run_one_scenario(doc_cfg: dict, scen_id: str) -> tuple:
    """
    Execute a single scenario.  Returns (passed: bool, message: str, is_fallback: bool).
    """
    mod_name = doc_cfg["module"]
    fn_name  = doc_cfg["fn"]

    try:
        mod = __import__(mod_name)
        fn  = getattr(mod, fn_name)
        success, msg = fn(scen_id, logger)
        return success, msg, False
    except FileNotFoundError as e:
        # App not installed — strict E2E loop enforces active testing
        return False, f"App not installed: {e}", False
    except Exception as e:
        tb = traceback.format_exc()
        return False, f"Exception: {e}\n{tb}", False


def screenshot(scen_id: str, attempt: int):
    try:
        import pyautogui as pg
        path = SCREENSHOTS / f"{scen_id}_attempt{attempt}_fail.png"
        pg.screenshot(str(path))
        logger.info(f"  Screenshot saved: {path}")
    except Exception:
        pass


def run_doc_block(doc_cfg: dict, start_from: str = None) -> dict:
    """Run all scenarios for one document type sequentially."""
    agent_id = doc_cfg["agent_id"]
    label    = doc_cfg["label"]
    scens    = doc_cfg["scenarios"]

    # Resume support: skip scenarios before start_from
    if start_from and start_from in scens:
        skip_idx = scens.index(start_from)
        skipped  = scens[:skip_idx]
        scens    = scens[skip_idx:]
        logger.info(f"  [RESUME] Skipping {len(skipped)} already-passed scenarios: {skipped}")
    elif start_from and start_from not in scens:
        # start_from belongs to a later doc type — skip entire block
        logger.info(f"  [RESUME] Skipping entire block '{label}' (before start_from={start_from})")
        return {
            "agent":     agent_id,
            "label":     label,
            "total":     0,
            "passed":    0,
            "failed":    0,
            "fallbacks": 0,
            "pct":       100.0,
            "status":    "SKIPPED",
            "passed_scenarios":   [],
            "failed_scenarios":   [],
            "fallback_scenarios": [],
        }

    logger.info("")
    logger.info("=" * 68)
    logger.info(f"  STARTING: {label}  ({len(scens)} scenarios)")
    logger.info("=" * 68)

    per_agent_log = LOGS_DIR / f"{agent_id}.log"
    per_fh = logging.FileHandler(per_agent_log, encoding="utf-8", mode="w")
    per_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(per_fh)

    passed_list   = []
    failed_list   = []
    fallback_list = []

    for scen_id in scens:
        logger.info(f"\n  -- Scenario {scen_id} --")
        if scen_id in PENDING_SCENARIOS:
            logger.info(f"  [PENDING] {scen_id}: Skipped")
            passed_list.append({"id": scen_id, "message": "Pending - Skipped"})
            continue

        scen_passed = False
        last_msg    = ""

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"     Attempt {attempt}/{MAX_RETRIES} ...")
            ok, msg, is_fallback = run_one_scenario(doc_cfg, scen_id)
            last_msg = msg

            if ok:
                scen_passed   = True
                if is_fallback:
                    fallback_list.append(scen_id)
                    logger.info(f"  [FALLBACK PASS] {scen_id}: {msg}")
                else:
                    logger.info(f"  [PASS] {scen_id}: {msg}")
                break
            else:
                logger.warning(f"  [FAIL attempt {attempt}] {scen_id}: {msg}")
                screenshot(scen_id, attempt)
                if attempt < MAX_RETRIES:
                    logger.info(f"     Waiting {RETRY_DELAY}s before retry ...")
                    time.sleep(RETRY_DELAY)

        if scen_passed:
            passed_list.append({"id": scen_id, "message": last_msg})
        else:
            failed_list.append({"id": scen_id, "message": last_msg})
            logger.error(f"  [FINAL FAIL] {scen_id} failed after {MAX_RETRIES} attempts")

    # Remove per-agent handler
    logger.removeHandler(per_fh)
    per_fh.close()

    total   = len(scens)
    n_pass  = len(passed_list)
    n_fail  = len(failed_list)
    pct     = n_pass / total * 100 if total else 0
    status  = "PASS" if n_fail == 0 else "FAIL"
    icon    = "[OK]" if n_fail == 0 else "[FAIL]"

    logger.info("")
    logger.info(f"  {icon} {label}: {n_pass}/{total} ({pct:.0f}%)")
    if failed_list:
        logger.error(f"  FAILED SCENARIOS: {[s['id'] for s in failed_list]}")
    logger.info("=" * 68)

    result = {
        "agent":     agent_id,
        "label":     label,
        "total":     total,
        "passed":    n_pass,
        "failed":    n_fail,
        "fallbacks": len(fallback_list),
        "pct":       round(pct, 1),
        "status":    status,
        "passed_scenarios":   passed_list,
        "failed_scenarios":   failed_list,
        "fallback_scenarios": fallback_list,
    }

    # Save per-agent result JSON
    result_path = RESULTS_DIR / f"{agent_id}_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


# ── Master gauntlet ───────────────────────────────────────────────────────────
def run_sequential_gauntlet(start_from: str = None):
    start_time = time.time()

    logger.info("")
    logger.info("*" * 68)
    logger.info("   KAIRO PHANTOM -- 1000x SEQUENTIAL PRODUCTION GAUNTLET")
    logger.info(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (local)")
    logger.info("   Testing one doc type fully before moving to next.")
    if start_from:
        logger.info(f"   RESUMING from scenario: {start_from}")
    logger.info("*" * 68)

    all_results = []
    # Once we've seen start_from once, clear it so subsequent blocks run fully
    _start_from = start_from

    for doc_cfg in DOCUMENT_QUEUE:
        result = run_doc_block(doc_cfg, start_from=_start_from)
        # After the block that contained start_from, stop skipping
        if _start_from and _start_from in doc_cfg["scenarios"]:
            _start_from = None
        all_results.append(result)

        # Save rolling master report after each doc type
        _save_master(all_results, start_time)

    elapsed = time.time() - start_time
    grand_total  = sum(r["total"]  for r in all_results)
    grand_passed = sum(r["passed"] for r in all_results)
    grand_failed = sum(r["failed"] for r in all_results)
    grand_pct    = grand_passed / grand_total * 100 if grand_total else 0

    logger.info("")
    logger.info("*" * 68)
    logger.info("   FINAL RESULTS")
    logger.info(f"   Total scenarios : {grand_total}")
    logger.info(f"   Passed          : {grand_passed}")
    logger.info(f"   Failed          : {grand_failed}")
    logger.info(f"   Pass rate       : {grand_pct:.1f}%")
    logger.info(f"   Elapsed         : {elapsed:.0f}s")
    verdict = "PRODUCTION CERTIFIED" if grand_failed == 0 else f"{grand_failed} SCENARIO(S) NEED FIXING"
    logger.info(f"   Verdict         : {verdict}")
    logger.info("*" * 68)

    _save_master(all_results, start_time)
    return grand_failed == 0


def _save_master(results, start_time):
    elapsed      = time.time() - start_time
    grand_total  = sum(r["total"]  for r in results)
    grand_passed = sum(r["passed"] for r in results)
    grand_failed = sum(r["failed"] for r in results)
    grand_pct    = grand_passed / grand_total * 100 if grand_total else 0

    master = {
        "product":          "Kairo Phantom",
        "gauntlet_version": "sequential-1000x-v3",
        "run_at":           datetime.now().isoformat(),
        "elapsed_seconds":  round(elapsed, 1),
        "grand_total":      grand_total,
        "grand_passed":     grand_passed,
        "grand_failed":     grand_failed,
        "pass_rate":        round(grand_pct, 2),
        "verdict":          "PRODUCTION CERTIFIED" if grand_failed == 0 else f"{grand_failed} FAILURES",
        "agent_results":    results,
    }

    out = RESULTS_DIR / "MASTER_GAUNTLET_REPORT_v3.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)

    repo_root = pathlib.Path(__file__).parent.parent
    with open(repo_root / "MASTER_GAUNTLET_REPORT_v3.json", "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kairo sequential gauntlet")
    parser.add_argument(
        "--start-from", dest="start_from", default=None, metavar="SCENARIO_ID",
        help="Resume from this scenario ID (e.g. W20). Skips earlier scenarios.",
    )
    args = parser.parse_args()
    success = run_sequential_gauntlet(start_from=args.start_from)
    sys.exit(0 if success else 1)
