# Kairo Phantom — Hero Video Shot List

> Segment-by-segment production guide for the 90-second hero video.

## Thumbnail

The thumbnail is the **split-screen contrast frame** from Segment 1 (0–8s): LEFT side shows a cloud tool confidently citing a clause/number that doesn't exist; RIGHT side shows Kairo highlighting the exact pixel of the correct text. This single frame communicates the entire value proposition.

## Shot List

| Timecode | Duration | On-Screen Action | Burned Caption | Audio (optional) |
|:---|:---|:---|:---|:---|
| 0:00–0:08 | 8s | **Split-screen contrast.** LEFT: a cloud LLM chat interface showing a confident answer citing "Section 7.3" with a fabricated quote. A red ✗ overlay appears on the fake citation. RIGHT: Kairo Phantom overlay showing the same question, with the answer highlighted at the exact pixel location in the document, green ✓ overlay. | "ChatGPT cites things that don't exist. Kairo refuses." | Subtle tension build — low drone, then a clean "ding" when Kairo's highlight appears |
| 0:08–0:40 | 32s | **Single document walkthrough (contract).** User drops a contract PDF into Kairo. The document renders. User types: "What is the termination date?" Kairo extracts "June 1, 2029" and highlights the exact line in Section 3. User clicks the highlight — document scrolls to the source region. User types: "What does Section 5 reference?" Kairo shows "Exhibit A" with both the reference in Section 5 and the target in Exhibit A highlighted. | "Drop a PDF. Ask a question. Get the exact source." (appears 0:10) | Clean, minimal ambient — no music, just UI sounds (drop, type, highlight) |
| 0:40–0:60 | 20s | **The refusal moment.** User asks: "What is the penalty for late delivery?" The document has no such clause. Kairo shows the refusal panel: ⚠ icon, "No grounded source found — refusing to answer", and the "why?" explanation. The panel is clearly labeled — not blank, not an error. | "No source found. Kairo stays silent." | Silence — literally 2 seconds of no audio, then a soft tone acknowledging the refusal |
| 0:60–0:90 | 30s | **Architecture callout.** Clean animated diagram: Rust core (trust boundary) → Python sidecar (127.0.0.1:7438) → Tauri overlay (render-only). Text appears: "100% on your machine". Then: "MIT open-source". Then: "make bench prints real numbers" with a terminal clip showing actual bench output. | "100% on your machine · MIT · make bench prints real numbers." | Upbeat, confident close — simple beat that resolves |

## Production Notes

- **Segment 1 (0–8s)** is the hook. The split-screen must be instantly readable at thumbnail size. The red ✗ / green ✓ contrast is the visual anchor.
- **Segment 2 (0:08–0:40)** uses ONE document type only (contract). Do not switch between invoices and papers — the goal is to show the click-back-to-source interaction clearly, not to demo every Pack.
- **Segment 3 (0:40–0:60)** is the trust moment. The refusal must look intentional and well-designed, not like a crash or empty state. The "why?" explanation is critical — it shows the user that silence is a feature.
- **Segment 4 (0:60–0:90)** is the credibility close. The terminal clip showing `make bench` output must be REAL output from a clean run — no fabricated numbers.

## Caption Style

- Font: Inter or system sans-serif, white with subtle dark shadow
- Size: Large enough to read on mobile (min 24px equivalent)
- Position: Lower third, centered
- Duration: Leave on screen for the full segment unless noted

## Aspect Ratio

- Primary: 16:9 (1920×1080) for YouTube/web embed
- Thumbnail crop: 1280×720, center on the split-screen contrast frame
