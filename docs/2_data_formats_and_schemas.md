# 2. Data Formats & Schemas

This section details the strict schemas used across the API boundary and the database layer. 

## Ingestion API Schema (`POST /events`)

All events stream through a unified ingestion endpoint. The body validates against the `EventCreate` Pydantic model.

```json
{
  "delivery_id": "string (UUID or external reference)",
  "rider_id": "string (UUID)",
  "event_type": "delivery_created | location_ping | delivery_completed | claim_filed",
  "lat": 40.7128,          // Optional for certain events
  "lng": -74.0060,         // Optional
  "delivery_status": "in_flight",
  "occurred_at": "2024-01-01T12:00:00Z", // ISO 8601 Timestamp
  "source": "rider_app",
  "payload": {
      // Dynamic JSON payload specific to the event_type
  }
}
```

### Specific Payload Structures

The `payload` block is unstructured JSONB, but the Rules Engine expects specific keys based on the `event_type`.

**1. `delivery_created`**
Hydrates the physical space for the delivery.
```json
"payload": {
    "consumer_id": "cust_883",
    "target_lat": 40.7128,
    "target_lng": -74.0060,
    "geofence_radius_m": 30.0
}
```

**2. `delivery_completed`**
Passes upstream Proof of Delivery (POD) artifacts.
```json
"payload": {
    "proof_of_delivery": {
        "pod_type": "photo",
        "is_verified_by_upstream": true,
        "pod_lat": 40.71282,
        "pod_lng": -74.00601
    }
}
```

**3. `claim_filed`**
Carries dispute details from the customer app.
```json
"payload": {
    "claim_type": "did_not_arrive",
    "reason_text": "I checked outside and there was no bag."
}
```

## Relational Database Schema

### 1. `events` (SQLAlchemy)
* `id`: UUID (Primary Key)
* `delivery_id`: String (Index)
* `rider_id`: String (Index)
* `event_type`: String (Index)
* `lat` / `lng`: Float
* `occurred_at`: DateTime (TZ Aware)
* `payload`: JSONB

### 2. `deliveries` (SQLAlchemy)
* `id`: String (Primary Key)
* `consumer_id` / `rider_id`: String (Indexes)
* `status`: String
* `target_lat` / `target_lng`: Float
* `geofence_radius_m`: Float

### 3. `scores` & `rule_executions`
* `scores.entity_type`: `delivery` | `rider` | `pair`
* `scores.entity_id`: e.g. `del_123`
* `scores.score`: Integer 0-100
* `scores.band`: `LOW` | `ELEVATED` | `HIGH` | `CRITICAL`
* `rule_executions.fired`: Boolean
* `rule_executions.evidence`: JSONB (Contains execution variables)
