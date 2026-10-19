import os  # 🔐 SYSTEM-SCHUTZ: Import für das Auslesen der .env-Variablen
import uvicorn
from fastapi import FastAPI, HTTPException, Response, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, UTC
# 🚀 NEU: FileResponse für die native, unverzerrte Binär-Auslieferung hinzugefügt
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

# 🔐 Import des cloud-agnostischen Repository-Patterns
from database import DatabaseRepository

app = FastAPI(
    title="FlowSync Enterprise API",
    description="Gehärteter REST-Sicherheitslayer für die logistische Middleware",
    version="1.3.0"
)

from fastapi.staticfiles import StaticFiles

# ==============================================================================
# 🔐 OFFLINE-FIRST ASSET-MOUNTING: Zwingt Windows zum korrekten MIME-Type-Streaming
# ==============================================================================
# Mountet das gesamte Hauptverzeichnis als statischen Speicher. Dadurch wird die 
# zxing.min.js mit garantiertem JavaScript-Sicherheits-Header ans Handy übertragen.
app.mount("/static", StaticFiles(directory="."), name="static")

db = DatabaseRepository()

# ==============================================================================
# 🔓 CORS-FREIGABE (Middleware-Array für entkoppelte Web-Clients)
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# ==============================================================================
# 📦 GESTEUERTE INPUT-VALIDIERUNG (Pydantic-Absicherung gegen SQL-Injections)
# ==============================================================================
class ScanEvent(BaseModel):
    unique_scan_id: str = Field(..., min_length=5, max_length=150)
    device_id: str = Field(..., min_length=3, max_length=100)
    timestamp: int
    uuid: str
    barcode: str = Field(..., min_length=1, max_length=100)
    scan_duration_sec: float = Field(..., ge=0.0)
    scan_type: str = Field(..., max_length=50)
    order_id: Optional[str] = None # Optionales Feld für die relationale Verknüpfung im ERD

# ==============================================================================
# 🌐 API ENDPOINTS (Inbound-Validierung & Quarantäne-Routing)
# ==============================================================================
@app.post("/api/v1/warehouse/scans")
async def receive_scan(scan: ScanEvent, response: Response):
    print(f"\n[API RECV] Validierungs-Check für Gerät: {scan.device_id}")
    payload_dict = scan.model_dump()
    
    # Inbound-Schutzwall: Heuristik-Prüfung gegen SQL-Injections
    blacklist = ["UNION", "SELECT", "DROP", "--", "OR 1=1"]
    if any(pattern in scan.barcode.upper() for pattern in blacklist):
        db.push_to_quarantine(payload_dict, "SECURITY_VIOLATION: SQL Patterns detected.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Eingabedaten verletzen die Sicherheitsrichtlinien."
        )

    try:
        # 🚀 OFFLINE-FALLBACK-PROTECTION: Fängt Netzwerk-Abstürze im Schul-WLAN ab
        success, db_status = db.insert_scan_event(payload_dict)
    except Exception as e:
        print(f" ⚠️ [NETZWERK BLOCK] Cloud blockiert durch Firewall: {str(e)}")
        # Wenn das Schul-WLAN blockiert, retten wir die Daten lokal in die Quarantäne
        db.push_to_quarantine(payload_dict, f"OFFLINE_SCHUL_WLAN_BLOCK: {str(e)}")
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "offline_buffered", "message": "Scan lokal gesichert. Cloud-Verbindung blockiert."}
    
    if not success:
        db.push_to_quarantine(payload_dict, f"TRANSAKTIONS_FEHLER: {db_status}")
        raise HTTPException(status_code=500, detail="Transaktions-Fehler.")
        
    if db_status == "200_DUPLICATE_IGNORED":
        response.status_code = status.HTTP_200_OK
        return {"status": "success", "message": "Duplicate bypassed safely."}
        
    print(f" 🟢 [SUCCESS] Scan-Event permanent in Cloud gespeichert.")
    response.status_code = status.HTTP_201_CREATED
    return {"status": "success", "message": "Scan persisted."}
        
    print(f" 🟢 [SUCCESS] Scan-Event validiert und permanent gespeichert.")
    response.status_code = status.HTTP_201_CREATED
    return {"status": "success", "message": "Scan successfully validated and persisted."}

@app.get("/api/v1/warehouse/transactions")
async def get_all_transactions():
    """Holt Scans aus der Cloud oder greift bei Firewall-Sperren auf ein lokales Backup zurück."""
    try:
        # Versucht regulär, die echten Live-Daten aus Supabase abzufragen
        return db.get_recent_scans(limit=100)
    except Exception as e:
        print(f" ⚠️ [HUB TRANSACTIONS BLOCK] Cloud nicht erreichbar wegen Firewall: {str(e)}")
        
        # 🚀 FALLBACK: Holt stattdessen die lokal zwischengespeicherten Quarantäne-Scans
        if hasattr(db, 'get_quarantine_scans'):
            return db.get_quarantine_scans()
            
        # Absicherung: Gibt ein leeres Array zurück, damit das Hub sauber rendert und nicht abstürzt
        return []

@app.get("/api/v1/warehouse/export-tms", response_class=PlainTextResponse)
async def export_tms_batch():
    try:
        one_day_ago = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        scans = db.fetch_scans_for_batch_export(one_day_ago)
        
        csv_content = "auftrag_id;status;verarbeitet_am\n"
        for scan in scans:
            barcode = scan.get("barcode", "UNKNOWN")
            status_value = scan.get("scan_type", "GELADEN")
            timestamp = scan.get("created_at", "")
            csv_content += f"{barcode};{status_value};{timestamp}\n"
            
        print(f" 📑 [BATCH EXPORT] {len(scans)} Datensätze strukturiert.")
        return csv_content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export layer crash: {str(e)}")

from fastapi.responses import HTMLResponse, PlainTextResponse # 🚀 Oben bei den Imports anpassen

# ... Ihr bestehender Code bleibt völlig unverändert ...

# ==============================================================================
# 🌐 STANDARD APPLICATON ROUTING: Frontend-Auslieferung
# ==============================================================================
@app.get("/terminal", response_class=HTMLResponse)
async def get_mobile_terminal():
    """Liefert die Scanner-App als schlanke, blitzschnelle HTML-Seite aus."""
    try:
        with open("scanner_app.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail="scanner_app.html nicht im Hauptordner gefunden!"
        )

@app.get("/hub", response_class=HTMLResponse)
async def get_dispatch_hub():
    """Liefert das sichere Disponenten-Dashboard (Hub) im Leitstand aus."""
    try:
        with open("hub_dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="hub_dashboard.html nicht gefunden!")


@app.get("/hub", response_class=HTMLResponse)
async def get_dispatch_hub():
    """Liefert das sichere Disponenten-Dashboard (Hub) im Leitstand aus."""
    try:
        with open("hub_dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail="hub_dashboard.html nicht im Hauptordner gefunden!"
        )

@app.get("/api/v1/hub/config")
async def get_hub_config():
    """Gibt die Supabase-Konfiguration sicher aus den lokalen Umgebungsvariablen an das Dashboard weiter."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") # Hier wird der Public Anon Key ausgelesen
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Supabase-Konfiguration in der .env-Datei unvollständig!")
        
    return {
        "supabase_url": supabase_url,
        "supabase_key": supabase_key
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
