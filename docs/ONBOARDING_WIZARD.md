# Kairo Phantom — Onboarding Wizard

> A domain onboarding wizard per Pack that explains "silence means the data isn't clear enough to trust."

## Design Principle

When a user first installs Kairo Phantom, they are guided through a short onboarding wizard that:
1. Selects a Pack (generic / invoice / paper / contract)
2. Explains what the Pack does and what fields it extracts
3. Explains the refusal behavior — silence is a feature, not a bug
4. Optionally ingests a sample document to demonstrate

## Wizard Flow

### Step 1: Welcome
```
Welcome to Kairo Phantom

Kairo answers questions about your documents by citing the exact source
region the answer came from. If it can't ground a claim, it stays silent.

This means: silence = the data isn't clear enough to trust.
You will never see a hallucinated answer.

[Continue]
```

### Step 2: Pack Selection
```
Choose your document type:

  [ ] Generic — any document (summaries, key claims, entities)
  [ ] Invoice — invoices and bills (vendor, amounts, line items, terms)
  [ ] Paper — academic papers (title, authors, findings, figure captions)
  [ ] Contract — legal contracts (parties, terms, cross-references, exhibits)

You can switch Packs at any time.
```

### Step 3: Pack-Specific Explanation

#### Invoice Pack
```
Invoice Pack extracts:
  • Vendor name, invoice number, dates
  • Total amount due, currency, tax
  • Line items, payment terms

What to expect:
  • If the invoice has a clear "Total Amount Due" field, Kairo will
    extract it and highlight the exact line.
  • If the total is in a merged cell or a partially scanned region,
    Kairo may refuse — this means the OCR/layout couldn't confidently
    locate the total. Silence protects you from a wrong number.

  [Try with a sample invoice]
```

#### Contract Pack
```
Contract Pack extracts:
  • Agreement title, parties, effective date
  • Termination date, governing law
  • Cross-references between sections and exhibits

What to expect:
  • If a clause references "Section 4" or "Exhibit A," Kairo will
    extract the reference and highlight both the reference and the target.
  • If a cross-reference is ambiguous (e.g., "as defined above" with no
    specific section), Kairo may refuse — silence means the reference
    couldn't be resolved to a specific, grounded location.

  [Try with a sample contract]
```

#### Paper Pack
```
Paper Pack extracts:
  • Title, authors, abstract
  • Key findings, figure captions
  • Figure-caption-only facts (data that appears only in captions)

What to expect:
  • If a fact appears in a figure caption (e.g., "Figure 3: BERT-Large
    has 340M parameters"), Kairo will extract it and highlight the caption.
  • If a fact is only implied by a figure image but not stated in text,
    Kairo may refuse — silence means the fact isn't in any text region
    the verifier can anchor to.

  [Try with a sample paper]
```

#### Generic Pack
```
Generic Pack extracts:
  • Summary, key claims
  • Entities, topics

What to expect:
  • Kairo will summarize and extract key claims from any document.
  • If a claim cannot be grounded to specific text, Kairo refuses —
    silence means the summary would be a guess, not a grounded extraction.

  [Try with a sample document]
```

### Step 4: Silence Means Trust
```
Understanding Kairo's silence

Kairo's core promise: No source → no answer.

When Kairo refuses to answer, it's not broken. It means:
  1. The document doesn't contain a clear, locatable answer
  2. The OCR/layout couldn't confidently extract the relevant region
  3. The grounding verifier couldn't anchor the model's output to real text

This is by design. A hallucinated answer is worse than no answer.

The refusal panel will always tell you WHY it refused, so you can:
  • Try rephrasing your question
  • Check if the document is complete (not partially scanned)
  • Switch to a different Pack if the document type changed

[Got it — start using Kairo]
```

### Step 5: First Document
```
Drop your first document

Drag and drop a PDF, .txt, or .docx file to get started.
Or use one of the sample documents provided.

[Drop zone appears here]
```

## Wizard State

The wizard runs once on first launch (detected by `--first-run` flag). The selected Pack is saved to config and can be changed later via Settings. The wizard does not modify any documents — it is READ + SUGGEST ONLY.
