# Product Roadmap: NAAS-Agentic-Core

This roadmap outlines the 12-month strategic development plan for the North African AI Safety Lab's core toolkit. Our goal is to achieve production-grade reliability for youth-facing GenAI safety evaluation.

## Q1: Protocols & Baseline Suite (Months 1-3)
**Focus:** Establishing rigorous governance and the first version of the code-switching evaluation dataset.

*   [x] **Governance Framework:** Publish SAFEGUARDING.md, DATA_POLICY.md, and ethical review board (ERB) application template.
*   [ ] **Baseline Code-Switching Suite:** Release v0.1 of the Arabic-French-Darija adversarial prompt dataset (500+ curated prompts).
*   [ ] **MVP Verification Logic:** Implement basic "Verify-then-Reply" loop with keyword-based filtering.

**Definition of Done:**
*   Governance documents merged and live.
*   Initial dataset released with datasheets.
*   Basic interception rate > 60% on test set.

## Q2: Toolkit Implementation & Dashboards (Months 4-6)
**Focus:** Building the user-facing tools and improving the interception engine.

*   [ ] **Contextual Agent:** Upgrade verification logic to use LLM-based context awareness (reducing false positives).
*   [ ] **Dashboard V1:** Release local dashboard for visualizing interception rates and PII risks.
*   [ ] **Blind Audit Tool:** Release a simple UI for human reviewers to label model outputs for reliability metrics.

**Definition of Done:**
*   Interception rate > 85% on test set.
*   Dashboard visualizes 4 core metrics.
*   Audit tool used to label 1000+ interactions.

## Q3: Pilot & Workshops (Months 7-9)
**Focus:** Real-world testing with partner NGOs and educational institutions.

*   [ ] **Pilot Deployment:** Deploy the toolkit in a controlled environment with 2 partner schools (supervised).
*   [ ] **Mentor Training Program:** Finalize and distribute the "AI Safety Mentor" training curriculum.
*   [ ] **Workshops:** Host 3 workshops for North African educators on AI safety risks.

**Definition of Done:**
*   Successful pilot with 0 high-severity safety incidents.
*   Feedback collected from 20+ mentors.
*   Pilot report published.

## Q4: Analysis & Publication (Months 10-12)
**Focus:** Disseminating findings and solidifying the open-source community.

*   [ ] **Impact Report:** Publish a comprehensive report on the state of code-switching safety in current LLMs.
*   [ ] **Toolkit v1.0:** Official release with full documentation, stable API, and Docker support.
*   [ ] **Community Handover:** Establish a maintainer committee from the community for long-term sustainability.

**Definition of Done:**
*   Peer-reviewed paper or preprint released.
*   v1.0 release tagged on GitHub.
*   Maintainer governance structure ratified.

> **Note:** This roadmap is subject to change based on research findings and community feedback.
