# docs/assets — Recording Guide

This directory holds the GIF and image assets referenced by the root `README.md`.
Until the real recordings are committed, the README will show broken-image icons —
**this is expected**. Record the assets below and drop them into this folder.

## Assets to Record

| File | What to Record | Suggested Duration | Max Size |
|---|---|---|---|
| `banner.png` | A static banner image for the top of the README. Should include the Kairo Phantom logo/wordmark on a dark background. 880×300px or similar. | N/A (static image) | < 1 MB |
| `ghost-typing-hero.gif` | Hero GIF: Kairo Phantom ghost-typing into a real application (e.g., Microsoft Word). Show the agent opening Word and typing a document in real-time. This is the first thing visitors see. | 6–8 s loop | < 5 MB |
| `demo-ghost-typing.gif` | Short demo of ghost-typing into Excel or an IDE — filling cells or writing code. | 5–7 s loop | < 5 MB |
| `demo-receipt.gif` | Demo of the provenance receipt: show an action being taken, then the JSON receipt appearing, then the verification command running and passing. | 6–8 s loop | < 5 MB |
| `demo-airgap.gif` | Demo of air-gap mode: start with `KAIRO_AIR_GAP=true make run`, show the agent working with zero network indicator, confirm offline operation. | 5–7 s loop | < 5 MB |

## Recommended Recording Tools

| Platform | Tool | Notes |
|---|---|---|
| Linux | [Peek](https://github.com/phw/peek) | Simple animated GIF recorder |
| macOS | [Kap](https://getkap.co/) | Free, exports to GIF |
| Windows | [ScreenToGif](https://www.screentogif.com/) | Free, lightweight, built-in editor |

## Recording Tips

1. **Keep it under 8 seconds.** Attention spans are short. A tight loop is better than a long walkthrough.
2. **Keep it under 5 MB.** GitHub renders large GIFs slowly. Reduce frame rate (15 fps is fine) or crop to the relevant window area.
3. **Show the real thing.** No mockups, no staged screenshots. Record actual ghost-typing into a real application.
4. **Loop cleanly.** The GIF should loop seamlessly — start and end at a similar visual state.
5. **Dark theme preferred.** Most developers browsing GitHub use dark mode. A dark background makes the GIF pop.
6. **Crop tightly.** Remove unnecessary window chrome, taskbars, or desktop background. Focus on the app being driven.

## After Recording

```bash
# From the repo root
cd docs/assets

# Copy your recorded files here
cp ~/Downloads/ghost-typing-hero.gif .
cp ~/Downloads/banner.png .
# ... etc

# Commit
git add docs/assets/
git commit -m "docs: add real GIF demos and banner assets"
git push origin master
```

Once committed, the broken-image icons in the README will be replaced with the real recordings.