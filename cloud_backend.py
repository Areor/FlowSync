from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware  # NEU: CORS-Schutzwall-Erweiterung
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="Logistik SaaS Cloud API")

# ==============================================================================
# 🔓 NEU: CORS-FREIGABE (Erlaubt dem Webbrowser den Zugriff aus dem Frontend)
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Erlaubt absolut jedem Client (auch lokalen HTML-Dateien) den Zugriff
    allow_credentials=True,
    allow_methods=["*"],  # Erlaubt POST, GET, OPTIONS etc.
    allow_headers=["*"],  # Erlaubt alle HTTP-Header
)

# einfache In-Memory-Datenbank
TRANSACTION_DATABASE = []
PROCESSED_SCAN_IDS = set()  # Idempotenz

class ScanEvent(BaseModel):
    unique_scan_id: str
    device_id: str
    timestamp: int
    uuid: str
    barcode: str
    scan_duration_sec: float

@app.post("/api/v1/warehouse/scans", status_code=status.HTTP_201_CREATED)
async def receive_scan(scan: ScanEvent):
    """Nimmt Scans entgegen und blockiert über Idempotenz Duplikate."""
    print(f"\n[API RECV] Eingehender Request von Gerät: {scan.device_id}")
    print(f" 🆔 Scan-ID: {scan.unique_scan_id}")
    print(f" 📦 Barcode: {scan.barcode} | Dauer: {scan.scan_duration_sec}s")

    if scan.unique_scan_id in PROCESSED_SCAN_IDS:
        print(f" 🛑 [IDEMPOTENZ-ALARM] Scan {scan.unique_scan_id} ist ein Duplikat!")
        return {"status": "success", "message": "Duplicate ignored safely. Data already preserved."}

    TRANSACTION_DATABASE.append(scan.model_dump())
    PROCESSED_SCAN_IDS.add(scan.unique_scan_id)

    print(f" 🟢 [SUCCESS] Scan erfolgreich in die Datenbank eingetragen. Datensätze gesamt: {len(TRANSACTION_DATABASE)}")
    return {"status": "success", "message": "Scan successfully processed and stored."}

@app.get("/api/v1/warehouse/transactions")
async def get_all_transactions():
    return TRANSACTION_DATABASE

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
