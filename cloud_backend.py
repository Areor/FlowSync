from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client
from postgrest.exceptions import APIError
from datetime import datetime, timedelta, UTC
import uvicorn

app = FastAPI(title="Logistik SaaS Cloud API")

# ==============================================================================
# 🔑 SUPABASE CONFIGURATION
# ==============================================================================
# TODO: Kopieren Sie diese Werte aus Ihren Supabase-Projekteinstellungen (Settings -> API)
SUPABASE_URL = "https://glkllutkmxroklwkbomw.supabase.co"
SUPABASE_KEY = "sb_publishable_tlDUgJV9ZUcQh61xTqzrFQ_9p8BaCBc"

# Initialisierung des offiziellen Supabase-Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================================================================
# 🔓 CORS-FREIGABE (Erlaubt dem Webbrowser den Zugriff aus dem Frontend)
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Erlaubt absolut jedem Client den Zugriff
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# ==============================================================================
# 📦 DATA MODELS (PYDANTIC)
# ==============================================================================
class ScanEvent(BaseModel):
    unique_scan_id: str
    device_id: str
    timestamp: int
    uuid: str
    barcode: str
    scan_duration_sec: float
    scan_type: str = "BELADUNG"  # Standardwert, passend zu Ihrem DDL-Schema

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
@app.post("/api/v1/warehouse/scans", status_code=status.HTTP_201_CREATED)
async def receive_scan(scan: ScanEvent, response: Response):
    """Nimmt Scans live entgegen und nutzt Supabase/PostgreSQL zur Deduplizierung."""
    print(f"\n[API RECV] Request von Gerät: {scan.device_id} | Typ: {scan.scan_type}")
    print(f" 🆔 Scan-ID: {scan.unique_scan_id} | 📦 Barcode: {scan.barcode}")

    try:
        # Vorbereitung der Datenstruktur für das relationale PostgreSQL-Insert
        db_payload = {
            "unique_scan_id": scan.unique_scan_id,
            "device_id": scan.device_id,
            "barcode": scan.barcode,
            "scan_type": scan.scan_type,
            "scan_duration_sec": scan.scan_duration_sec,
            "client_timestamp": scan.timestamp
        }

        # Live-Insert in die Cloud-Datenbank (Tabelle: scan_events)
        data = supabase.table("scan_events").insert(db_payload).execute()
        
        print(f" 🟢 [SUCCESS] Scan dauerhaft in Supabase gespeichert.")
        return {"status": "success", "message": "Scan successfully persisted in cloud database."}

    except APIError as e:
        # PostgreSQL fängt das Duplikat über den UNIQUE-Constraint ab (Error Code 23505 = Unique Violation)
        if e.code == "23505" or "duplicate key" in str(e.message).lower():
            print(f" 🛑 [IDEMPOTENZ-SCHUTZWALL] Duplikat blockiert: {scan.unique_scan_id}")
            
            # Wir ändern den HTTP-Statuscode auf 200 OK, damit die Client-App den Scan als "erledigt" löscht
            response.status_code = status.HTTP_200_OK
            return {"status": "success", "message": "Duplicate ignored safely. Data already preserved."}
        
        # Andere unerwartete Datenbankfehler fangen und ausgeben
        print(f" ❌ [DATABASE ERROR] {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e.message}")

@app.get("/api/v1/warehouse/transactions")
async def get_all_transactions():
    """Holt die letzten 100 Scans live aus Supabase ab."""
    try:
        response = supabase.table("scan_events").select("*").order("created_at", desc=True).limit(100).execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e.message}")

from fastapi.responses import PlainTextResponse
from datetime import datetime, timedelta

@app.get("/api/v1/warehouse/export-tms", response_class=PlainTextResponse)
async def export_tms_batch():
    """Generiert am Tagesende den konsolidierten CSV-Batch-Export für das Altsystem."""
    try:
        # Holt alle gesammelten Scans der letzten 24 Stunden aus Supabase
        one_day_ago = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        response = supabase.table("scan_events")\
                           .select("barcode, scan_type, created_at")\
                           .gte("created_at", one_day_ago)\
                           .execute()
        
        scans = response.data
        
        # CSV-Header definieren
        csv_content = "auftrag_id;status;verarbeitet_am\n"
        
        # Datensätze in das vom Altsystem erwartete CSV-Format konvertieren
        for scan in scans:
            barcode = scan.get("barcode", "UNKNOWN")
            status_value = scan.get("scan_type", "GELADEN")
            timestamp = scan.get("created_at", "")
            
            csv_content += f"{barcode};{status_value};{timestamp}\n"
            
        print(f" 📑 [BATCH EXPORT] {len(scans)} Datensätze für den TMS-Export strukturiert.")
        return csv_content

    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Database export error: {e.message}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
