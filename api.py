from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime

app = FastAPI(title="FinPulse Ingestion Gateway")

# In-memory log buffer
telemetry_logs = []

class TelemetryPayload(BaseModel):
    endpoint: str
    status_code: int
    latency_ms: int
    error_tag: str = "NONE"

@app.post("/api/v1/telemetry/ingest")
def ingest_event(payload: TelemetryPayload):
    event = payload.model_dump()
    event["timestamp"] = datetime.datetime.now().isoformat()
    event["correlation_id"] = f"TXN-{len(telemetry_logs) + 10001}"
    telemetry_logs.append(event)
    return {"status": "INGESTED", "correlation_id": event["correlation_id"]}

@app.get("/api/v1/telemetry/stream")
def get_stream():
    return telemetry_logs[-100:]
