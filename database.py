import os
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

# Lädt die Umgebungsvariablen aus der lokalen .env-Datei
load_dotenv()

class DatabaseRepository:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise RuntimeError("❌ [DATABASE] Kritischer Fehler: SUPABASE_URL oder SUPABASE_KEY fehlt in .env!")
        
        # Initialisierung des Supabase-Clients (Privilegierte service_role)
        self.client: Client = create_client(self.url, self.key)
        print("💾 [DATABASE] Cloud-Repository-Verbindung erfolgreich initialisiert.")

    def insert_scan_event(self, scan_data: dict) -> tuple[bool, str]:
        """
        Persistiert ein Scan-Event in der Cloud-Datenbank.
        Gibt ein Tuple zurück: (Erfolg: bool, Statusmeldung: str)
        """
        try:
            db_payload = {
                "unique_scan_id": scan_data.get("unique_scan_id"),
                "device_id": scan_data.get("device_id"),
                "barcode": scan_data.get("barcode"),
                "scan_type": scan_data.get("scan_type"),
                "scan_duration_sec": scan_data.get("scan_duration_sec"),
                "client_timestamp": scan_data.get("timestamp")
            }
            
            self.client.table("scan_events").insert(db_payload).execute()
            return True, "201_CREATED"

        except APIError as e:
            # PostgreSQL fängt das Duplikat über den UNIQUE-Constraint ab (Error Code 23505)
            if e.code == "23505" or "duplicate key" in str(e.message).lower():
                return True, "200_DUPLICATE_IGNORED"
            
            return False, f"DATABASE_ERROR: {e.message}"

    def get_recent_scans(self, limit: int = 100) -> list:
        """Holt die letzten X Scans geordnet nach Erstellungsdatum aus der Cloud."""
        try:
            response = self.client.table("scan_events")\
                           .select("*")\
                           .order("created_at", desc=True)\
                           .limit(limit)\
                           .execute()
            return response.data
        except APIError:
            return []

    def fetch_scans_for_batch_export(self, iso_timestamp: str) -> list:
        """Holt alle Scans, die jünger als der übergebene Zeitstempel sind."""
        try:
            response = self.client.table("scan_events")\
                           .select("barcode, scan_type, created_at")\
                           .gte("created_at", iso_timestamp)\
                           .execute()
            return response.data
        except APIError:
            return []
    def push_to_quarantine(self, raw_payload: dict, error_message: str) -> bool:
        """
        Schiebt einen korrupten oder nicht-heilbaren Datensatz 
        in die Quarantäne-Infrastruktur des Backends.
        """
        try:
            quarantine_payload = {
                "payload": raw_payload,
                "status": "pending",
                "error_type": error_message
            }
            self.client.table("data_quarantine").insert(quarantine_payload).execute()
            print(f" ⚠️ [QUARANTÄNE] Datensatz isoliert. Grund: {error_message}")
            return True
        except APIError as e:
            print(f" ❌ [QUARANTÄNE ERROR] Konnte Quarantäne-Eintrag nicht schreiben: {e.message}")
            return False