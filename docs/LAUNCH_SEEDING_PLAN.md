# Kairo Phantom — Launch Seeding Plan

> Dated T-minus checklist from T-14 to launch day.

## Timeline

| Date (T-minus) | Action | Owner | Status |
|:---|:---|:---|:---|
| T-14 | Identify 5–7 local-AI/privacy accounts for early access | Launch lead | ☐ |
| T-14 | Send early-access builds + bench output to selected accounts | Launch lead | ☐ |
| T-14 | Post "I'm building this" teaser on r/LocalLLaMA | Launch lead | ☐ |
| T-12 | Incorporate early-access feedback; fix blocking issues | Eng team | ☐ |
| T-10 | Finalize hero video (90s) from shot list | Video editor | ☐ |
| T-10 | Prepare Show HN post (review body + 3 prepared replies) | Launch lead | ☐ |
| T-7 | Finalize FAQ.md and REPLICATE.md | Eng team | ☐ |
| T-7 | Verify `make bench` reproduces from clean checkout | Eng team | ☐ |
| T-7 | Verify `scripts/replicate.py` runs end-to-end on public corpus | Eng team | ☐ |
| T-5 | Cut signed installers (macOS .dmg + Windows .msi) | Release eng | ☐ |
| T-5 | Verify air-gap mode: `strace` shows zero network egress | Eng team | ☐ |
| T-3 | Soft-launch on r/LocalLLaMA (full post + video) | Launch lead | ☐ |
| T-3 | Monitor r/LocalLLaMA feedback; respond to comments | Launch lead | ☐ |
| T-2 | Prepare HN post for submission; verify all links work | Launch lead | ☐ |
| T-1 | Final dry run: clean machine → install → grounded answer in < 5 min | Eng team | ☐ |
| T-0 (Launch day) | Submit Show HN post at 8–10am US Eastern | Launch lead | ☐ |
| T-0 | Post contrast clip (split-screen thumbnail) to social | Launch lead | ☐ |
| T-0 | Engage one trusted amplifier for retweet of contrast clip | Launch lead | ☐ |
| T+1 | Monitor HN comments; deploy prepared replies as needed | Launch lead | ☐ |
| T+1 | Collect feedback; file issues for top requested features | Eng team | ☐ |
| T+3 | Publish "What we learned from launch" retrospective | Launch lead | ☐ |

## Early Access Accounts (5–7 targets)

Identify accounts in the local-AI/privacy space who:
- Have an existing audience interested in local LLMs, privacy, or document tools
- Are technically credible (can run `make bench` and verify receipts)
- Are likely to share the contrast clip (the highest-leverage asset)

Candidate categories:
1. Local LLM advocates (Ollama/LM Studio community voices)
2. Privacy-focused developers (air-gap, local-first proponents)
3. Document tool reviewers (PDF/OCR/contract analysis space)
4. Open-source Rust/Tauri community members
5. AI safety/alignment researchers (hallucination mitigation angle)

## r/LocalLLaMA Teaser (T-14)

Post title: "Building a local doc Q&A tool that refuses to hallucinate — looking for early testers"

Body: Brief description of the verifier-independence approach, link to the repo, request for feedback on grounding thresholds and refusal UX. Do NOT link the hero video yet — save it for the soft launch.

## HN Timing

- **Day:** Weekday (Tuesday–Thursday preferred; avoid Friday/Monday)
- **Time:** 8–10am US Eastern (peak HN engagement window)
- **Title:** "Show HN: Kairo Phantom – local doc Q&A that refuses to hallucinate (MIT, Rust, offline)"
- **First comment:** Post the cascade ablation results as the first comment to preempt the "can you prove it?" question

## Soft-Launch Order

1. **r/LocalLLaMA first (T-3)** — this community is the most receptive and forgiving. They'll give technical feedback and surface bugs before the wider HN audience sees it.
2. **HN (T-0)** — after r/LocalLLaMA feedback is incorporated. Submit at 8–10am Eastern.
3. **Product Hunt (deprioritized)** — Product Hunt's audience is less technical and less aligned with the local-first/privacy value prop. Only post if the HN launch goes well and there's bandwidth to manage a third channel.

## The Single Highest-Leverage Move

**One trusted amplifier retweet of the contrast clip.**

The 0–8s split-screen contrast frame (cloud tool citing fake text vs. Kairo highlighting real text) is the single most communicative asset. If one trusted voice in the local-AI/privacy space retweets this clip with a one-line endorsement, it will drive more qualified attention than any other single action in the launch plan. Identify this person during the T-14 early-access outreach and confirm their willingness to share on launch day.
