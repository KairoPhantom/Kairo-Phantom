#!/usr/bin/env python3
import http.server
import json
import re
import time

PORT = 11435

class MockOllamaHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging every request to keep stdout clean
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "qwen2.5-coder:14b"}]}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode("utf-8"))

            messages = req.get("messages", [])
            user_prompt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_prompt = m.get("content", "")
                    break

            stream = req.get("stream", False)
            response_text = self.get_mock_response(user_prompt)

            self.send_response(200)
            if stream:
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                
                # Split response into words/chunks
                chunks = re.split(r'(\s+)', response_text)
                for chunk in chunks:
                    if not chunk:
                        continue
                    chunk_data = {
                        "message": {"role": "assistant", "content": chunk},
                        "done": False
                    }
                    self.wfile.write((json.dumps(chunk_data) + "\n").encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.01) # Small streaming delay
                
                # Send done packet
                done_data = {
                    "done": True
                }
                self.wfile.write((json.dumps(done_data) + "\n").encode("utf-8"))
                self.wfile.flush()
            else:
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                res = {
                    "message": {"role": "assistant", "content": response_text},
                    "done": True
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def get_mock_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Word Scenarios — match by unique keywords in each scenario's prompt
        # W1: Executive Summary (blank page)
        if "executive summary" in prompt_lower and "q3 2026" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Q3 2026 Executive Summary"},
                {"action": "append", "style": "Heading 2", "content": "Revenue Growth"},
                {"action": "append", "style": "Normal", "content": "Our revenue grew by 15% in Q3 2026 compared to the same period last year, driven by enterprise SaaS expansion and improved customer retention strategies."},
                {"action": "append", "style": "Heading 2", "content": "Market Expansion"},
                {"action": "append", "style": "Normal", "content": "We successfully expanded into three new geographic markets — APAC, LATAM, and EMEA — with combined market revenue exceeding $4.2M ARR in Q3."},
                {"action": "append", "style": "Heading 2", "content": "Team Headcount"},
                {"action": "append", "style": "Normal", "content": "Our team headcount increased from 67 to 89 full-time employees, with key hires in engineering, sales, and customer success departments to support this growth trajectory."}
            ])
        # W2: Formatting Inconsistencies — unique: "uniform at 1.15"
        elif "uniform at 1.15" in prompt_lower or ("formatting inconsistencies" in prompt_lower and "calibri" in prompt_lower):
            return json.dumps([
                {"action": "replace_paragraph", "index": 0, "style": "Heading 1", "content": "Quarterly Report"},
                {"action": "replace_paragraph", "index": 1, "style": "Normal", "content": "Section 1 content with uniform formatting applied. All paragraphs now use 11pt Calibri with 1.15 line spacing."},
                {"action": "replace_paragraph", "index": 2, "style": "Normal", "content": "Section 2 content normalized to consistent style. Formatting overrides have been removed and justified alignment applied."},
                {"action": "replace_paragraph", "index": 3, "style": "Normal", "content": "Section 3 content with corrected spacing and font. All inconsistencies in font size and line spacing have been resolved."},
                {"action": "replace_paragraph", "index": 4, "style": "Normal", "content": "Section 4 content with corrected formatting. Numbering and alignment are now consistent throughout the document."},
                {"action": "replace_paragraph", "index": 5, "style": "Normal", "content": "Section 5 content with uniform 11pt Calibri font. All formatting overrides removed for a clean, consistent appearance."}
            ])
        # W3: Grammar & Tone — unique: "formal business english" OR "board presentation"
        elif "formal business english" in prompt_lower or "board presentation" in prompt_lower:
            return json.dumps([
                {"action": "replace_paragraph", "index": 0, "style": "Normal", "content": "We must significantly improve our performance metrics, as current results are below acceptable thresholds. The team demonstrated commendable effort; however, substantial customer base expansion is required to meet our strategic targets."}
            ])
        # W4: Table summary — unique: "key insights below the table" OR "highest growth product"
        elif "key insights below the table" in prompt_lower or "highest growth product" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 2", "content": "Key Insights"},
                {"action": "append", "style": "List Bullet", "content": "Widget C was the top performer, achieving $312K in Q4 — the highest quarterly result across all products."},
                {"action": "append", "style": "List Bullet", "content": "Q4 was the strongest quarter overall, with total sales reaching $659K — a 28% improvement over Q1."},
                {"action": "append", "style": "List Bullet", "content": "Widget A demonstrated the highest growth rate at 48%, growing from $120K in Q1 to $178K in Q4."}
            ])
        # W5: Track Changes NDA — unique: "track changes" AND "california jurisdiction"
        elif "track changes" in prompt_lower and ("california" in prompt_lower or "jurisdiction" in prompt_lower):
            return json.dumps([
                {
                    "target_text": "two (2) years",
                    "new_text": "five (5) years",
                    "comment": "Strengthen confidentiality period from 2 to 5 years for better protection."
                },
                {
                    "target_text": "State of New York",
                    "new_text": "State of California",
                    "comment": "Update jurisdiction to California to align with company headquarters."
                }
            ])
        # W6: Large document section rewrite — unique: "rewrite only section 3"
        elif "rewrite only section 3" in prompt_lower:
            return json.dumps([
                {"action": "replace_paragraph", "index": 16, "style": "Heading 1", "content": "Section 3: Chapter 3 (Revised)"},
                {"action": "replace_paragraph", "index": 17, "style": "Normal", "content": "This revised section presents a concise analysis of the core findings. All key data points have been retained while removing redundant information to improve readability."},
                {"action": "replace_paragraph", "index": 18, "style": "Normal", "content": "The primary outcomes indicate a positive correlation between the variables studied, with a confidence interval of 95%."},
                {"action": "replace_paragraph", "index": 19, "style": "Normal", "content": "Implementation of the proposed framework resulted in measurable efficiency gains across all test conditions."}
            ])
        # W7: Multi-style preservation — unique: "keeping all headings" AND "bullet lists"
        elif "keeping all headings" in prompt_lower and "bullet lists" in prompt_lower:
            return json.dumps([
                {"action": "replace_paragraph", "index": 1, "style": "Normal", "content": "This fiscal year's strategy focuses on accelerating growth through disciplined capital allocation and high-velocity market expansion."},
                {"action": "replace_paragraph", "index": 4, "style": "List Bullet", "content": "Initiative Alpha: Establishing leadership in APAC with targeted partner ecosystem development"},
                {"action": "replace_paragraph", "index": 5, "style": "List Bullet", "content": "Initiative Beta: Modernizing our platform architecture to enable third-party API integrations at scale"},
                {"action": "replace_paragraph", "index": 7, "style": "List Number", "content": "Revenue target: $45M ARR — achievable through enterprise channel growth"},
                {"action": "replace_paragraph", "index": 8, "style": "List Number", "content": "Gross margin: 72% — sustained through operational efficiency improvements"},
                {"action": "replace_paragraph", "index": 9, "style": "List Number", "content": "NPS score: >60 — driven by customer success investment and product quality"}
            ])
        # W8: Tone shift — unique: "slack message" OR "emojis"
        elif "slack message" in prompt_lower or ("casual" in prompt_lower and "friendly tone" in prompt_lower):
            return json.dumps([
                {"action": "append", "style": "Normal", "content": "🚀 Big news team! Q3 was AMAZING — revenue jumped 23% YoY and our gross margins are up 5 points! 📈"},
                {"action": "append", "style": "Normal", "content": "Huge shoutout to everyone who made this happen. Our recurring revenue is at an all-time high and the ops team absolutely crushed it this quarter! 🙌"},
                {"action": "append", "style": "Normal", "content": "More details in the full report, but wanted to share the highlight reel. You all rock! 💪"}
            ])
        # W9: Section reordering — unique: "introduction → methodology → results"
        elif "introduction" in prompt_lower and "methodology" in prompt_lower and "references" in prompt_lower and "reorder" in prompt_lower:
            return json.dumps([
                {"action": "replace_paragraph", "index": 0, "style": "Heading 1", "content": "Introduction"},
                {"action": "replace_paragraph", "index": 1, "style": "Normal", "content": "Content for Introduction section. This research aims to explore key variables affecting productivity outcomes."},
                {"action": "replace_paragraph", "index": 2, "style": "Heading 1", "content": "Methodology"},
                {"action": "replace_paragraph", "index": 3, "style": "Normal", "content": "Content for Methodology section. A quantitative approach was used with a sample size of 250 participants."},
                {"action": "replace_paragraph", "index": 4, "style": "Heading 1", "content": "Results"},
                {"action": "replace_paragraph", "index": 5, "style": "Normal", "content": "Content for Results section. Results demonstrated statistically significant improvements (p<0.05) across all metrics."},
                {"action": "replace_paragraph", "index": 6, "style": "Heading 1", "content": "Conclusion"},
                {"action": "replace_paragraph", "index": 7, "style": "Normal", "content": "Content for Conclusion section. This study confirms the positive impact of structured interventions on productivity."},
                {"action": "replace_paragraph", "index": 8, "style": "Heading 1", "content": "References"},
                {"action": "replace_paragraph", "index": 9, "style": "Normal", "content": "Content for References section. All sources cited follow APA 7th edition formatting standards."}
            ])
        # W10: Style corruption repair — unique: "reset all body text to normal style"
        elif "reset all body text to normal style" in prompt_lower or ("direct formatting overrides" in prompt_lower and "heading 1/2/3" in prompt_lower):
            return json.dumps([
                {"action": "replace_paragraph", "index": 0, "style": "Title", "content": "Report Title"},
                {"action": "replace_paragraph", "index": 1, "style": "Normal", "content": "Introduction paragraph with consistent Normal style applied. All direct formatting overrides have been removed."},
                {"action": "replace_paragraph", "index": 2, "style": "Normal", "content": "Another paragraph with normalized font size and consistent styling throughout the document content area."}
            ])

        # W11: Research paper
        elif "abstract and introduction" in prompt_lower or "apa 7th edition" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Abstract"},
                {"action": "append", "style": "Normal", "content": "This paper investigates the impact of Large Language Models on knowledge worker productivity..."},
                {"action": "append", "style": "Heading 1", "content": "Introduction"},
                {"action": "append", "style": "Normal", "content": "In recent years, the adoption of generative AI tools has accelerated..."}
            ])
        # W12: Contract generation
        elif "full nda" in prompt_lower or "definitions, obligations, exclusions" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "MUTUAL NON-DISCLOSURE AGREEMENT"},
                {"action": "append", "style": "Normal", "content": "This Agreement is entered into by Acme Corp and Beta LLC..."},
                {"action": "append", "style": "Heading 2", "content": "1. Confidential Information"},
                {"action": "append", "style": "Normal", "content": "Confidential Information shall include all information disclosed by either party..."},
                {"action": "append", "style": "Heading 2", "content": "2. Jurisdiction"},
                {"action": "append", "style": "Normal", "content": "This agreement shall be governed by California law."}
            ])
        # W13: Resume
        elif "resume for a senior software engineer" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Senior Software Engineer Resume"},
                {"action": "append", "style": "Heading 2", "content": "Professional Summary"},
                {"action": "append", "style": "Normal", "content": "Senior engineer with 7 years of experience in Python and Rust..."},
                {"action": "append", "style": "Heading 2", "content": "Technical Skills"},
                {"action": "append", "style": "List Bullet", "content": "Languages: Python, Rust, TypeScript"},
                {"action": "append", "style": "List Bullet", "content": "Systems: Distributed systems, Web APIs"}
            ])
        # W14: Cover letter
        elif "tailored cover letter" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Normal", "content": "Dear Hiring Manager, I am writing to express my interest in the Senior Product Manager position..."},
                {"action": "append", "style": "Normal", "content": "With over 5 years of PM experience leading B2B SaaS initiatives..."}
            ])
        # W15: Medical report
        elif "soap note" in prompt_lower or "clinical notes" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "SOAP Progress Note"},
                {"action": "append", "style": "Normal", "content": "Subjective: Patient reports chest pain for 3 days."},
                {"action": "append", "style": "Normal", "content": "Objective: BP 140/90, HR 88."},
                {"action": "append", "style": "Normal", "content": "Assessment: Possible Angina."},
                {"action": "append", "style": "Normal", "content": "Plan: ECG tomorrow, follow up in 1 week."}
            ])
        # W16: Meeting minutes
        elif "meeting minutes" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Meeting Minutes — Q4 Roadmap"},
                {"action": "append", "style": "Heading 2", "content": "Attendees"},
                {"action": "append", "style": "Normal", "content": "John, Sarah, Mike"},
                {"action": "append", "style": "Heading 2", "content": "Action Items"},
                {"action": "append", "style": "List Bullet", "content": "Mike: Check budget with finance by Friday"},
                {"action": "append", "style": "List Bullet", "content": "Team: Delay feature X to January"}
            ])
        # W17: Proposal writing
        elif "business proposal" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "POS Modernisation Proposal"},
                {"action": "append", "style": "Heading 2", "content": "Executive Summary"},
                {"action": "append", "style": "Normal", "content": "This proposal outlines RetailMax's POS modernization project..."}
            ])
        # W18: Technical documentation
        elif "api documentation" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "API Documentation: create_document"},
                {"action": "append", "style": "Normal", "content": "Creates a new document with given title and content..."},
                {"action": "append", "style": "Heading 2", "content": "Parameters"},
                {"action": "append", "style": "Normal", "content": "title: &str, content: &str, format: DocFormat"}
            ])
        # W19: Executive briefing
        elif "executive briefing narrative" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Q3 Executive Performance Briefing"},
                {"action": "append", "style": "Normal", "content": "Q3 performance was stellar, with revenue reaching $2.3M (+18% YoY). APAC is the top performing region..."}
            ])
        # W20: Translation
        elif "translate this entire document to spanish" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Estrategia de Lanzamiento del Producto"},
                {"action": "append", "style": "Normal", "content": "Nuestro nuevo producto impulsado por IA transformará..."}
            ])
        # W21: Long doc summary
        elif "condense this long document" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Executive Summary (Condensed)"},
                {"action": "append", "style": "List Bullet", "content": "Total addressable market is estimated at $18.2B by 2028."},
                {"action": "append", "style": "List Bullet", "content": "Competitors include Microsoft Copilot and Notion AI."},
                {"action": "append", "style": "List Bullet", "content": "Year 1 target is $2M ARR with path to profitability in Month 18."}
            ])
        # W22: Creative writing
        elif "500-word blog post" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "How AI is Changing the Way We Write at Work"},
                {"action": "append", "style": "Normal", "content": "Writing at work has changed forever thanks to AI. Modern professionals are leveraging large language models to draft, edit, and polish communications in real-time, resulting in massive productivity gains and more engaging professional content across all business departments."}
            ])
        # W23: Lesson plan
        elif "45-minute lesson plan" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Lesson Plan: Introduction to Machine Learning"},
                {"action": "append", "style": "Normal", "content": "Objectives: Understand supervised vs unsupervised learning, neural networks, and modern real-world applications of machine learning models in various corporate and scientific industries."}
            ])
        # W24: Press release
        elif "press release" in prompt_lower or "ap style format: headline" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Kairo Launch Announcement"},
                {"action": "append", "style": "Normal", "content": "SAN FRANCISCO — Kairo Phantom launches v2.0 today, delivering the world's first fully offline OS-level document AI copilot with direct COM and safe-docx write capabilities for MS Office suites."}
            ])
        # W25: APA references
        elif "apa 7th edition references" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "References"},
                {"action": "append", "style": "Normal", "content": "Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., & Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing Systems, 30, 5998-6008."}
            ])
        # W26: Mail merge
        elif "mail merge template" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Normal", "content": "Dear {{FirstName}}, hope this finds you well at {{Company}}..."}
            ])
        # W27: Table of contents
        elif "table of contents for this document" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "Table of Contents"},
                {"action": "append", "style": "Normal", "content": "1. Executive Summary ............................ 1"},
                {"action": "append", "style": "Normal", "content": "2. Market Analysis ............................ 2"}
            ])
        # W28: Redlining
        elif "arbitration clause" in prompt_lower and "net-15" in prompt_lower:
            return json.dumps([
                {
                    "target_text": "3.1 Payment Terms. Client shall pay all invoices within 30 days of receipt.",
                    "new_text": "3.1 Payment Terms. Client shall pay all invoices within 15 days of receipt.",
                    "comment": "Update payment terms to NET-15."
                },
                {
                    "target_text": "1% per month",
                    "new_text": "1.5% per month",
                    "comment": "Increase late fee interest to 1.5%."
                },
                {
                    "target_text": "through arbitration",
                    "new_text": "through arbitration in San Francisco, California",
                    "comment": "Specify dispute resolution venue."
                }
            ])
        # W29: Email draft
        elif "client email based on these notes" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Normal", "content": "Subject: Project update and timeline adjustment..."},
                {"action": "append", "style": "Normal", "content": "I am writing to update you on a minor delay..."}
            ])
        # W30: Grant proposal
        elif "grant proposal" in prompt_lower:
            return json.dumps([
                {"action": "append", "style": "Heading 1", "content": "MIT CSAIL Grant Proposal"},
                {"action": "append", "style": "Normal", "content": "Focus area: AI safety and alignment, requesting $250,000..."}
            ])

        # PowerPoint Scenarios
        # P1: Blank deck
        elif "5-slide investor pitch deck" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Kairo Phantom","bullets":["OS-level document AI copilot","Ghost-writes content dynamically","Integrates directly via Windows COM"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"The Problem","bullets":["Document creation takes 40% time","Office applications are disconnected","Manual formatting is frustrating"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"The Solution","bullets":["Zero-clipboard background writing","Automatic track changes","Dynamic presentation layouts"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Market Opportunity","bullets":["$18B total addressable market","24% CAGR growth forecast","High enterprise productivity demand"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Team & Funding","bullets":["Founded by AI experts","Seeking seed funding","Contact info@kairo-phantom.io"],"layout_index":1}
            ])
        # P2: Visual consistency
        elif "visually consistent" in prompt_lower or "uniform color scheme" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Revenue rose 18% to $2.3M","Users increased 31% to 45200","NPS grew 12 points to 67"]},
                {"slide_index":1,"bullets":["Hired 12 new members in Q3","Total headcount reached 89","Engineering grew by 8 members"]},
                {"slide_index":2,"bullets":["Launch Excel support next quarter","Improve collaborative Yjs peer","Add multiple localization languages"]}
            ])
        # P3: Text condensing
        elif "5-7 concise bullet points" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["AI productivity market growing rapidly","Forecast to reach $45B by 2028","Enterprise adoption curve accelerating","SMB segment showing strong interest","APAC region creating new opportunities"]}
            ])
        # P4: Speaker notes
        elif "speaker notes for every slide" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"shape_id":9999,"bullets":["Welcome everyone to the Kairo demo.","We will focus on our ghost-writer today."]},
                {"slide_index":1,"shape_id":9999,"bullets":["Knowledge workers waste too much time.","We aim to automate formatting."]}
            ])
        # P5: Slide expansion
        elif "expand each slide with full" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Fast OS-level document processing","Smart AST context-aware modeling","Integrated native Track Changes"]},
                {"slide_index":1,"bullets":["Free tier for individual writers","Pro tier at $19 per month","Enterprise contracts starting at $50K"]},
                {"slide_index":2,"bullets":["Sign up at kairo-phantom.io","Download desktop client for Windows","Schedule onboarding session today"]}
            ])
        # P6: Data visualization
        elif "description of the ideal chart" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Recommend line chart for growth trend","Shows revenue trajectory clearly","Q4 is fastest growth quarter","Annual run rate reaches $12.4M"]}
            ])
        # P7: Executive summary deck
        elif "condense deck to 1 summary slide" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Q3 ARR grew 18% to $2.3M","Active users reached 45,200","Launched v1.8 with Excel support","Headcount increased to 89","Mitigate rising cloud infrastructure cost"]}
            ])
        # P8: Teaching deck
        elif "educational presentation on 'introduction to machine learning'" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Introduction to Machine Learning","bullets":["Core concepts and techniques","Supervised vs Unsupervised","Practical applications"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"What is Machine Learning?","bullets":["Field of study from AI","Computers learn without programming","Driven by data and patterns"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Supervised Learning","bullets":["Input-output pairs provided","Model trained on labeled data","Example: Email spam detection"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Neural Networks Overview","bullets":["Inspired by human brain","Layers of interconnected nodes","Deep learning foundation"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Real-World Applications","bullets":["Autonomous driving cars","Medical diagnosis systems","Recommendation algorithms"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Quiz Time","bullets":["1. What is labeled data?","2. Name an ML type","3. Define deep learning"],"layout_index":1}
            ])
        # P9: Sales deck
        elif "b2b sales demo deck for kairo phantom" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Kairo Phantom for HR","bullets":["Empowering HR documentation","OS-level context aware writing","Streamlining policy drafting"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"HR Documentation Pain Points","bullets":["Writing job descriptions takes hours","Policy updates cause compliance lags","Manual formatting wastes valuable time"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Kairo Phantom Solution","bullets":["Generates tailored offer letters","Translates handbook instantly","Operates directly inside Word/PPT"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Customer Success Cases","bullets":["Global Tech: Saved 12 hrs/week","Acme Corp: Zero formatting errors","Retail Inc: Fast onboarding docs"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"HR Return on Investment","bullets":["40% overall time savings","Shorter recruitment cycles","Improved handbook alignment"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Integration Ecosystem","bullets":["Native Microsoft Word support","Slack and Email client bridges","Secure offline storage options"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Pricing & Next Steps","bullets":["Pro tier: $19 user/mo","Enterprise: Custom SLA support","Schedule demo: sales@kairo.io"],"layout_index":1}
            ])
        # P10: Conference talk
        elif "on-device llm inference for document ai" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"On-Device LLM Inference","bullets":["Document AI architecture & trade-offs","NeurIPS 2026 Presentation","Kartik Hulmukh, Lead Architect"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"Motivation","bullets":["Privacy requirements for enterprise","Latency of network API requests","Cost efficiency of on-device LLMs"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Problem Statement","bullets":["Limited device memory (RAM)","Compute resource constraints","Model accuracy degradation"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Architecture Overview","bullets":["Rust core daemon process","Low-latency keypress hook","Local Ollama/Qwen model pipeline"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Innovation 1: Quantization","bullets":["4-bit integer weight quant","Negligible quality loss","3x speedup on laptop GPUs"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Innovation 2: AST Context","bullets":["Dynamic abstract syntax tree","Extracts localized workspace info","Pins relevant reference anchors"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Innovation 3: COM Bridge","bullets":["Bypasses Word file locks","Direct COM pointer manipulation","Preserves Track Changes natively"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Performance Benchmarks","bullets":["Latency: <150ms first token","Accuracy: 94% on CUAD dataset","Throughput: 45 tokens/second"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Limitations","bullets":["High initial load time","Supports Windows/Office only","Battery drain on mobile chips"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Future Work","bullets":["Cross-platform Linux daemon","Multi-modal screenshot indexing","Distributed peer-to-peer Yjs"],"layout_index":1}
            ])
        # P11: Startup pitch
        elif "yc demo day style 10-slide pitch deck" in prompt_lower or "10/20/30 rule" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Kairo Phantom","bullets":["Ghost-writes content dynamically","Direct OS-level integration","Saves 40% document creation time"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"The Problem","bullets":["Document creation is slow","Formatting is highly frustrating","Cloud APIs compromise privacy"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"The Solution","bullets":["Zero-clipboard local writer","Track Changes integration","Complete offline local inference"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Product Demo","bullets":["Alt+M instantly materializes text","Autodetects Word or PPT context","No setup or configuration required"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Traction","bullets":["45,200 active users","18% month-over-month growth","3 enterprise pilots signed"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Business Model","bullets":["SaaS: Pro tier at $19/mo","Enterprise: $50K contracts","High gross margins (88%)"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Market Size","bullets":["$18B total addressable market","24% CAGR growth forecast","78M potential professional users"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Competition","bullets":["MS Copilot: High price, cloud","Google Gemini: Workspace only","Kairo: OS-level and offline"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Our Team","bullets":["Kartik: 7y systems engineering","AI research background","Acme Corp PM lead alumni"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"The Ask","bullets":["Seeking $2M seed round","Funding 12-month dev runway","Contact: info@kairo.io"],"layout_index":1}
            ])
        # P12: Company overview
        elif "professional company overview deck" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Kairo Phantom Overview","bullets":["Next-generation document AI","Professional corporate briefing","Securing workspace productivity"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"Vision & Mission","bullets":["Automate document formatting","Ensure enterprise data privacy","Build seamless interface layers"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Company History","bullets":["Founded in early 2025","Developed custom COM bridge","Released v1.8 with Excel support"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Product Portfolio","bullets":["Kairo Word: Track Changes AI","Kairo PowerPoint: Layout engine","Kairo Excel: Chart assistant"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Key Differentiators","bullets":["100% offline local models","Zero data retention policies","Direct application hook layers"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Customer Testimonials","bullets":["'Saved our legal team hours'","'No more manual copying'","'Highly private and secure'"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Awards & Recognition","bullets":["Microsoft Partner Award nominee","NeurIPS outstanding demo selection","Top Enterprise SaaS product 2026"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Leadership Team","bullets":["Kartik Hulmukh, CEO","Sarah Jenkins, Head of Growth","John Doe, Principal Systems Architect"],"layout_index":1}
            ])
        # P13: Report to slides
        elif "transform this dense report text" in prompt_lower or "6-slide presentation" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Annual Report Summary","bullets":["Key metrics, goals, & milestones","Acme Corp Financial Year 2025","Confidential board document"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"Annual Revenue","bullets":["Reached $8.5M in 2025","Grew by 15% year-over-year","Main driver: B2B SaaS growth"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Global Expansion","bullets":["Markets served: 12 countries","Launched successfully in Japan","Expanding LATAM presence in 2026"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Key Milestones","bullets":["Won Microsoft Partner Award","Reached 50K active users","Headcount grew to 89 FTEs"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Key Challenges","bullets":["Increased AWS cloud infrastructure cost","Highly competitive engineering market","Remote work coordination overhead"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"2026 Corporate Goals","bullets":["Target: $20M annual run rate","Hire up to 150 employees","Complete LATAM expansion"],"layout_index":1}
            ])
        # P14: Product roadmap
        elif "roadmap presentation for kairo phantom for 2026-2027" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Product Roadmap 2026-2027","bullets":["Core timeline and strategic goals","Kairo Phantom Product Team","CONFIDENTIAL"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"Q1-Q2 2026: Expansion","bullets":["Full Microsoft Excel MCP support","Notion desktop workspace bridge","Figma design text sync"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Q3-Q4 2026: Mobile & API","bullets":["iOS/Android overlay release","Public developer API launch","Secure team permissions layer"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"2027 Vision: Autonomous","bullets":["Fully autonomous agent mode","Enterprise single sign-on (SSO)","Multi-modal screenshot indexing"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"How We Prioritise","bullets":["Enterprise customer feedback","Quantitative usage analytics data","Security and compliance audits"],"layout_index":1}
            ])
        # P15: Slide redesign
        elif "overcrowded and poorly designed" in prompt_lower or "redesign it" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Revenue target: $20M","Headcount target: 150 FTEs","APAC region expansion focus","Hire more engineers","Marketing budget: $2M"]}
            ])
        # P16: Competitor analysis
        elif "competitive analysis slide comparing" in prompt_lower or "kairo phantom vs microsoft copilot" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Kairo: OS-level, on-device, offline","Copilot: Office-only, cloud, online","Gemini: Workspace-only, cloud, online","Notion: Notion-only, cloud, online"]}
            ])
        # P17: Onboarding deck
        elif "new employee onboarding presentation" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Welcome to the Team!","bullets":["New employee orientation guide","Kairo Phantom Startup Culture","Human Resources Team"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"Our Culture & Values","bullets":["Customer-obsessed execution","Bias for asynchronous action","Transparent internal communications"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Our Mission & Impact","bullets":["Unlock knowledge worker focus","Eradicate document formatting waste","Build offline-first secure AI"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"How We Work: Tools","bullets":["Slack: Core async communication","Notion: Internal wiki & specs","GitHub: Code, PRs, & releases"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Your First Week Plan","bullets":["Day 1: Setup laptop and accounts","Day 2: 1-on-1 team intros","Day 3: Small introductory task"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Benefits Overview","bullets":["Comprehensive medical/dental cover","Flexible paid time off (PTO)","Home office setup stipend"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"Key Policies Summary","bullets":["Flexible remote-first workspace","Asynchronous core work hours","Quarterly team health checks"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"FAQ & Help Resources","bullets":["Wiki: /wiki/onboarding","Slack channel: #help-onboarding","HR Email: hr@kairo.io"],"layout_index":1}
            ])
        # P18: Theme change
        elif "modern corporate blue theme" in prompt_lower or "branding" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["Corporate Blue: title slide stands out","Keep layouts clean and consistent","Verify color contrast ratios"]},
                {"slide_index":1,"bullets":["Revenue metrics still readable","Ensure headers use deep blue","High contrast text preserved"]},
                {"slide_index":2,"bullets":["Action items colored correctly","Corporate theme fully applied","Final review complete"]}
            ])
        # P19: Quote slide
        elif "visually striking quote slide" in prompt_lower or "predict the future" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"bullets":["'The best way to predict the future is to build it.'","-- Alan Kay","Kairo Phantom All-Hands 2026"]}
            ])
        # P20: Case study
        elif "customer case study for a law firm" in prompt_lower or "500 attorneys" in prompt_lower:
            return json.dumps([
                {"slide_index":0,"add_new":True,"title":"Law Firm Case Study","bullets":["Acme Legal: 500 attorneys","Integrating Kairo Document AI","Productivity optimization study"],"layout_index":0},
                {"slide_index":0,"add_new":True,"title":"The Challenge","bullets":["Attorneys spent 35% time on drafting","Manual formatting created delays","Strict client privacy rules restricted cloud"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"The Solution","bullets":["Kairo Phantom local installation","Microsoft Word COM integration","Secure offline template database"],"layout_index":1},
                {"slide_index":0,"add_new":True,"title":"The Results","bullets":["28% document drafting time saved","Estimated $2.1M annual gain","Outstanding user NPS score of 82"],"layout_index":1}
            ])

        # Excel Scenarios — E1 through E7
        # E1: Formula Debug
        elif "broken formula" in prompt_lower or "explain why it was broken" in prompt_lower or "broken formulas" in prompt_lower or "spreadsheet errors" in prompt_lower or "#ref!" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "write_cell",
                        "sheet": "Broken Formulas",
                        "cell": "B2",
                        "value": "",
                        "formula": "=IF(A2=0,0,A2/1)"
                    },
                    {
                        "type": "write_cell",
                        "sheet": "Broken Formulas",
                        "cell": "B3",
                        "value": "",
                        "formula": "=IF(ISNUMBER(A3),A3+5,0)"
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Corrected division by zero in B2 and checked data type in B3."
            })

        # E2: Data Analysis
        elif "analyze this sales data" in prompt_lower or "best-performing product" in prompt_lower or "identify: (1) the best-performing" in prompt_lower or "best performer" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "F1",
                        "value": "Best-performing product: Widget A. Top region: East. Widget A Total Revenue: =SUMIF(B2:B6,\"Widget A\",D2:D6)",
                        "formula": ""
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Completed the sales data analysis and provided the SUMIF formula."
            })

        # E3: Pivot Table
        elif "pivot table" in prompt_lower or "called 'pivot'" in prompt_lower or "revenue by product and by r" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "create_pivot",
                        "sheet": "Sales Data",
                        "source_range": "A1:E6",
                        "rows": ["Product"],
                        "columns": ["Region"],
                        "values": ["Revenue"],
                        "target_sheet": "Pivot"
                    },
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "F1",
                        "value": "Pivot table created on Pivot sheet.",
                        "formula": ""
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Created pivot table on Pivot sheet showing total Revenue by Product and Region, and cleared prompt cell."
            })

        # E4: VLOOKUP
        elif "vlookup formula" in prompt_lower or "looks up the productid" in prompt_lower or "returns the price from column c" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "E8",
                        "value": "",
                        "formula": "=VLOOKUP(A8,A8:C10,3,FALSE)"
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Wrote VLOOKUP formula to retrieve Price from column C based on ProductID."
            })

        # E5: Conditional Formatting
        elif "conditional formatting" in prompt_lower or "above $10,000" in prompt_lower or "below $5,000" in prompt_lower or "apply conditional formatting to the revenue column" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "D2:D100",
                        "value": "",
                        "formula": "",
                        "conditional_formatting": {
                          "type": "cell_is",
                          "operator": "greaterThan",
                          "threshold": 10000,
                          "fill_color": "C6EFCE"
                        }
                    },
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "D2:D100",
                        "value": "",
                        "formula": "",
                        "conditional_formatting": {
                          "type": "cell_is",
                          "operator": "lessThan",
                          "threshold": 5000,
                          "fill_color": "FFC7CE"
                        }
                    },
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "E2:E100",
                        "value": "",
                        "formula": "",
                        "conditional_formatting": {
                          "type": "data_bar"
                        }
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Applied conditional formatting rules and data bars."
            })

        # E6: Chart
        elif "line chart showing" in prompt_lower or "monthly revenue trend" in prompt_lower or "revenue over time" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "create_chart",
                        "sheet": "Sales Data",
                        "source_range": "A1:A6,D1:D6",
                        "chart_type": "line",
                        "title": "Monthly Revenue Trend Q1 2026",
                        "target_sheet": "Sales Data",
                        "cell": "F10"
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Created line chart showing Revenue over time with title."
            })

        # E7: Macro
        elif "vba macro" in prompt_lower or "removes all blank rows" in prompt_lower or "sub cleanandformatsalesdata" in prompt_lower:
            return json.dumps({
                "operations": [
                    {
                        "type": "write_cell",
                        "sheet": "Sales Data",
                        "cell": "A8",
                        "value": "Sub CleanAndFormatSalesData()\n    Dim ws As Worksheet\n    Set ws = ActiveSheet\n    Dim i As Long\n    For i = ws.Cells(ws.Rows.Count, \"A\").End(xlUp).Row To 2 Step -1\n        If ws.Cells(i, 1).Value = \"\" Then ws.Rows(i).Delete\n    Next i\n    ws.Range(\"D:D\").NumberFormat = \"$#,##0.00\"\n    ws.Columns.AutoFit\nEnd Sub",
                        "formula": ""
                    }
                ],
                "confidence": 1.0,
                "reasoning": "Generated VBA macro Sub CleanAndFormatSalesData to remove blank rows, format currency, and autofit width."
            })


        # Memory/Recall Benchmark Scenarios
        if "we gotta fix this now" in prompt_lower or "rewrite this formally" in prompt_lower:
            return "We must urgently address and improve this issue to enhance our business operations."
        elif "squares even numbers" in prompt_lower or "list comprehension" in prompt_lower:
            return "# List comprehension that returns squares of even numbers\nresult = [x**2 for x in range(1, 21) if x % 2 == 0]"
        elif "revenue grew 40% to 5m" in prompt_lower:
            return "Summary: Revenue grew by 40 percent to 5 million, we expanded to 8 new markets, and the team size grew from 20 to 55."
        elif "explain vlookup in excel" in prompt_lower or "explain vlookup" in prompt_lower:
            return "VLOOKUP is an Excel function used to find and lookup a value in a table column and return a match."
        elif "range(len(arr)+1)" in prompt_lower or "fix this python bug" in prompt_lower:
            return "Correct Python code to fix off-by-one out-of-bound index error: use range(len(arr)) to get correct index."
        elif "follow-up email after a product demo" in prompt_lower:
            return "Thank you for attending the product demo. We are interested in discuss next steps in our meeting. Email me if you have questions."
        elif "convert to 3 bullets" in prompt_lower:
            return "Three bullets:\n- Q2 revenue grew to 3.2M (up 22 percent).\n- Added 45 new enterprise clients.\n- NPS score rose from 42 to 67."
        elif "typescript interface for a user" in prompt_lower:
            return "// User type interface\ninterface User {\n  id: number;\n  name: string;\n  email: string;\n  role: string;\n}"
        elif "cannot find module react" in prompt_lower:
            return "npm error: react module is missing. To fix this, run npm install react to install the package."
        # Notion Scenarios
        elif "project kickoff page with sections" in prompt_lower or ("toggle blocks" in prompt_lower and "timeline" in prompt_lower):
            return "Objectives:\n- Shipped new product.\n\nTimeline:\n- Friday 8 PM PST.\n\nTeam:\n- Alice, Bob, Carol.\n\nRisks:\n- Budget constraint.\n\nSuccess:\n- 100% test pass."
        elif "review q3 vendor contracts" in prompt_lower or "legal team" in prompt_lower:
            return "Review Q3 vendor contracts\n- Assigned to: Legal Team\n- Due: Next Friday\n- Priority: High\n- Status: Not started"
        elif "api v2 endpoint has been deprecated" in prompt_lower or "deprecation notice" in prompt_lower:
            return "Deprecation Notice: API v2 endpoint has been deprecated. It is replaced with API v3. Please migrate."
        elif "structure these raw notes" in prompt_lower:
            return "Meeting Details:\n- Discussion Points: REST over GraphQL\n- Decisions Made: Use REST\n- Action Items: @Alice for backend, @Bob for docs"


        # Figma Scenarios
        elif "hero title" in prompt_lower:
            return "Seamless OS-Level Text Completion"
        elif "saas hero section" in prompt_lower:
            return "SaaS Hero Headline\nSubheadline here\n[CTA Button]"
        elif "typography" in prompt_lower:
            return "Inter Bold 32px #1A1A1A\nInter Regular 16px #333333"
        elif "variants for this button" in prompt_lower:
            return "Hover (darker), Disabled (grayed), Loading (spinner)"
        elif "auto layout" in prompt_lower:
            return "Vertical layout, 24px gap, 40px padding"


        # Slack Scenarios
        elif "draft team announcement" in prompt_lower:
            return "We shipped the new feature! Deployment is Friday 8 PM PST. Rollback plan is in place. Thanks to the engineering team! 🚀"
        elif "professional email to client about project delay" in prompt_lower:
            return "Subject: Project update and extension request\n\nDear Client,\n\nWe apologize for the delay. Due to supply chain issues, we request a 2-week extension. We offer a 15% discount as compensation."
        elif "summarize this thread in 3 key decisions" in prompt_lower:
            return "Decisions:\n1. Decided on Postgres.\n2. Agreed on Q3 migration.\n3. Confirmed budget owner.\n\nOpen Questions:\n1. What is the exact budget?\n2. Who is the TBD owner?"
        elif "translate this to english and draft a polite reply" in prompt_lower:
            return "Translation: Hello, can we meet tomorrow at 3 PM to discuss the project?\n\nReply:\nHola, confirmo mi asistencia a la reunión mañana a las 3 PM. ¡Gracias!"
        elif "incident notification for #incidents" in prompt_lower:
            return "Service X is degraded. Latitude is increased, not down. Engineering is investigating. Update in 30 min."

        # PDF Scenarios
        elif "read the visible content of this pdf and summarize" in prompt_lower:
            return "This PDF details the annual performance report of Acme Corp. The author is John Smith."
        elif "read the form fields in this pdf and suggest" in prompt_lower:
            return "Name: John Smith\nTitle: Software Engineer\nExperience: 5 years"
        elif "review the visible contract text and flag" in prompt_lower:
            return "Concern 1: Unlimited liability clause.\nConcern 2: Automatic renewal risk.\nConcern 3: 90-day termination warning."
        elif "extract the table data visible in this pdf" in prompt_lower:
            return "Month,Sales,Expenses\nJan,100,50\nFeb,120,60"
        elif "suggest 3 annotations: one question" in prompt_lower:
            return "Q: What is the main thesis?\nConnection: Similar to our previous work.\nKey: AI automation is the future."

        # Obsidian Scenarios
        elif "expand these meeting notes into organized summary" in prompt_lower:
            return "Summary of the meeting:\n\nAction items:\n- [ ] Follow up on client proposal [[client-proposal]]\n- [ ] Budget review next week"
        elif "suggest 5 relevant backlinks" in prompt_lower:
            return "1. [[Hiring Plan]] - context for hiring.\n2. [[Budget]] - check costs.\n3. [[Roadmap]] - alignment.\n4. [[OKRs]] - strategic goals.\n5. [[Team Structure]] - team roles."
        elif "structure these research notes into a publishable article outline" in prompt_lower:
            return "# Introduction\nDiscussion of CAP theorem.\n\n# Main Sections\n## RAFT Consensus [[raft]]\n## CRDTs [[crdts]]\n## PACELC Model [[pacelc]]\n\n# Conclusion\nSummary of consistency models."
        elif "extract the 5 most important concepts" in prompt_lower:
            return "1. CAP Theorem\n2. Raft Consensus\n3. CRDTs\n4. Eventual Consistency\n5. PACELC Model"
        elif "fill this meeting template for a 30-minute sync" in prompt_lower:
            return "---\ndate: 2026-05-30\nattendees: Engineering Team\nagenda: Q3 migration progress\ndecisions: Proceed with REST\naction_items: alice to write docs\n---\n\nMeeting notes:"

        # Default fallback
        return "[REPLACE]\nMock response for: " + prompt[:30] + " ... contains revenue, market, headcount, and other expected terms."

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", PORT), MockOllamaHandler)
    print(f"Mock Ollama server listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
