# 3. Rules & Formulas

The core intelligence of the Risk Engine is entirely deterministic, meaning it relies on fixed mathematical checks rather than opaque probabilistic models. This allows operational teams to trust, audit, and explain the exact reason a delivery was blocked.

## Core Geometric Math: Haversine Formula
Spatial distance between two GPS coordinates is calculated using the Haversine formula to account for the Earth's curvature.

$$ a = \sin^2\left(\frac{\Delta\text{lat}}{2}\right) + \cos(\text{lat}_1) \cdot \cos(\text{lat}_2) \cdot \sin^2\left(\frac{\Delta\text{lng}}{2}\right) $$
$$ c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right) $$
$$ d = R \cdot c $$

*(Where $R = 6371000$ meters, Earth's radius)*

---

## Event-Triggered Rules

### Rule 1: `gps_jump_speed`
**Goal**: Detect GPS teleportation (mock-location apps) used by couriers to fake proximity to a restaurant or customer.
* **Trigger**: `location_ping`
* **Mechanism**: 
  1. Fetch the immediately preceding `location_ping` for the delivery.
  2. Calculate Haversine distance ($\Delta d$ in meters) between the two pings.
  3. Calculate elapsed time ($\Delta t$ in seconds).
  4. Compute implied speed: $v = (\Delta d / \Delta t) \times 3.6$ (to get km/h).
* **Threshold**: Fires if $v > \text{threshold\_kmh}$ (e.g., 120 km/h).
* **Evidence Payload**: `distance_meters`, `elapsed_seconds`, `speed_kmh`.

### Rule 2: `geofence_loiter_completion`
**Goal**: Detect "Ghost Deliveries". A courier drives near the drop-off zone, waits out the in-app unresponsiveness timer (e.g., 5 minutes), and marks the order complete *without ever getting out of the car or approaching the physical door*.
* **Trigger**: `delivery_completed`
* **Mechanism**:
  1. Retrieve `target_lat` and `target_lng` from the `deliveries` state projection.
  2. Fetch all `location_ping` events for the delivery.
  3. Calculate the distance of every ping to the target. Track the absolute `min_distance_to_door`.
  4. Track the first and last time a ping fell inside the `outer_radius_m` (e.g., 200m).
  5. Calculate `dwell_time_seconds` = $t_{last} - t_{first}$ inside the outer zone.
* **Threshold**: Fires if `min_distance_to_door` > `door_radius_m` (e.g., 30m) **AND** `dwell_time_seconds` >= `min_dwell_time_sec` (e.g., 300s).
* **Evidence Payload**: `min_distance_to_door_m`, `dwell_time_seconds`, `reason`.

### Rule 3: `dna_against_verified_pod`
**Goal**: Catch abusive customers seeking refunds by claiming "Did Not Arrive" against an order that has iron-clad physical proof.
* **Trigger**: `claim_filed` (with `claim_type: did_not_arrive`)
* **Mechanism**:
  1. Fetch the `delivery_completed` event.
  2. Extract the `proof_of_delivery` object from the JSONB payload.
  3. Verify `is_verified_by_upstream` is `true` (meaning upstream systems validated the image was a door/signature).
  4. Calculate the Haversine distance between the `pod_lat/lng` and the delivery `target_lat/lng`.
* **Threshold**: Fires if the POD is valid AND `pod_distance <= max_pod_distance_m` (e.g., 30m).
* **Evidence Payload**: `pod_type`, `pod_distance_to_target_m`, `contradiction=true`.

---

## Scheduled Rules

### Rule 4: `pair_dispute_velocity`
**Goal**: Catch collusion rings where a rider and customer pair up to repeatedly report failed deliveries and split the refunded capital. This signal is invisible on a single order but mathematically obvious over time.
* **Trigger**: Scheduled background job (or evaluated dynamically during the simulation).
* **Mechanism**:
  1. Aggregate the `deliveries` table grouping by `rider_id` and `consumer_id` over the last 30 days (`created_at >= cutoff_date`).
  2. Count `total_deliveries` and `disputed_deliveries`.
  3. Calculate `dispute_rate = disputed / total`.
* **Threshold**: Fires if `total_deliveries >= min_deliveries` (e.g., 3) AND `dispute_rate >= min_dispute_rate` (e.g., 0.50).
* **Evidence Payload**: `total_deliveries`, `dispute_rate`, `pair`.

### Rule 5 & 6: `rider_dispute_velocity` & `consumer_dispute_velocity`
**Goal**: Identify globally high-risk individual entities (riders who constantly lose food, or consumers who constantly claim non-arrival) independent of who they are paired with.
* **Trigger**: Scheduled background job.
* **Mechanism**:
  1. Aggregate the `deliveries` table for a specific `rider_id` (or `consumer_id`) over the rolling window (e.g., 30 days).
  2. Count `total_deliveries` and `disputed_deliveries`.
  3. Calculate `dispute_rate = disputed / total`.
* **Threshold**:
  * **Rider**: Fires if `total_deliveries >= 10` AND `dispute_rate >= 0.15` (15%).
  * **Consumer**: Fires if `total_deliveries >= 5` AND `dispute_rate >= 0.20` (20%).
* **Evidence Payload**: `entity_type`, `entity_id`, `total_deliveries`, `dispute_rate`.
