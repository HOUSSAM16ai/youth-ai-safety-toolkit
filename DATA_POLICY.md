# Data Policy: Privacy-by-Design

This policy outlines the data governance framework for the NAAS-Agentic-Core project. We adhere to a "Privacy-by-Design" and "Privacy-by-Default" approach to protect all participants, specifically focusing on youth safety.

## 1. Data Collection Scope

We strictly limit data collection to the minimum necessary for safety evaluation and research integrity.

### Data We Collect
*   **Guardian Contact Information:** Email/phone for consent purposes (stored separately from session data).
*   **Participant Age Band:** Aggregated age ranges (e.g., "13-15", "16-18") rather than exact dates of birth.
*   **Pseudonymised Session IDs:** Unique, random identifiers linked to interaction logs to allow for analysis without revealing identity.
*   **Privacy-Preserving Telemetry:** System performance metrics, safety flag activations, and error rates.
*   **Optional Wellbeing Check-ins:** Aggregated, non-clinical self-reported wellbeing scores (if applicable to specific study protocols).

### Data We Do NOT Collect
*   **Full Date of Birth:** We do not store exact birth dates.
*   **National Identification Numbers:** No government IDs are collected or stored.
*   **Precise Geolocation:** No GPS or precise location data is recorded by default.
*   **Raw Chat Logs for Publication:** We do not publish raw, unredacted conversations.
*   **Direct Identifiers in Analysis:** Names and addresses are never stored with analysis datasets.

## 2. Storage & Security

*   **Role-Based Access Control (RBAC):** Access to raw data is restricted to authorized researchers with active safeguarding training.
*   **Encryption:** All sensitive data is encrypted in transit (TLS 1.2+) and at rest (AES-256).
*   **Audit Logs:** Access to sensitive data stores is logged and auditable.
*   **Separation of Duties:** Contact information (for consent) is stored in a separate, siloed system from research data (telemetry/chats).

## 3. Data Retention

We enforce strict retention schedules to minimize risk.

*   **Raw Telemetry & Logs:** Retained for **30 days** post-collection for immediate analysis and debugging.
*   **Anonymised/Aggregated Data:** Retained indefinitely for longitudinal research and publication.
*   **Incident Records:** Retained as required by the [SAFEGUARDING.md](./SAFEGUARDING.md) protocol (typically longer, pending institutional review) if a safety incident occurs.
*   **Deletion:** Upon expiration of the retention period, raw data is securely deleted/overwritten.

## 4. Publication & Sharing

*   **Aggregated Findings:** We publish statistical analysis, interception rates, and error patterns.
*   **Sanitised Test Cases:** We share constructed "red-teaming" prompts that do not contain user data.
*   **No Raw Youth Data:** We **never** publish raw transcripts of youth interactions.
*   **Incident Patterns:** We share anonymised descriptions of safety failure modes to help the community improve, without identifying individuals.

## 5. Compliance

This policy aligns with the principles of data minimization and purpose limitation (e.g., GDPR Art. 25). However, users deploying this toolkit must verify compliance with their specific local jurisdiction's data protection laws.
