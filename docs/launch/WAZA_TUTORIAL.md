# Build Your First Kairo Waza Agent in 10 Minutes

*Phase 3, Item 5 — Waza Agent Builder Tutorial*

---

## What Is a Waza Agent?

A **Waza agent** is a skill plugin for Kairo Phantom. When you install one,
Kairo gains a new expert mode for specific domains — legal, medical, academic,
sales, or anything you define.

Waza agents are plain TOML + Markdown files. No code required.

---

## Prerequisites

```bash
# Kairo Phantom must be installed and running
cargo install kairo-phantom
kairo status     # should show: ✓ Kairo Phantom running
```

---

## Step 1 — Scaffold a New Agent

```bash
kairo skill new my-agent
```

This creates a directory `~/.kairo-phantom/skills/my-agent/` with two files:

```
my-agent/
├── manifest.toml   ← metadata and routing rules
└── SKILL.md        ← the system prompt for this agent
```

---

## Step 2 — Edit the Manifest

Open `~/.kairo-phantom/skills/my-agent/manifest.toml`:

```toml
[agent]
name        = "My Agent"
version     = "0.1.0"
description = "Does X for Y use case"
author      = "Your Name"

[routing]
# Keywords that trigger this agent when detected in the prompt
keywords    = ["my-keyword", "another-keyword"]
# Document types this agent handles
doc_types   = ["WordDocument", "PowerPoint"]   # or ["ExcelSpreadsheet"]
# Priority (higher = preferred when multiple agents match)
priority    = 50

[limits]
max_tokens  = 1000
temperature = 0.3      # lower = more deterministic (good for legal/medical)
```

---

## Step 3 — Write the System Prompt

Open `~/.kairo-phantom/skills/my-agent/SKILL.md`:

```markdown
# My Agent

You are a specialized assistant for [YOUR DOMAIN].

## Behavior Rules
- Always respond in [STYLE]
- Never include [FORBIDDEN CONTENT]
- Keep responses under [WORD COUNT] words

## Output Format
[Describe exactly what the output should look like]

## Examples

**Prompt:** // [example command]
**Output:** [example response]
```

The contents of `SKILL.md` become the LLM system prompt when this agent is active.

---

## Step 4 — Install and Test

```bash
# Install from local directory
kairo skill add ./my-agent/

# Or if you built it in place:
kairo skill list    # should show "my-agent" in the list

# Test it
kairo skill test my-agent "// rewrite this in my-agent style"
```

---

## Step 5 — Verify in Word

1. Open Word
2. Type `// [one of your routing keywords]`
3. Press `Alt+Ctrl+M`
4. Kairo should route to your agent (the swarm log shows which agent handled it)

---

## The 5 Built-In Seed Agents

Kairo ships with 5 production-quality agents you can study as templates:

| Agent | File | Keywords |
|---|---|---|
| Legal Review | `skills/legal-review/` | contract, NDA, clause, indemnify |
| Academic Editor | `skills/academic-editor/` | abstract, citation, methodology, thesis |
| Marketing Copywriter | `skills/marketing-copywriter/` | campaign, CTA, landing page, product |
| Code Reviewer | `skills/code-reviewer/` | refactor, function, bug, PR review |
| Medical Scribe | `skills/medical-scribe/` | patient, diagnosis, SOAP, clinical |

```bash
# View any seed agent
cat ~/.kairo-phantom/skills/legal-review/SKILL.md
cat ~/.kairo-phantom/skills/legal-review/manifest.toml
```

---

## Sharing Your Agent

Once your agent works well:

1. Create a GitHub repo: `kairo-waza-MY-AGENT`
2. Add the `manifest.toml` and `SKILL.md`
3. Submit a PR to [Kairo Phantom](https://github.com/KairoPhantom/Kairo-Phantom)
   listing your agent in the Community Waza Registry

Other users can then install it with:
```bash
kairo skill install github:yourname/kairo-waza-my-agent
```

---

## Advanced: Routing by Document Type

You can make an agent that only activates for Excel:

```toml
[routing]
doc_types = ["ExcelSpreadsheet"]
keywords  = ["formula", "calculate", "pivot"]
```

Or one that activates for all doc types but requires a specific prefix:

```toml
[routing]
doc_types = ["WordDocument", "PowerPoint", "ExcelSpreadsheet"]
command_prefix = "// legal:"    # only activates for "// legal: ..." commands
```

---

## CLI Reference

```bash
kairo skill new <name>           # scaffold new agent
kairo skill list                 # list installed agents
kairo skill add <path>           # install agent from local directory
kairo skill install <url>        # install agent from GitHub
kairo skill rm <name>            # remove an agent
kairo skill test <name> "<cmd>"  # test agent with a prompt
kairo skill info <name>          # show agent metadata
```

---

## Troubleshooting

**"Agent not appearing in `kairo skill list`"**
- Check `manifest.toml` for TOML syntax errors: `kairo skill validate my-agent`

**"Agent not triggering in Word"**
- Check routing keywords match what you're typing
- Try lowering the `priority` if another agent is stealing the route

**"Response doesn't match my SKILL.md instructions"**
- Check the model supports your instruction style (smaller models follow instructions less reliably)
- Try `temperature = 0.1` for more faithful instruction following

---

*Built a great agent? Submit it to the [Community Registry](https://github.com/KairoPhantom/Kairo-Phantom/discussions) — we feature the best ones in the README.*
