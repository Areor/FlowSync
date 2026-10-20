# FlowSync: Resilient Event-Driven B2B Logistics Middleware

FlowSync is a highly available, offline-ready ecosystem designed for real-time tracking and synchronization of goods movements at logistics ramps. The system connects a mobile AR scanner tool directly to a reactive dispatch dashboard (Dispatch Hub) via a secured FastAPI gateway.

## 🛰️ Architecture & Resilience Highlights

The system was specifically engineered to autonomously mitigate network dropouts at coverage edges (e.g., inside large warehouses) and bypass restrictive client isolation policies:

*   **Native Hardware Triggering:** Zero dependency on heavy frontend JavaScript libraries; utilizes the native Google **`BarcodeDetector` API** directly at the browser-RAM layer for ultra-low latency scanning (<50ms).
*   **Offline-First Queue:** Integration of a transaction-secured **IndexedDB queue (FIFO)** within the mobile client ensures seamless local buffering during Wi-Fi blackouts.
*   **Inbound Shieldwall & Quarantine:** Built-in heuristic filtering within the FastAPI gateway screens for injection patterns, automatically routing malformed or blocked payloads into an in-memory quarantine buffer.
*   **MIME-Type & Tunnel Hardening:** Architectural design structured to circumvent Google Chrome *Strict MIME-Type Checking* (Nosniff) and asynchronous CORS blocks within highly restrictive enterprise networks.

## 🛠️ Tech Stack

*   **Backend:** Python 3.14, FastAPI (ASGI), Uvicorn, HTTPX/Httpcore
*   **Frontend:** Vanilla JS (ES6+), HTML5 Canvas (AR Bounding Box), CSS3 Grid/Flexbox
*   **Cloud & Storage:** Supabase (PostgreSQL), IndexedDB (Client-RAM)

## 🔄 End-to-End Data Flow (B2B Infrastructure)

```text
[ Motorola Terminal ] --( Native BarcodeDetector API )
         |
         | (Network Drop: IndexedDB FIFO-Queue / Local Buffer)
         v
[ ngrok Tunnel / WAN ] 
         |
         | (REST-POST / JSON Payload)
         v
[ FastAPI API Gateway ] --( Heuristic & SQL Injection Shieldwall )
         |
         +---> [ Success ] ---> ( Supabase Cloud DB ) ---> [ Dispatch Hub / Monitor ]
         |
         +---> [ Net Block ] -> ( In-Memory Quarantine ) -> [ Fail-Safe 202 Fallback ]
```

## 🔌 API Specification (REST Endpoints)

### `POST /api/v1/warehouse/scans`
Ingests mobile scans, validates the incoming JSON structure, and persists records safely.

*   **Payload (Request Format):**
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
*   **Response Codes:**
    *   `201 Created`: Scan successfully processed and persisted to the cloud database.
    *   `202 Accepted`: Cloud connection blocked by firewall; payload safely quarantined locally.
    *   `422 Unprocessable Entity`: Security violation triggered or malformed payload isolated.

### `GET /api/v1/warehouse/transactions`
Fetches the last 100 verified transaction records to populate the dispatcher dashboard.

## 🚀 Installation & Local Setup

### 1. Clone the Repository & Navigate
```bash
git clone https://github.com/Areor/FlowSync.git
cd FlowSync
```

### 2. Install Dependencies
```bash
pip install fastapi uvicorn supabase python-dotenv httpx pydantic
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and add your Supabase credentials:
```env
SUPABASE_URL="https://supabase.co"
SUPABASE_KEY="your-secret-supabase-api-key"
```

### 4. Run the Backend Server
```bash
python cloud_backend.py
```
The system will be accessible locally at `http://localhost:8000`.

### 5. Expose the Mobile Terminal
To test the web app on your physical mobile device, tunnel port `8000` via ngrok:
```bash
ngrok http 8000
```
Then open the generated `https://.../terminal` URL inside your mobile Chrome browser.

## 🤖 Development Methodology & AI Collaboration

This project was built using modern **AI-Pair-Programming methodologies**. 
*   **Architectural Design & Engineering:** Oliver Preuss (Core logic, debugging, network-hardening strategies, asymmetric hysteresis design, and local runtime verification).
*   **Code Generation Assistance:** Advanced AI synthesis models (leveraged to accelerate boilerplate delivery and optimize code sanitization pipelines).

*Demonstrating high-efficiency software orchestration and rapid prototyping in restricted network environments.*


## 📝 License & Copyright
Project developed as part of an advanced Software Engineering portfolio by Oliver Preuss, 2026. Open for demonstration and educational purposes.
