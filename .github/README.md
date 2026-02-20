# 🛡️ North African AI Safety Lab (NAAS Lab)
## Project: EL-NUKHBA (The Elite)

![Status](https://img.shields.io/badge/Status-Active_Research-success?style=for-the-badge)
![Grant Application](https://img.shields.io/badge/Grant_Application-EMEA_Youth_%26_Wellbeing_2026_(Submitted)-0b7285?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)
![Tech](https://img.shields.io/badge/Architecture-Agentic_RAG-orange?style=for-the-badge)

> A safeguarding-first agentic tutoring framework for North African education that reduces AI-related harm in Arabic/French/Darija code-switching contexts through verification, risk screening, and measurable outcomes.

---

## Executive summary (≤30 words)
A safeguarding-first agentic tutoring toolkit and evaluation framework that helps youth-serving organisations and educators reduce AI-related educational harm and improve wellbeing and AI literacy outcomes in North Africa.

---

## Why this matters: the safety gap
Young people increasingly use AI for learning and guidance, but safety and developmental appropriateness are not guaranteed—especially in low-resource, code-switching contexts. This can lead to:
1) Educational hallucinations (incorrect facts presented confidently)
2) Misalignment with local curricula and classroom norms
3) Inequitable access to high-quality learning support

NAAS Lab addresses this gap by pairing practical safeguards with independent, shareable evidence on what works in real-world deployments.

---

## What we deliver (practical outputs + independent evidence)

### 1) Practical toolkit (usable by partners)
- **Risk screening checklist** for youth-facing AI use (privacy, misuse, harmful content, age-appropriateness)
- **Safeguarding playbook** (consent/assent guidance, escalation, incident response)
- **AI literacy modules** for youth, parents, and educators
- **Implementation templates** (policies, training agenda, briefing notes)

### 2) Independent evidence (useful beyond direct beneficiaries)
- **Evaluation protocol** for real-world deployments (pre/post + incident logging with minimal data)
- **Impact measurement plan** with clear indicators and collection schedule
- **Stakeholder outputs** (templates for policymakers/regulators, NGOs, and product teams)

---

## How it works (high-level)
EL-NUKHBA uses a verify-then-reply approach:
1) **Retrieve** relevant context from curated sources (no general web retrieval by default)
2) **Draft** a response using structured reasoning
3) **Critique** with a safety/quality check (accuracy, tone, age-appropriateness, misuse risks)
4) **Respond** only if the output meets defined thresholds; otherwise revise or abstain

This repo focuses on making the safeguards operational (checklists, incident workflows, evaluation instruments), not just describing them.

---

## Impact measurement (what we will track)
We use simple, auditable indicators (definitions and instruments in `docs/IMPACT_MEASUREMENT_PLAN.md`):
- **Safety:** rate of unsafe/incorrect outputs intercepted before reaching learners
- **Curriculum alignment:** agreement rate with curated curriculum sources and teacher review sampling
- **Wellbeing (non-clinical):** learner confidence and help-seeking pathways (survey-based, aggregated)
- **AI literacy:** scenario-based judgement improvements (pre/post)
- **Adoption:** uptake of “safe mode” workflows by partner sites

We publish only aggregated, non-identifiable results.

---

## Ethics, safeguarding, and data protection
This project is safeguarding-first and privacy-by-design:
- **Safeguarding policy & incident response:** `SAFEGUARDING.md`
- **Data protection (minimization, storage, retention, publishing rules):** `DATA_PROTECTION.md`

If the project involves direct engagement with minors or their data, the repo documents consent/assent procedures, risk assessment, and incident escalation.

---

## Independence & transparency
We intend to publish methods and findings independently (including failures), and share practical guidance that helps stakeholders understand what safe, responsible AI looks like in real-world youth contexts.

---

## Repository map
- `docs/` — grant alignment, theory of change, roadmap, evaluation protocol, impact measurement plan
- `toolkit/` — checklists, templates, training materials
- `briefs/` — stakeholder-facing brief templates
- `.github/` — CI/CD workflows and engineering automation notes (not the main project narrative)

---

## Quick start (for partners)
1) Read `toolkit/START_HERE.md`
2) Run `toolkit/RISK_SCREENING_CHECKLIST.md`
3) Adopt `SAFEGUARDING.md` and `DATA_PROTECTION.md` requirements
4) Use `docs/EVALUATION_PROTOCOL.md` and `docs/IMPACT_MEASUREMENT_PLAN.md` for measurement and reporting

---

## Legal host, governance, and contact (EMEA eligibility)

**Registered legal entity:** Interactive Training Courses Platform (trading as NAAS AI Safety Lab)
**Jurisdiction:** Algeria (EMEA)
**Project governance:** Independent research project (methods and findings remain independently publishable).
**Project lead:** Houssam Benmerah
**Research contact:** h.benmerah@univ-eltarf.dz
**Repository:** https://github.com/HOUSSAM16ai/NAAS-Agentic-Core

> This repository is maintained by the project team under the registered entity above.
> References to third-party organisations, platforms, or products do not imply endorsement or affiliation.
