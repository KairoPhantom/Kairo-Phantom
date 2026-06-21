# Kairo Phantom — Public Roadmap

This roadmap is public and community-driven. Items marked **help wanted** are open for contribution.

---

## Scope Boundaries (What Kairo Does and Does Not Do)

### Kairo DOES:
- **Read** documents and extract structured data with grounded citations
- **Suggest** actions to the user (never auto-applies)
- **Refuse** to answer when it cannot ground a claim to source text
- **Audit** every answer and refusal in a tamper-evident signed log
- Run **local-first** with zero network egress by default

### Kairo Does NOT:
- Write to or drive source applications (Word, Excel, desktop) — v1 is READ + SUGGEST ONLY
- Act as a multi-domain expert swarm or router
- Operate as a collaborative/cloud-by-default layer
- Auto-apply any suggestion without explicit human confirmation

---

## Current State (v1 Launch)

| Feature | Status |
|:---|:---|
| Grounding cascade (EXACT → FUZZY → SEMANTIC → BLOCK) | ✅ Shipped |
| 4 Packs (generic, invoice, paper, contract) | ✅ Shipped |
| Provenance chain (Action → Extraction → Chunk → Document) | ✅ Shipped |
| Signed audit log (tamper-evident) | ✅ Shipped |
| Reproducibility receipts | ✅ Shipped |
| Golden corpus snapshot tests | ✅ Shipped |
| Adversarial corpus + red-team flow | ✅ Shipped |
| Standalone verifier crate | ✅ Shipped |
| Air-gap mode (zero egress) | ✅ Shipped |

---

## Roadmap

### Q3 2026 — Post-Launch Hardening

- [ ] **help wanted**: Expand golden corpus to 100+ (document, question) pairs
- [ ] **help wanted**: Add adversarial document types (scanned PDFs, handwritten forms)
- [ ] **help wanted**: Multi-language document support (initial: Spanish, French, German)
- [ ] Tauri overlay polish: citation hover-preview with bbox highlighting
- [ ] Performance: sub-2s cold-start on M1 / Ryzen 7

### Q4 2026 — Enterprise Features

- [ ] **help wanted**: SOC 2 Type II documentation pack
- [ ] Signed installer distribution (macOS notarization, Windows code signing)
- [ ] Enterprise SSO integration (read-only audit log access)
- [ ] **help wanted**: Custom Pack SDK for domain-specific extraction

### 2027 — The 1000x Layer

- [ ] **help wanted**: Community Pack marketplace
- [ ] Federated learning for correction flywheel (opt-in, privacy-preserving)
- [ ] **help wanted**: Cross-document reasoning with multi-hop grounding
- [ ] Visual retrieval (ColQwen2/ColPali) for image-heavy documents

---

## Help Wanted

We welcome contributions in these areas. Each has a `help wanted` label on GitHub.

| Area | Label | Description |
|:---|:---|:---|
| Golden corpus expansion | `help wanted: corpus` | Add (document, question) → expected answer/refusal pairs |
| Adversarial documents | `help wanted: red-team` | Submit adversarial documents that try to break grounding |
| Multi-language support | `help wanted: i18n` | Help Kairo ground citations in non-English documents |
| Custom Packs | `help wanted: packs` | Build domain-specific extraction Packs |
| Verifier integrations | `help wanted: verifier` | Integrate the verifier with more RAG frameworks |
| Documentation | `help wanted: docs` | Improve guides, examples, and API docs |

---

## How to Contribute

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines, scope boundaries, and development setup.

## How to Submit Adversarial Documents

See [red-team/README.md](../red-team/README.md) for the adversarial submission flow and [red-team/submit_template.md](../red-team/submit_template.md) for the submission template.

---

*This roadmap is a living document. Priorities may shift based on community feedback and contribution velocity.*