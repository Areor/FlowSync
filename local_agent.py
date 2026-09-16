import os
import time
import json
import hashlib
import shutil
import uuid  
from datetime import datetime
import chardet
import requests  

class LocalAgent:
    def __init__(self, config_path="config.json", hash_store_path="processed_hashes.txt"):
        self.config_path = os.path.abspath(config_path)
        self.hash_store_path = os.path.abspath(hash_store_path)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.config = self.load_config()
        
        raw_watch_folder = self.config["watch_folder"]
        if raw_watch_folder.startswith("."):
            self.watch_folder = os.path.abspath(os.path.join(base_dir, raw_watch_folder))
        else:
            self.watch_folder = os.path.abspath(raw_watch_folder)
            
        self.archive_folder = os.path.join(self.watch_folder, "archive")
        self.api_url = self.config.get("api_endpoint", "http://localhost:8000/api/v1/warehouse/scans")
        
        # NEU: Konfiguration für den abendlichen Batch-Export (Standard: 18:00 Uhr)
        self.export_target_dir = os.path.abspath(os.path.join(base_dir, "./tms_outbound"))
        self.scheduled_export_time = self.config.get("export_time", "18:00")
        self.last_export_date = "" # Verhindert, dass der Export innerhalb derselben Minute mehrfach triggert

        os.makedirs(self.watch_folder, exist_ok=True)
        os.makedirs(self.archive_folder, exist_ok=True)
        os.makedirs(self.export_target_dir, exist_ok=True)

    def load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            default_config = {
                "watch_folder": "./watch_dir",
                "api_endpoint": "http://localhost:8000/api/v1/warehouse/scans", 
                "expected_columns": ["auftrag_id", "gewicht_kg", "status"],
                "column_types": {"auftrag_id": "str", "gewicht_kg": "float", "status": "str"},
                "export_time": "18:00" # NEU: Standardzeit im Config-File hinterlegt
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            return default_config
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        print("\n[CONFIG] config.json erfolgreich geheilt und aktualisiert.")

    def verify_file_stability(self, file_path: str) -> bool:
        try:
            initial_size = os.path.getsize(file_path)
            time.sleep(2.0)
            current_size = os.path.getsize(file_path)
            return initial_size == current_size and current_size > 0
        except OSError:
            return False

    def detect_encoding(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            return result["encoding"] if result["encoding"] else "utf-8"

    def calculate_sha256(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def is_duplicate(self, file_hash: str) -> bool:
        if not os.path.exists(self.hash_store_path):
            return False
        with open(self.hash_store_path, "r") as f:
            processed_hashes = f.read().splitlines()
        return file_hash in processed_hashes

    def log_hash(self, file_hash: str):
        with open(self.hash_store_path, "a") as f:
            f.write(file_hash + "\n")

    def parse_csv_header_and_rows(self, file_path: str, encoding: str) -> tuple:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if not lines:
            return [], []
        
        delimiter = ";" if ";" in lines[0] else ","
        header = [col.strip().replace('"', '') for col in lines[0].split(delimiter)]
        
        rows = []
        for line in lines[1:]:
            values = [val.strip().replace('"', '') for val in line.split(delimiter)]
            if len(values) == len(header):
                rows.append(dict(zip(header, values)))
        return header, rows

    def find_first_valid_value(self, rows: list, column_name: str) -> str:
        for row in rows:
            val = row.get(column_name, "").strip()
            if val != "" and val.lower() != "null":
                return val
        return None

    def determine_data_type(self, value: str) -> str:
        if not value:
            return "unknown"
        try:
            int(value)
            return "int"
        except ValueError:
            try:
                float(value.replace(",", "."))
                return "float"
            except ValueError:
                return "str"

    def execute_self_healing(self, incoming_header: list, rows: list) -> bool:
        expected_set = set(self.config["expected_columns"])
        incoming_set = set(incoming_header)
        
        missing_columns = expected_set - incoming_set
        new_columns = incoming_set - expected_set
        
        if not missing_columns and not new_columns:
            return True
            
        if len(missing_columns) == 1 and len(new_columns) == 1:
            old_col = list(missing_columns)[0]
            new_col = list(new_columns)[0]
            
            print(f"\n[WARNUNG] Spalte '{old_col}' fehlt. Neue Spalte '{new_col}' erkannt.")
            sample_value = self.find_first_valid_value(rows, new_col)
            detected_type = self.determine_data_type(sample_value)
            expected_type = self.config["column_types"].get(old_col, "str")
            
            if detected_type == expected_type or (expected_type == "float" and detected_type == "int"):
                idx = self.config["expected_columns"].index(old_col)
                self.config["expected_columns"][idx] = new_col
                self.config["column_types"][new_col] = self.config["column_types"].pop(old_col)
                self.save_config()
                return True
                
        return False

    def process_file(self, file_path: str):
        filename = os.path.basename(file_path)
        print(f"\n[FILE] Neue Datei erkannt: {filename}")
        if not self.verify_file_stability(file_path):
            return
            
        encoding = self.detect_encoding(file_path)
        file_hash = self.calculate_sha256(file_path)
        
        if self.is_duplicate(file_hash):
            print(f"[SKIP] Inhalt bereits bekannt.")
            self.archive_file(file_path)
            return
            
        header, rows = self.parse_csv_header_and_rows(file_path, encoding)
        
        if not self.execute_self_healing(header, rows):
            print(f"[STOP] Strukturfehler. Erwartet: {self.config['expected_columns']}, Erhalten: {header}")
            return
            
        success_count = 0
        agent_device_id = "LOCAL_AGENT_SERVER"
        id_column = self.config["expected_columns"][0]
        
        for row in rows:
            timestamp = int(time.time() * 1000)
            row_uuid = str(uuid.uuid4())
            composite_key = f"SC-{agent_device_id}-{timestamp}-{row_uuid}"
            
            payload = {
                "unique_scan_id": composite_key,
                "device_id": agent_device_id,
                "timestamp": timestamp,
                "uuid": row_uuid,
                "barcode": row.get(id_column, "UNKNOWN_ORDER"),
                "scan_duration_sec": 0.1 
            }
            
            try:
                response = requests.post(self.api_url, json=payload, timeout=5)
                if response.status_code in [200, 201]:
                    success_count += 1
            except requests.exceptions.RequestException as e:
                print(f"[API ERROR] Übertragung fehlgeschlagen: {e}")
                return 

        print(f"[API SUCCESS] {success_count} von {len(rows)} Datensätzen erfolgreich in die Cloud gestreamt.")
        self.log_hash(file_hash)
        self.archive_file(file_path)

    def archive_file(self, file_path: str):
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(self.archive_folder, f"{timestamp}_{filename}")
        try:
            shutil.move(file_path, dest_path)
            print(f"[ARCHIV] Datei verschoben nach: {dest_path}")
        except Exception as e:
            print(f"[ERROR] {e}")

    # ==========================================================================
    # 📥 NEU: DIE OUTBOUND BATCH-EXPORT ENGINE
    # ==========================================================================
    def download_daily_tms_export(self):
        """Holt die bereinigte CSV aus der Cloud und legt sie im TMS-Importordner ab."""
        # Generiert die korrekte Export-URL aus der Scans-API-URL
        export_url = self.api_url.replace("/scans", "/export-tms")
        
        try:
            print(f"\n[OUTBOUND] Getriggerter Datenabruf von der Cloud-API...")
            response = requests.get(export_url, timeout=10)
            
            if response.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_file_path = os.path.join(self.export_target_dir, f"TMS_RUECKSPIEL_{timestamp}.csv")
                
                with open(export_file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                    
                print(f" 💾 [OUTBOUND SUCCESS] Bereinigte CSV gesichert unter: {export_file_path}")
            else:
                print(f" ⚠️ [OUTBOUND WARN] Keine neuen Daten oder Serverfehler (Status: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f" ❌ [OUTBOUND ERROR] Download fehlgeschlagen: {e}")

    def run(self):
        print(f"\n=======================================================")
        print(f"🚀 FLOWSYNC LOGISTIK-AGENT AKTIV")
        print(f"📂 INBOUND ORDNER: {self.watch_folder}")
        print(f"📥 OUTBOUND ORDNER: {self.export_target_dir}")
        print(f"⏰ EXPORT-UHRZEIT: {self.scheduled_export_time} Uhr")
        print(f"🌐 ZIEL-API-SERVER: {self.api_url}")
        print(f"=======================================================\n")
        
        spinner = ['|', '/', '-', '\\']
        spinner_idx = 0
        
        try:
            while True:
                # 1. Inbound-Prüfung: Scannt den Ordner aktiv für 5 Sekunden
                for _ in range(10): 
                    current_time_str = datetime.now().strftime("%H:%M")
                    current_date_str = datetime.now().strftime("%Y-%m-%d")
                    
                    print(f"\r[{spinner[spinner_idx]}] Agent aktiv... Uhrzeit: {datetime.now().strftime('%H:%M:%S')} | Drücke STRG+C", end="", flush=True)
                    spinner_idx = (spinner_idx + 1) % len(spinner)
                    
                    # ⏰ NEU: Der Scheduler-Zeitschalter (Prüft im Sekundentakt auf Übereinstimmung)
                    if current_time_str == self.scheduled_export_time and self.last_export_date != current_date_str:
                        print(f"\n\n⏰ [SCHEDULER] Export-Uhrzeit ({self.scheduled_export_time}) erreicht!")
                        self.download_daily_tms_export()
                        self.last_export_date = current_date_str  # Verhindert Mehrfachaustragung in dieser Minute
                        
                    time.sleep(0.5)
                
                # 2. Datei-Verarbeitung falls eine neue CSV eingeworfen wird
                for item in os.listdir(self.watch_folder):
                    item_path = os.path.join(self.watch_folder, item)
                    if os.path.isfile(item_path) and item.lower().endswith('.csv'):
                        self.process_file(item_path)
                        
        except KeyboardInterrupt:
            print("\n\n[STOP] Local Agent wurde manuell beendet.")

if __name__ == "__main__":
    agent = LocalAgent()
    agent.run()
