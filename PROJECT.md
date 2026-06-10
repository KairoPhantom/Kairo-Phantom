# Project: Kairo Phantom v3.9.0 1000x Upgrade Master Roadmap and Launch Checklist

## Architecture
- python-docx write-back with XML-level insertion in `sidecar/masters/word_master.py`.
- QLoRA 4B model schema compliance and model swap in `scripts/eval_schema_compliance.py` and `litellm_config.yaml`.
- LiteLLM 3-Tier/4-Tier smart routing configurations in `litellm_config.yaml`.
- Create-from-scratch creators: `sidecar/creators/docx_creator.py`, `pptx_creator.py`, and `xlsx_creator.py`.
- Launch checklist and PR Gate compliance verified via `kairo-sidecar/pr_gate_runner.py` and test suites.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Baseline Verification & Exploration | Investigate existing codebase, run tests, and check status of all gates | None | DONE (297534ec-9c74-424f-9fb1-0c7cdfaf6ce6) |
| 2 | python-docx Write-Back Integration | Refine XML-level paragraph insertion and atomic write in `word_master.py` | M1 | DONE (df9a49da-9b47-4f05-91ea-d56544053b0f) |
| 3 | LiteLLM Smart Routing & Config | Configure 4 tiers and fallback chains in `litellm_config.yaml` | M1 | DONE (2a3079fd-6b61-49b4-ada5-49ab62eee2f7) |
| 4 | Unsloth Fine-Tuning & Model Swap | Verify 4B schema compliance and execute model swap if compliance >= 95% | M1 | DONE (2a3079fd-6b61-49b4-ada5-49ab62eee2f7) |
| 5 | Document Creators | Implement/refine creators for docx, pptx, xlsx using standard libraries and `os.startfile()` | M1 | DONE (2a3079fd-6b61-49b4-ada5-49ab62eee2f7) |
| 6 | Production Gates Verification | Run gate runner, debug and fix failing gates to pass at least 13/14 gates | M2, M3, M4, M5 | DONE (9a9fa7d0-c16b-4f2e-9ba4-490ff3cd65d0) |

## Interface Contracts
### word_master ↔ Document Writer
- `WordWriter.apply_operations()` must use XML-level `ref_para._element.addnext(new_para._element)`.
- Use tmp+rename pattern with backup copy before saving.
### LiteLLM ↔ Router
- `litellm_config.yaml` must define 4 tiers: `kairo-fast` (4B), `kairo-standard` (Qwen 7B), `kairo-think` (Qwen 8B reasoning), `kairo-cloud` (Claude Sonnet).
- Smart routing based on token counts, confidence, task type.
