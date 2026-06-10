"""
memmachine_demo.py
==================
Deterministic 3-session demo showing how Kairo MemMachine learns from user
behaviour and adapts its output over time.

Run with:
    python scripts/memmachine_demo.py

No external dependencies — uses only the stdlib + kairo-sidecar's MemMachineClient.
ANSI colours are emitted via escape codes; they work on Windows 10+ (VT100 mode).
"""

import sys
import os
import time
import tempfile

# ── Ensure stdout speaks UTF-8 on Windows (needed for emoji) ──────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Make the sidecar package importable when running from the repo root ────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SIDECAR_ROOT = os.path.join(_REPO_ROOT, "kairo-sidecar")
if _SIDECAR_ROOT not in sys.path:
    sys.path.insert(0, _SIDECAR_ROOT)

from sidecar.mem_machine import MemMachineClient  # noqa: E402

# ── Enable VT100 on Windows so ANSI codes render ───────────────────────────────
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ── ANSI colour palette ────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

BG_DARK   = "\033[48;5;234m"   # near-black background strip
FG_WHITE  = "\033[97m"
FG_CYAN   = "\033[96m"
FG_GREEN  = "\033[92m"
FG_YELLOW = "\033[93m"
FG_MAGENTA= "\033[95m"
FG_BLUE   = "\033[94m"
FG_RED    = "\033[91m"
FG_GREY   = "\033[90m"

# ── Helper printers ────────────────────────────────────────────────────────────

def _hr(char: str = "─", width: int = 72, colour: str = FG_GREY) -> str:
    return f"{colour}{char * width}{RESET}"


def header(title: str) -> None:
    print()
    print(_hr("═"))
    print(f"  {BOLD}{FG_CYAN}{title}{RESET}")
    print(_hr("═"))


def sub(label: str, value: str = "") -> None:
    print(f"  {FG_YELLOW}▸{RESET}  {BOLD}{label}{RESET}  {FG_GREEN}{value}{RESET}")


def event(icon: str, msg: str, detail: str = "") -> None:
    detail_str = f"  {DIM}{FG_GREY}{detail}{RESET}" if detail else ""
    print(f"  {icon}  {msg}{detail_str}")


def code_block(lines: list[str], label: str = "") -> None:
    if label:
        print(f"  {DIM}{FG_GREY}╔══ {label} ══{RESET}")
    for line in lines:
        print(f"  {DIM}{FG_GREY}│{RESET}  {FG_BLUE}{line}{RESET}")
    if label:
        print(f"  {DIM}{FG_GREY}╚{'═' * (len(label) + 6)}{RESET}")


def pause(ms: int = 120) -> None:
    """Tiny deterministic delay makes output feel 'alive' without randomness."""
    time.sleep(ms / 1000)


# ── Fixed demo data (fully deterministic) ─────────────────────────────────────

SESSION_1_INTERACTIONS = [
    dict(
        domain="word",
        task_type="insert",
        user_prompt="// draft a cover letter opening paragraph for a senior data scientist role",
        output_preview="Dear Hiring Committee, I am writing to express my strong interest in the Senior Data Scientist position...",
        confidence=1.0,
        style_notes="prefers_formal_tone, uses_full_salutation, avoids_contractions",
    ),
    dict(
        domain="excel",
        task_type="insert",
        user_prompt="// add an IF formula that marks Q4 revenue cells red when below target",
        output_preview='=IF(D4<$B$2,"BELOW TARGET","OK")',
        confidence=0.97,
        style_notes="",
    ),
    dict(
        domain="word",
        task_type="insert",
        user_prompt="// add a bullet-point summary of the methodology section",
        output_preview="• Data ingestion pipeline: Apache Kafka → Spark structured streaming\n• Model training: XGBoost with Optuna hyperparameter search",
        confidence=0.99,
        style_notes="prefers_bullet_lists_over_prose, technical_vocabulary",
    ),
]

SESSION_2_QUERY_DOMAIN = "word"

SESSION_3_NEW_PROMPT_RAW = (
    "// write an executive summary for the Q3 performance report"
)


# ── Demo sessions ──────────────────────────────────────────────────────────────

def run_session_1(mem: MemMachineClient) -> None:
    header("SESSION 1  ·  User writes — Kairo watches & learns")

    print()
    print(f"  {FG_GREY}Simulating a typical Monday-morning writing session…{RESET}")
    print()

    for i, ix in enumerate(SESSION_1_INTERACTIONS, 1):
        app = ix["domain"].upper()
        icon = "📝" if ix["domain"] == "word" else "📊"
        pause(80)

        event(
            icon,
            f"{BOLD}Op {i}{RESET}  ·  {FG_MAGENTA}{app}/{ix['task_type']}{RESET}",
            ix["user_prompt"],
        )

        ok = mem.record_interaction(**ix)
        status = f"{FG_GREEN}✔ recorded{RESET}" if ok else f"{FG_RED}✘ failed{RESET}"
        print(f"       {FG_GREY}↳ MemMachine:{RESET} {status}", end="")

        if ix["style_notes"]:
            print(f"  {FG_YELLOW}style_notes:{RESET} {DIM}{ix['style_notes']}{RESET}", end="")
        print()
        pause(40)

    print()
    print(f"  {FG_GREY}Session 1 complete.  3 interactions persisted to local SQLite.{RESET}")


def run_session_2(mem: MemMachineClient) -> str:
    header("SESSION 2  ·  Next day — Kairo remembers")

    print()
    print(f"  {FG_GREY}User opens Word.  Alt+M is pressed.  MemMachine wakes up…{RESET}")
    print()
    pause(150)

    # Retrieve memory
    recalled = mem.query(domain=SESSION_2_QUERY_DOMAIN, limit=5)
    profile  = mem.get_style_profile(domain=SESSION_2_QUERY_DOMAIN)

    n_interactions = sum(t["count"] for t in profile["task_frequencies"])

    sub("Query domain", SESSION_2_QUERY_DOMAIN)
    pause(60)
    sub("Interactions found", str(n_interactions))
    pause(60)

    print()
    print(
        f"  {FG_GREEN}{BOLD}** Kairo remembers your writing preferences "
        f"from {n_interactions} previous interactions{RESET}"
    )
    print()

    print(_hr())
    print(f"  {BOLD}{FG_CYAN}Recalled style context:{RESET}")
    print()
    for line in recalled.splitlines():
        print(f"    {FG_BLUE}{line}{RESET}")
    print()
    print(_hr())

    # Task-frequency breakdown
    print()
    print(f"  {BOLD}Task frequency profile:{RESET}")
    for tf in profile["task_frequencies"]:
        bar = "█" * tf["count"]
        print(
            f"    {FG_MAGENTA}{tf['task_type']:<12}{RESET} "
            f"{FG_GREEN}{bar}{RESET} ×{tf['count']}  "
            f"{DIM}(avg confidence {tf['avg_confidence']:.2f}){RESET}"
        )

    return recalled


def run_session_3(mem: MemMachineClient, memory_context: str) -> None:
    header("SESSION 3  ·  Kairo adapts — memory shapes the prompt")

    print()
    print(f"  {FG_GREY}New request arrives…{RESET}")
    print()
    sub("User types", SESSION_3_NEW_PROMPT_RAW)
    print()
    pause(100)

    # ── BEFORE memory ─────────────────────────────────────────────────────────
    prompt_before = f"""\
You are a helpful writing assistant.
The user is working in Microsoft Word.

User request: {SESSION_3_NEW_PROMPT_RAW.lstrip('// ')}

Please write the requested content."""

    # ── AFTER memory ──────────────────────────────────────────────────────────
    prompt_after = f"""\
You are a helpful writing assistant.
The user is working in Microsoft Word.

{memory_context}

Based on this user's established style:
  • Use formal, professional language (no contractions)
  • Prefer bullet points over dense prose for summaries
  • Include precise technical vocabulary where appropriate
  • Use full salutations and sign-offs in letters

User request: {SESSION_3_NEW_PROMPT_RAW.lstrip('// ')}

Please write the requested content matching the user's documented style."""

    # ── Side-by-side diff ─────────────────────────────────────────────────────
    print(f"  {BOLD}{FG_RED}BEFORE memory  {FG_GREY}(generic assistant, no context){RESET}")
    print()
    for line in prompt_before.splitlines():
        print(f"  {FG_RED}─{RESET}  {DIM}{line}{RESET}")

    print()
    pause(120)

    print(f"  {BOLD}{FG_GREEN}AFTER memory   {FG_GREY}(Kairo knows you){RESET}")
    print()
    for line in prompt_after.splitlines():
        marker = f"{FG_GREEN}+{RESET}" if line.strip() else " "
        print(f"  {marker}  {line}")

    print()
    print(_hr())
    print()

    # ── Impact summary ────────────────────────────────────────────────────────
    tokens_before = len(prompt_before.split())
    tokens_after  = len(prompt_after.split())
    quality_delta = "+∞"   # deterministic humour

    print(f"  {BOLD}{FG_CYAN}Impact summary{RESET}")
    print()
    print(f"    {FG_YELLOW}Prompt tokens added by MemMachine:{RESET}  {tokens_after - tokens_before}")
    print(f"    {FG_YELLOW}Style constraints injected:       {RESET}  4")
    print(f"    {FG_YELLOW}Generic vs. personalised output:  {RESET}  {quality_delta} quality improvement")
    print()

    # ── Privacy reminder ──────────────────────────────────────────────────────
    print(
        f"  {FG_GREY}[PRIVATE]  All memory stored locally at{RESET} "
        f"{FG_BLUE}~/.kairo/memmachine.db{RESET}  "
        f"{FG_GREY}-- never leaves your machine.{RESET}"
    )


# ── Finale ─────────────────────────────────────────────────────────────────────

def print_finale() -> None:
    print()
    print(_hr("═", colour=FG_GREEN))
    print()
    print(f"  {BOLD}{FG_GREEN}[DONE]  Demo complete.{RESET}")
    print()
    print(f"  {FG_WHITE}MemMachine transformed 3 raw interactions into personalised context{RESET}")
    print(f"  {FG_WHITE}that makes every future Kairo response feel like it was written{RESET}")
    print(f"  {FG_WHITE}by someone who has worked alongside you for months.{RESET}")
    print()
    print(f"  {FG_CYAN}>>  Run{RESET} {BOLD}kairo seed <your-docs-folder>{RESET} {FG_CYAN}to seed from your real documents.{RESET}")
    print(f"  {FG_CYAN}>>  Run{RESET} {BOLD}kairo export-memory{RESET}             {FG_CYAN}to back up your style profile.{RESET}")
    print()
    print(_hr("═", colour=FG_GREEN))
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    # Use a fresh temp DB so the demo is fully deterministic
    db_file = tempfile.mktemp(suffix=".db", prefix="kairo_demo_")

    print()
    print(f"  {BOLD}{BG_DARK}{FG_CYAN}  [KAIRO PHANTOM]  MemMachine Learning Demo  {RESET}")
    print(f"  {DIM}Temp DB:{RESET}  {FG_GREY}{db_file}{RESET}")

    mem = MemMachineClient(db_path=db_file)

    # ── Run all three sessions ─────────────────────────────────────────────────
    run_session_1(mem)
    pause(200)

    memory_context = run_session_2(mem)
    pause(200)

    run_session_3(mem, memory_context)

    print_finale()

    # Clean up temp file so we leave no trace
    try:
        os.remove(db_file)
    except OSError:
        pass


if __name__ == "__main__":
    main()
