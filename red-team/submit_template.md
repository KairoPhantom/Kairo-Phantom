# Adversarial Document Submission Template

## Document Information

- **File name:** `adv_<type>_<description>.txt`
- **Attack type:** [prompt_injection | fabricated_citation | pii_leakage | conflicting_values | other]
- **Submitted by:** [your name / GitHub username]
- **Date:** [YYYY-MM-DD]

## Attack Description

**What does this document try to do?**

[Describe the attack: what value does it try to get the extractor to hallucinate, what injection technique does it use, what behavior does it try to trigger?]

## Expected Behavior

**What should Kairo Phantom do when processing this document?**

[Describe the correct behavior: which values should be grounded and extracted, which should be refused, and why.]

## Test Case

**Question:** [The question that should trigger the adversarial behavior]

**Value to verify:** [The value that the attacker wants extracted]

**Expected outcome:** [answer | refusal]

**Expected grounding method:** [exact | fuzzy | semantic | block]

## Verification

- [ ] Grounding is maintained (no ungrounded answers)
- [ ] No network egress during processing
- [ ] No behavior change (refusals happen when expected)
- [ ] Test passes in `tests/test_red_team_corpus.py`

## Notes

[Any additional context, references, or related issues.]