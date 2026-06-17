# Kairo Phantom — Zero-Install Web Demo Specification

## Overview
This document specifies the architecture and requirements for the Kairo Phantom zero-install web demo. The goal is to allow prospective users and design partners to try Kairo's refuse-or-cite capability in under 10 seconds without running any command-line installation.

## Key Features
1. **Interactive Document Upload**
   - Supports Drag-and-Drop or File dialog upload for `.txt`, `.md`, `.pdf`, `.docx`.
   - File is parsed entirely inside the user's browser context (using local WASM/JS libraries where possible) or sent to a stateless transient session API with instant garbage collection.

2. **Query Verification Playground**
   - User can ask any arbitrary question about the uploaded document.
   - Outputs a verified grounded answer with pixel bounding boxes highlighted on the document preview.
   - Demonstrates the refusal mechanism: if the answer is not verifiable in the document, it displays an explicit refusal message ("Refused to answer: not verifiable in source text") instead of generating a hallucinated response.

3. **Domain Pack Selector**
   - Dropdown menu to run extraction templates for launch packs:
     - `generic`: Summary, Key Claims, Entities, Topics
     - `invoice`: Vendor, Invoice Number, Totals, Dates
     - `paper`: Title, Authors, Abstract Summary, Key Claims, Methods, Numbers
     - `contract`: Parties, Dates, Obligations, Governing Law

4. **Flywheel Simulation**
   - Allows users to type in corrections for any extracted field.
   - Shows how subsequent extractions for that field are calibrated (i.e. confidence score is lowered) based on the correction history.

## Technical Design
- **Frontend Framework**: Vanilla CSS & HTML with TailwindCSS components or custom glassmorphic aesthetics.
- **Stateless Ingestion**: Utilizes client-side PDF parsing (via PDF.js) and layout analysis to generate the visual page layout and extract chunks.
- **Local Vectors**: Uses a lightweight JS-native bag-of-words / TF-IDF implementation or a tiny WASM embedding model for local semantic searches.
- **Security & Privacy**: Zero server-side persistence of uploaded document content. Chunks are discarded immediately after the session terminates.

## Acceptance Criteria
- Upload to answer time is less than 10 seconds.
- Refusal correctness is 100% on the unanswerable set.
- All resolved citations highlight the correct pixel region of the source text.
