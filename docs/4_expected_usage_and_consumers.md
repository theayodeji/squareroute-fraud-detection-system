# 4. Expected Usage & Consumers

The Delivery Fraud Risk Engine does not *enforce* decisions; it is an intelligence layer that provides actionable recommendations to downstream systems. The score is a **decision input**, not a verdict.

## Score Normalization

Scores are generated on a 0-100 scale and bucketed into 4 actionable bands:
* **Low (0–29)**: Proceed normally.
* **Elevated (30–59)**: Log, monitor, increase sampling.
* **High (60–84)**: Flag for review, hold payout, deny refund.
* **Critical (85–100)**: Block, auto-investigate, escalate.

## Core Consumers

### 1. The Payout Job
* **When**: Executes right before a rider is paid for a completed delivery.
* **Action**: Hits `GET /deliveries/{id}`.
* **Logic**: If the API returns `HIGH` or `CRITICAL` (e.g., due to a Ghost Delivery or GPS Teleportation flag), the payout job *holds the funds* and drops the delivery into a manual review queue.

### 2. The Refund Job
* **When**: Executes when a customer attempts to get their money back via a "Did Not Arrive" (DNA) flow in the app.
* **Action**: Hits `GET /deliveries/{id}/evidence`.
* **Logic**: The Risk Engine has already evaluated the `claim_filed` event. If the API returns `CRITICAL` due to `dna_against_verified_pod` firing, the refund job auto-denies the refund in the UI, presenting the customer with the verified photo as proof.

### 3. Ops Desk / In-Flight Monitoring
* **When**: Real-time tracking of active orders.
* **Action**: Consumes streaming updates or actively queries `GET /riders/{id}/risk`.
* **Logic**: If a courier triggers `gps_jump_speed` mid-delivery, the score jumps to `HIGH`. The Ops Desk can trigger an automated warning SMS to the rider or re-assign the order if teleportation is extreme.

### 4. Fraud Investigation / Finance
* **When**: Nightly or weekly review.
* **Action**: Reads raw `scores` and `rule_executions` from the Postgres database.
* **Logic**: Analysts review collusion alerts (`pair_dispute_velocity`), and Finance tracks the total monetary value saved by denied abusive refunds. Engineers use the `rule_executions` evidence payloads as highly-labeled training data to train future Machine Learning models.
