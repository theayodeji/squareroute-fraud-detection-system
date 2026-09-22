# 5. Deployment & Simulation

## Running the Architecture

The architecture allows flexibility between full-scale production deployments and instantaneous local development.

### Method A: Docker Compose (Production Stack)
Utilizes the official Docker compose file to spin up isolated containers.
* **Services**: FastAPI (API), Python Worker (Queue Consumer), PostgreSQL 16 (DB), Redis 7 (Broker/Cache).
* **Command**:
  ```bash
  docker-compose up --build
  ```

### Method B: Zero-Dependency Local Dev (Testing)
Ideal for CI/CD or running the simulation without installing Docker. The system automatically falls back to an `aiosqlite` in-memory database and an `AsyncMemoryBroker` for the queue.

* **Command**:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  pip install aiosqlite
  
  # Run the API
  uvicorn app.main:app --reload
  ```

---

## Running the Scenario Simulation

The repository includes a simulation script that acts as an automated integration test, generating physical events and executing them through the engine.

**To run:**
```bash
python -m scripts.run_simulation
```

### What it Tests:
1. **Legitimate Delivery**: Emits a target, logical pings over time, and a completion.
   * *Result*: Passes all rules. Score: `0 (LOW)`.
2. **GPS Teleportation**: Emits a ping, and then 5 seconds later emits a ping 20km away.
   * *Result*: `gps_jump_speed` FIRES. Score: `75 (HIGH)`.
3. **Ghost Delivery Loiter**: Approaches 150m from the door, stays there for 6 minutes, never gets closer, and marks complete.
   * *Result*: `geofence_loiter_completion` FIRES. Score: `70 (HIGH)`.
4. **False DNA Claim**: Drops off the order with an upstream-verified geotagged photo exactly at the door coordinates. Customer later files a claim.
   * *Result*: `dna_against_verified_pod` FIRES. Score: `85 (CRITICAL)`.
