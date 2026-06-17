# /legacy — Disabled Integrity Problems

> This directory contains files with integrity problems that were moved here
> per SPEC §S0. These are NOT domain capabilities — they are faked gauntlet
> scripts, mocked production bridges, stub-mode AI, and unverified bulk code.

## What Belongs Here

- Faked gauntlet scripts that always passed
- Mocked production bridges that never connected to real services
- Stub-mode AI that returned canned responses
- Unverified bulk code with no test coverage

## What Does NOT Belong Here

- **Domain code** — the 12 domains are PRESERVED in `/domains`
- **Working kernel/sidecar code** — stays in `/kernel`
- **Pack implementations** — stays in `/packs`

## Policy

Files here are DISABLED and never imported by the kernel or any Pack.
CI guards enforce this: `kernel_purity_guard.py` blocks any import from `/legacy`.

*Kairo Phantom · /legacy · integrity problems only · never domains.*
