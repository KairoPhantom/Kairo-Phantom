# Kairo Phantom — Installer Guide

> One-click install for macOS (.dmg/.pkg) and Windows (.msi). The installer bundles the Rust core + Python sidecar so there is **no separate sidecar install step**.

## Design Principle

Kairo Phantom ships as a single self-contained package. The Rust core binary, the Python sidecar (OCR/layout/extraction/embeddings), the Tauri overlay, and the default config are all bundled into one installer artifact. A user should never need to run `pip install`, `cargo build`, or manually start the sidecar.

## macOS Installer (.dmg / .pkg)

### Artifact
- **Format:** `.dmg` (drag-to-Applications) wrapping a signed `.pkg` installer
- **Signing:** Developer ID Application certificate + notarization via `xcrun notarytool`
- **Minimum OS:** macOS 12.0 (Monterey) — required for stable Accessibility APIs

### What the .pkg installs
| Component | Destination | Notes |
|:---|:---|:---|
| Rust core binary (`kairo-phantom`) | `/Applications/KairoPhantom.app/Contents/MacOS/` | Main executable |
| Python sidecar | `/Applications/KairoPhantom.app/Contents/Resources/kairo-sidecar/` | Bundled venv with all deps |
| Tauri overlay | `/Applications/KairoPhantom.app/Contents/MacOS/` | Thin render-only GUI |
| Config template | `~/Library/Application Support/Kairo/config.toml` | Only if not already present |
| Provenance store | `~/Library/Application Support/Kairo/provenance/` | Append-only, created on first run |
| LanceDB + models | `~/Library/Application Support/Kairo/models/` | Downloaded on first run (air-gap mode skips) |

### Install flow
1. User opens `KairoPhantom-x.x.x.dmg`
2. Drags `KairoPhantom.app` to `/Applications`
3. On first launch, macOS prompts for Accessibility permission (required for document reading)
4. First-run onboarding wizard launches (see `docs/ONBOARDING_WIZARD.md`)
5. Sidecar auto-starts on `127.0.0.1:7438` — no manual action needed

### Uninstall
- Delete `/Applications/KairoPhantom.app`
- Optionally remove `~/Library/Application Support/Kairo/`

## Windows Installer (.msi via Inno Setup)

### Artifact
- **Format:** `.msi` (via Inno Setup `KairoSetup.iss`)
- **Signing:** Authenticode code-signing certificate
- **Minimum OS:** Windows 10 1809 (build 17763)

### What the installer installs
| Component | Destination | Notes |
|:---|:---|:---|
| Rust core binary (`kairo-phantom.exe`) | `C:\Program Files\Kairo\` | Main executable |
| Python sidecar | `C:\Program Files\Kairo\kairo-sidecar\` | Bundled venv with all deps |
| Tauri overlay | `C:\Program Files\Kairo\` | Thin render-only GUI |
| Config template | `%APPDATA%\Kairo\config.toml` | Only if not already present |
| Provenance store | `%LOCALAPPDATA%\.kairo-phantom\` | Append-only, created on first run |
| Start menu + desktop shortcuts | Standard locations | Optional auto-start task |

### Install flow
1. User runs `KairoSetup.exe`
2. Inno Setup wizard: license → destination → install
3. Installer creates venv and installs sidecar dependencies automatically
4. First-run onboarding wizard launches with `--first-run` flag
5. Sidecar auto-starts on `127.0.0.1:7438` — no manual action needed

### Uninstall
- Use "Add or Remove Programs" → Kairo Phantom
- Or run `C:\Program Files\Kairo\unins000.exe`

## Bundled Sidecar — No Separate Install

The Python sidecar is **bundled inside the installer**, not installed separately. This is a critical design decision:

- **No `pip install` step for the user.** The installer creates the venv and installs dependencies during the install process.
- **No PATH pollution.** The sidecar runs from the application bundle directory.
- **Version lock.** The sidecar version matches the core binary version — they ship together.
- **Air-gap compatible.** All dependencies are pre-bundled; no network access needed during install (except optional model download on first run).

## winget Distribution

The `installer/winget/` directory contains the winget manifest for distribution via the Windows Package Manager:

```powershell
winget install KairoPhantom.KairoPhantom
```

## Verification

After install, verify the sidecar is running:
```bash
curl http://127.0.0.1:7438/health
# Expected: {"status": "ok"}
```

Verify the core binary:
```bash
kairo-phantom --version
# Expected: Kairo Phantom 1.x.x
```

## Troubleshooting

| Symptom | Fix |
|:---|:---|
| Sidecar not responding | Check `127.0.0.1:7438` is not in use; restart app |
| Accessibility permission denied (macOS) | System Settings → Privacy & Security → Accessibility → enable Kairo |
| Model download fails (air-gap) | Pre-download models to `models/` dir; see REPLICATE.md |
