# Kairo Phantom — Systematic In-Depth Premortem Analysis & Moat Validation

This document presents a comprehensive, production-grade premortem audit of the newly integrated VLM/CUA capabilities and the Writing Intelligence v2.0 roadmap for Kairo Phantom. It outlines potential failure modes, calculates risks, and registers the verified mitigation paths implemented across the codebase.

---

## 1. VLM / CUA Integration Failure Modes

### 1.1 VRAM Congestion & GPU Out-of-Memory (OOM)
* **Pre-mitigation Failure Scenario:** Consumer laptops with 4 GB to 8 GB VRAM launch the default Qwen2.5-VL-7B model (4.2 GB quantized GGUF). The system immediately experiences massive swapping, screen stuttering, or an out-of-memory driver crash, killing both Kairo and host application processes.
* **Likelihood:** High (for consumer devices).
* **Impact:** Critical (system instability).
* **Implementation Mitigation:**
  * **Dynamic Hardware Tiering:** Handled in [vlm_config.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_config.py#L163-L189). It queries VRAM via NVIDIA/AMD SMIs. If VRAM is $\ge 6\text{ GB}$, it runs the 7B tier. If VRAM is between $3$ and $5\text{ GB}$, it falls back to the 3B model (2.0 GB GGUF). If VRAM is $< 3\text{ GB}$ or no discrete GPU is available, it gracefully shifts to CPU-only execution and logs latency metrics.
  * **Immediate VRAM Unloading:** Handled in [vlm_grounding.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_grounding.py#L193). Every Ollama generate payload sets `keep_alive=0` so that Ollama releases the model from VRAM instantly after completing the single grounding or verification task.

### 1.2 GGUF Download Interruption, Corruption & Network drops
* **Pre-mitigation Failure Scenario:** A network drop or disk full condition mid-way through downloading the 4.2 GB model leaves a truncated or corrupt file at `~/.kairo-phantom/models/qwen2.5-vl-7b-instruct-Q4_K_M.gguf`. Ollama attempts to register the corrupt file, failing silently or crashing.
* **Likelihood:** Medium.
* **Impact:** High (model loading fails).
* **Implementation Mitigation:**
  * **Atomic Renaming & Tmp Files:** Handled in [vlm_download_manager.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_download_manager.py#L195-L258). The download stream writes to a `.tmp` file. The final rename to `.gguf` is executed only after the full byte length is successfully written.
  * **HTTP Range Resume Support:** Handled in [vlm_download_manager.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_download_manager.py#L202-L205). The manager checks for existing `.tmp` files, reads the local size, and starts range requests (`Range: bytes=X-`) to resume downloads on restart.

### 1.3 Thread Exhaustion in Named Pipe Notifier
* **Pre-mitigation Failure Scenario:** When a large download is active, progress notifications fire frequently. If the host pipe is blocked or slow, spawning a separate OS thread (`threading.Thread`) for every individual update will quickly cause thread starvation, slowing down the sidecar and exhausting system resources.
* **Likelihood:** Low-Medium (high frequency progress updates).
* **Impact:** Medium.
* **Implementation Mitigation:**
  * **Queue-based Single Worker Thread:** Handled in [vlm_download_manager.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_download_manager.py#L76-L120). Progress notification payloads are queued in a thread-safe `queue.Queue(maxsize=10)`. A single background daemon thread processes the queue. Stale/old progress frames are discarded if the queue fills up, guaranteeing $O(1)$ thread overhead.

### 1.4 Non-Windows Platform & Ctypes Crashes
* **Pre-mitigation Failure Scenario:** The CUA visual fallback requires clicking elements using coordinates. If Python's `ctypes.windll` is called on Linux or macOS systems, it will crash with an `AttributeError` instead of falling back to other interface APIs.
* **Likelihood:** Medium (for cross-platform sidecar runs).
* **Impact:** High (causes execution crash).
* **Implementation Mitigation:**
  * **System Check and Attribute Guard:** Handled in [cross_app_orchestrator.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/cross_app_orchestrator.py#L690-L711). The click routine explicitly verifies `sys.platform == "win32"` and wraps the `ctypes.windll` call in an `AttributeError` try-except block, logging clean warnings instead of crashing.

---

## 2. Cross-App Orchestration Failure Modes

### 2.1 Focus and Focus-Stealing Race Conditions
* **Pre-mitigation Failure Scenario:** During a multi-step Excel $\to$ PowerPoint workflow, the orchestrator requests window focus, but Windows takes a few hundred milliseconds to fully render the window, or another popup steals focus. Mouse clicks hit the wrong active elements.
* **Likelihood:** High.
* **Impact:** Critical (clicks hit background apps).
* **Implementation Mitigation:**
  * **Window Enumeration & ShowWindow Call:** Handled in [cross_app_orchestrator.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/cross_app_orchestrator.py#L476-L510). The focusing logic uses `EnumWindows` and explicitly calls `ShowWindow(hwnd, SW_RESTORE)` followed by `SetForegroundWindow` with a mandatory asynchronous delay (`await asyncio.sleep(0.5)`) to ensure rendering is complete before actions trigger.
  * **Semantic Pre-Action Grounding:** Handled in [cross_app_orchestrator.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/cross_app_orchestrator.py#L522-L560). Instead of clicking blind coordinates, a screenshot is taken *immediately* before clicking, and the VLM grounds coordinates in real-time, verifying that the target element is visible in the active viewport.

### 2.2 Brittle Pixel Verification Failure (RPA Mismatch)
* **Pre-mitigation Failure Scenario:** A button layout moves slightly due to window resizing or theme changes, causing simple pixel-diff/hash verification to fail, even though the save dialog was successfully clicked.
* **Likelihood:** High.
* **Impact:** High (spurious failures).
* **Implementation Mitigation:**
  * **Intent-Based VLM Semantic Verification:** Handled in [vlm_grounding.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/cua/vlm_grounding.py#L282-L350). Post-action check uses the VLM to compare "Before" and "After" screenshots against the `expected_result` (e.g., "does the dialog actually say 'Saved'?"), completely bypassing layout dependencies.

---

## 3. Writing Intelligence v2.0 Failure Modes

### 3.1 Copyright Check Performance Overhead
* **Pre-mitigation Failure Scenario:** Scanning long documents for plagiarism or training set leakage by matching every possible n-gram against a large database adds substantial latency (hundreds of milliseconds or seconds) to inline writing generation.
* **Likelihood:** High (for large corpus files).
* **Impact:** Medium (poor user experience).
* **Implementation Mitigation:**
  * **Bloom Filter Fast-Path Pre-filtering:** Handled in [memorization_auditor.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/writers/memorization_auditor.py#L59-L82). The auditor implements a space-efficient `BloomFilter` calibrated with $m=100,000$ bits and $k=4$ hashes.
  * **Dual-Verification Match:** Handled in [memorization_auditor.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/kairo-sidecar/sidecar/writers/memorization_auditor.py#L476-L488). If `h in self._bloom` evaluates to true, the auditor queries the exact `self._corpus` mapping to confirm the hit. If `h not in self._bloom`, it is instantly marked safe, bypassing dictionary lookups completely.

### 3.2 LoRA Adapter stylistic drift & base performance collapse
* **Pre-mitigation Failure Scenario:** Repeated overnight training runs on user session corrections lead to catastrophic forgetting, causing the model to lose base grammar capabilities or drift into repetitive style outputs.
* **Likelihood:** Medium.
* **Impact:** High (quality degradation).
* **Implementation Mitigation:**
  * **Limits and Held-Out Validation:** Handled in [personal_finetune.py](file:///c:/Users/praja/OneDrive/Desktop/test-env/repositories/kairo-phantom/scripts/training/personal_finetune.py#L130-L165). SFT training configurations restrict updates to `r=16`, `lora_alpha=32`, and place strict ceiling bounds of 1,000 maximum samples and 5.0 training epochs, avoiding overfitting. Base capability evaluation is performed against the `kmb1_benchmark` to reject degraded training cycles.
