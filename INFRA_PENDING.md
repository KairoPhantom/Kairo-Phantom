# Kairo Phantom 100X Plan — Part 1: INFRA_PENDING.md

> **Items blocked by infrastructure limitations in the current sandbox.**
> Each item has the exact command to verify on proper hardware.
> Updated: 2026-06-24

---

## BLOCKED ITEMS

### 1. Opik self-hosted dashboard (Phase 0.1, Step 1)
- **Blocker**: Docker is not available in this sandbox
- **Impact**: Cannot run `docker compose up` for Opik self-hosted (localhost:5173)
- **Workaround**: Implement provenance receipt + observability emit layer writing to local file/queue sink (built on identity.rs). The receipt emission is real and tested. Only the dashboard UI is deferred.
- **Verification command (on real hardware)**:
  ```bash
  git clone https://github.com/comet-ml/opik.git /data/opik
  cd /data/opik && docker compose up -d
  curl http://localhost:5173  # Should return 200
  ```

### 2. Linux ghost-typing verification on a real display (Phase 0 — pre-existing)
- **Blocker**: No X11/Wayland display server in this sandbox
- **Impact**: `inject_replace_line()` and `erase_prompt()` in `LinuxPlatformInjector` are implemented via xdotool but cannot be runtime-verified without a display
- **Workaround**: Implementation is complete and compiles. At runtime, if xdotool is missing or no display is available, the methods log a loud error (never return silently).
- **Verification command (on real hardware)**:
  ```bash
  # Requires: xdotool installed, DISPLAY set, X11 or Wayland session active
  cargo test --bin kairo-phantom -- test_injector
  # Or manually: run kairo-phantom, trigger Alt+Ctrl+M in a text editor
  ```

### 3. Rust binary compilation memory limit (workspace --no-run)
- **Blocker**: Sandbox has 3.8GB RAM, 2 cores, no swap. Full workspace `cargo test --workspace --no-run` can OOM-kill the linker when compiling the kairo-phantom binary.
- **Impact**: Must compile binary tests separately (`cargo test --bin kairo-phantom --no-run`) which works but takes ~55s.
- **Workaround**: Use `CARGO_INCREMENTAL=0` and compile targets individually. All tests pass when compiled this way.
- **Verification command (on real hardware)**:
  ```bash
  cargo test --workspace  # Should complete without OOM on a machine with ≥8GB RAM
  ```
- **NOTE**: Full Rust suite (478 tests) IS reproducible in this sandbox by compiling targets individually. The OOM only affects the single `--workspace --no-run` command that tries to compile everything at once.

---

### 5. Live paperless-ngx + Karakeep integration (Phase 0.7)
- **Blocker**: Docker is not available in this sandbox — cannot run paperless-ngx or Karakeep instances
- **Impact**: Bridge logic is tested against mock HTTP servers (clearly labeled as non-production).
  Live integration against real services is not verified here.
- **Workaround**: Bridge code is REAL (real urllib HTTP client, real auth, real JSON parsing).
  Mock servers simulate the API responses. The bridges FAIL LOUDLY (raise ConnectionError)
  when the real service is unreachable — they never silently no-op or fake success.
- **Verification command (on real hardware with Docker)**:
  ```bash
  # Start paperless-ngx
  docker compose up -d  # with paperless-ngx docker-compose.yml
  export KAIRO_CONNECTORS=paperless
  export PAPERLESS_URL=http://localhost:8000
  export PAPERLESS_TOKEN=<real_token>
  python3 -m pytest test_phase0_7_bridges.py -v  # All tests should pass against real service

  # Start Karakeep
  docker run -p 3000:3000 karakeep/karakeep
  export KAIRO_CONNECTORS=karakeep
  export KARAKEEP_URL=http://localhost:3000
  export KARAKEEP_TOKEN=<real_token>
  python3 -m pytest test_phase0_7_bridges.py -v
  ```
- **Blocker**: fastembed AllMiniLML6-v2 (80MB ONNX) requires network to download on first use
- **Impact**: Without this model, the system uses hash-based embeddings which are NON-SEMANTIC.
  - Hash embeddings produce deterministic vectors but do NOT capture semantic meaning.
  - "cancel subscription" and "end membership" will NOT be similar under hash embeddings.
  - Real semantic search (paraphrase retrieval, meaning-based KNN) is IMPOSSIBLE without the model.
- **Air-gap status**: NOT yet real. Air-gap currently falls back to hash embeddings (non-semantic).
  - Real air-gap requires pre-caching the fastembed model (one-time fetch, then fully offline).
  - The model is cached in ~/.cache/ after first download — subsequent runs work offline.
  - To enable real air-gap: download model once on a networked machine, copy ~/.cache/ to air-gapped machine.
- **Workaround**: Default (CI/headless) path uses hash embeddings — sufficient for testing
  vector store mechanics (insert, KNN, dimension checks) but NOT for semantic retrieval.
- **Verification command (on real hardware with network)**:
  ```bash
  # Build with local-embeddings feature (triggers model download on first test run)
  cargo test --lib -p phantom-core embedding --features local-embeddings

  # The semantic relevance test will run and verify:
  # query "cancel subscription" retrieves "membership termination" (not "newsletter subscribe")
  # This test is SKIPPED without --features local-embeddings

  # For air-gap: after first download, copy the cached model:
  cp -r ~/.cache/fastembed/ /air-gapped-machine/.cache/fastembed/
  cargo test --lib -p phantom-core embedding --features local-embeddings  # works offline
  ```
- **Model details**: all-MiniLM-L6-v2, 384-dim (truncated to 256), 80MB ONNX, CPU-only, MIT license