# NAAS-Agentic-Core
### Verify-then-Reply safety evaluation for youth-facing GenAI under Arabic/French/Darija code-switching.

![License](https://img.shields.io/badge/License-MIT-blue.svg) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Status](https://img.shields.io/badge/Status-Active_R%26D-yellow) ![Governance](https://img.shields.io/badge/Governance-Safeguarding_%2B_Data_Policy-red) ![Cite](https://img.shields.io/badge/Cite-CITATION.cff-lightgrey)

> **Why this matters**
> North African youth frequently code-switch between Arabic, French, and Darija. Current safety filters often fail in these mixed-language contexts, exposing minors to harmful content. This toolkit provides a localized, rigorous "Verify-then-Reply" evaluation framework to bridge that gap.

> **Governance & Safeguarding**
> This repository is governed by strict ethical protocols for youth safety. All research involving human subjects or youth-facing data must strictly adhere to [SAFEGUARDING.md](./SAFEGUARDING.md) and [DATA_POLICY.md](./DATA_POLICY.md).

## Architecture: Verify-then-Reply

Our approach intercepts Model interactions to ensure safety before any content reaches the user.

```mermaid
graph LR
    Input[User Input] --> PreChecks[Pre-Checks (PII/Toxicity)]
    PreChecks -->|Pass| Verification[Verification Loop]
    PreChecks -->|Block| Refusal[Immediate Refusal]
    Verification -->|Analyze| SafetyPolicy{Policy Decision}
    SafetyPolicy -->|Safe| Output[Final Output]
    SafetyPolicy -->|Unsafe| Refusal
    Output --> Telemetry[Telemetry & Audit Logs]
    Refusal --> Telemetry
```

## What We Measure

We empirically evaluate GenAI systems against four key safety metrics:

| Metric | Definition | Target |
| :--- | :--- | :--- |
| **Bypass Success Rate** | Percentage of adversarial prompts in mixed Arabic/French/Darija that successfully trigger unsafe generation. | 0% |
| **Interception Rate** | Percentage of unsafe content correctly blocked by the Verify-then-Reply layer (pre/post-generation). | >95% |
| **PII-Risk Events** | Number of potential PII leakage events detected per 100 interaction sessions. | 0 |
| **Reliability Errors** | Rate of false positives/negatives in safety judgments, measured via blinded human audit. | <5% |

## Repository Map

```text
.
├── docs/                       # Evaluation protocols, impact plans, and transparency reports
├── toolkit/                    # Operational tools: screening checklists, incident logs
├── src/                        # Core agentic logic and safety verification code
├── evaluation/                 # Code-switching test suites and benchmarking tools
├── CITATION.cff                # Citation metadata
├── DATA_POLICY.md              # Privacy-by-design and data handling rules
├── SAFEGUARDING.md             # Youth safety, supervision, and escalation protocols
├── SECURITY.md                 # Vulnerability reporting policy
├── CONTRIBUTING.md             # Developer and researcher contribution guide
└── README.md                   # Project overview
```

## Quickstart

**Note:** The following commands are examples. Please align paths to your specific environment and installation.

```bash
# 1. Clone the repository
git clone https://github.com/HOUSSAM16ai/NAAS-Agentic-Core.git
cd NAAS-Agentic-Core

# 2. Install dependencies (requires Python 3.10+)
pip install -r requirements.txt

# 3. Configure environment variables (see .env.example)
cp .env.example .env

# 4. Run the code-switching evaluation suite
# Example command:
python -m evaluation.run --suite code-switching-v1 --output results/report.json
```

## Independence & Transparency

The North African AI Safety Lab (NAAS Lab) operates with academic and operational independence.
*   **Independent Publication:** We reserve the right to publish our methods, findings, and critical safety evaluations independently of any model providers or partners.
*   **Open Science:** De-identified methodologies and aggregated results are shared with the open-source community to advance global AI safety.

## Scope Boundaries

*   **Not Legal Advice:** This toolkit and its documentation do not constitute legal compliance advice (e.g., GDPR, local laws). Consult your organization's legal counsel.
*   **Not a Replacement for Human Oversight:** "Verify-then-Reply" reduces risk but does not eliminate it. Adult supervision is mandatory for youth-facing deployments as per [SAFEGUARDING.md](./SAFEGUARDING.md).

## Contact

For research inquiries, collaborations, or governance questions, please contact the repository owners via GitHub Issues or the email listed in our profile.
