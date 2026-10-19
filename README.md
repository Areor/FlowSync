# FlowSync: Resiliente Event-Driven B2B-Logistik-Middleware

FlowSync ist ein hochverfügbares, offline-fähiges Ökosystem zur Echtzeit-Erfassung und Synchronisation von Warenbewegungen an Logistik-Rampen. Das System verbindet ein mobiles AR-Scannertool direkt mit einem reaktiven Leitstand-Dashboard (Dispatch Hub) über ein abgesichertes FastAPI-Gateway.

## 🛰️ Architektur- & Resilienz-Highlights

Das System wurde gezielt darauf ausgelegt, Netzwerkausfälle an Funkgrenzen (z. B. in Lagerhallen) und restriktive Client-Isolationen autonom abzufedern:

*   **Native Hardware-Zündung:** Verzicht auf schwere JS-Bibliotheken im Frontend; direkte Nutzung der Google **`BarcodeDetector` API** auf Chiptakt-Ebene für verzögerungsfreie Scans (<50ms).
*   **Offline-First-Queue:** Integration einer transaktionsgesicherten **IndexedDB-Warteschlange (FIFO)** im mobilen Client zur nahtlosen lokalen Pufferung bei Wi-Fi-Blackouts.
*   **Inbound-Schutzwall & Quarantäne:** Integrierte Heuristik-Prüfung im FastAPI-Gateway gegen Injections sowie automatische Umleitung blockierter oder unvollständiger Payloads in eine flüchtige InMemory-Quarantäne.
*   **MIME-Type & Tunnel-Härtung:** Architektur-Strukturierung zur Umgehung von Google Chrome *Strict MIME-Type Checking* (Nosniff) und asynchronen CORS-Sperren in restriktiven Netzwerken.

## 🛠️ Tech-Stack

*   **Backend:** Python 3.14, FastAPI (ASGI), Uvicorn, HTTPX/Httpcore
*   **Frontend:** Vanilla JS (ES6+), HTML5 Canvas (AR-Bounding-Box), CSS3 Grid/Flexbox
*   **Cloud & Storage:** Supabase (PostgreSQL), IndexedDB (Client-RAM)
## 🔄 Ende-zu-Ende Datenfluss (B2B-Infrastruktur)

```text
[ Motorola Terminal ] --( Native BarcodeDetector API )
         |
         | (Bei Netzverlust: IndexedDB FIFO-Queue / Lokaler Puffer)
         v
[ ngrok-Tunnel / WAN ] 
         |
         | (REST-POST / JSON-Payload)
         v
[ FastAPI API-Gateway ] --( Heuristik- & SQL-Injection-Schutzwall )
         |
         +---> [ Erfolgreich ] ---> ( Supabase Cloud DB ) ---> [ Dispatch Hub / PC-Monitor ]
         |
         +---> [ Netzwerk-Sperre ] -> ( InMemory-Quarantäne ) -> [ Fehlerfreier Fallback 202 ]
```

## 🔌 API-Spezifikation (REST-Endpunkte)

### `POST /api/v1/warehouse/scans`
Nimmt mobile Scans entgegen, validiert die JSON-Struktur und speichert sie transaktionssicher ab.

*   **Payload (Anfrage-Format):**
    ```json
    {
      "unique_scan_id": "MOBILE_1718251000_ABC123",
      "device_id": "MOTOROLA_RAMPE_A",
      "timestamp": 1718251000,
      "uuid": "ABC123XYZ",
      "barcode": "ORDER-4001A",
      "scan_duration_sec": 0.05,
      "scan_type": "WARENEINGANG"
    }
    ```
*   **Response-Codes:**
    *   `201 Created`: Scan erfolgreich verarbeitet und in der Cloud gespeichert.
    *   `202 Accepted`: Netzwerkblockade zur Cloud abgefangen; lokal in Quarantäne gesichert.
    *   `422 Unprocessable Entity`: Sicherheitsverletzung oder fehlerhafte Payload isoliert.

### `GET /api/v1/warehouse/transactions`
Liefert die letzten 100 verifizierten Transaktionen für das Disponenten-Dashboard aus.
## 🚀 Installation & Lokal ausführen

### 1. Repository klonen & Verzeichnis wechseln
```bash
git clone https://github.com[Dein-GitHub-Benutzername]/FlowSync.git
cd FlowSync
```

### 2. Abhängigkeiten installieren
```bash
pip install fastapi uvicorn supabase python-dotenv httpx pydantic
```

### 3. Umgebungsvariablen einrichten
Erstelle eine `.env`-Datei im Hauptverzeichnis und trage deine Supabase-Zugangsdaten ein:
```env
SUPABASE_URL="https://supabase.co"
SUPABASE_KEY="dein-geheimer-supabase-api-schlüssel"
```

### 4. Backend-Server starten
```bash
python cloud_backend.py
```
Das System läuft nun lokal unter `http://localhost:8000`.

### 5. Mobiles Terminal freischalten
Um die App auf dem Smartphone zu testen, tunnel den Port `8000` via ngrok:
```bash
ngrok http 8000
```
Rufe anschließend die generierte `https://.../terminal`-Adresse im mobilen Chrome-Browser auf.

## 📝 Lizenz & Urheberrecht
Projekt entwickelt im Rahmen des fortgeschrittenen Software-Engineering-Portfolios von Oliver [Dein Nachname], 2026. Frei verwendbar zu Demonstrations- und Bildungszwecken.
