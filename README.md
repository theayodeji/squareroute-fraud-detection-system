# Delivery Fraud Risk Engine

An event-driven risk engine for order-and-delivery platforms designed to detect courier and customer delivery fraud at the decision moment (payout, refund, in-flight ops) with explainable, deterministic rules.

## Comprehensive Documentation

The documentation has been broken down into detailed, step-by-step guides. Please read them in the following coherent order to understand the system fully:

1. [Overview & Architecture](docs/1_overview_and_architecture.md): Understand the core problem, the event-driven out-of-band philosophy, and the decoupled 4-Table data model.
2. [Data Formats & Schemas](docs/2_data_formats_and_schemas.md): Explore the exact JSON ingestion payloads, Pydantic APIs, and PostgreSQL/SQLAlchemy schemas.
3. [Rules & Formulas](docs/3_rules_and_formulas.md): Deep dive into the deterministic mechanisms, Haversine geospatial math, thresholds, and exact logic behind the 4 fraud rules.
4. [Expected Usage & Consumers](docs/4_expected_usage_and_consumers.md): Learn how the Payout Job, Refund System, and Ops Teams actually consume the normalized scores and rule evidence.
5. [Deployment & Simulation](docs/5_deployment_and_simulation.md): Step-by-step instructions for running the code locally (via Docker or Zero-Dependency mode) and executing the integration scenario simulation.

---

*This system was built with a bottom-up modular philosophy, separating the physical immutable facts (Events) from contextual state (Deliveries) and final business evaluation (Scores & Evidence).*
