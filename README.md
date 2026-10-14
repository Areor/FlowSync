# FlowSync — Commercial AR Warehouse Terminal & Real-Time Logistics Hub

A fault-tolerant, low-maintenance B2B logistics middleware bridging legacy ERP file dumps (CSV), modern mobile AR execution terminals (PWA), and live administrative monitoring dashboards. Features an autonomous self-healing parser, a database-backed idempotency shield, and a secure cloud-decoupled real-time telemetry architecture.

🚀 FlowSync — Fault-Tolerant Logistics SaaS Middleware

## ⚖️ License & Portfolio Notice
This project is currently published for portfolio and application purposes only. All rights reserved. Commercial use, reproduction, or distribution is strictly prohibited.

An event-driven, low-maintenance data-synchronization engine designed for medium-sized logistics operations. This enterprise-grade prototype bridges the gap between legacy ERP file dumps (CSV) and modern web execution terminals without requiring expensive direct database access or system-wide software overhauls.

## 🏗️ Architectural Core Pillars & Edge-Case Solutions
The system architecture is strictly split into decoupled, stateless layers engineered to withstand volatile real-world warehouse environments:

### 1. Intelligent Local Agent (`local_agent.py`)
A lightweight background worker monitoring local ERP export directories.
*   **File Stability Validation (Debounce Matrix):** Traps the classic file-locking issue. When an ERP takes seconds to write a massive CSV, the agent samples byte-size metrics over a 2-second delay. Processing is safely blocked until file-size volatility hits zero.
*   **Autonomous Self-Healing Parser:** Employs a deterministic 1:1 set-difference algorithm to catch schema mutations on the fly. If an admin renames a column at runtime, the engine heals its internal `config.json` without executing a fatal runtime crash.
*   **Fuzzy-Matching & Levenshtein Distance:** Leverages mathematical string-distance heuristics to autonomously map slightly mutated column headers (e.g., typos or minor export shifts like `auftrags_id`) without halting execution.
*   **Automated Outbound Scheduler:** Features an integrated background clock that automatically triggers at a user-defined time (e.g., 18:00) to fetch cleaned batch reports from the cloud and inject them back into the legacy ERP directory.

### 2. Idempotent SaaS Backend API (`cloud_backend.py` & `database.py`)
A rapid, asynchronous REST application layer powered by FastAPI and backed by Supabase (PostgreSQL).
*   **Database-Level Idempotency Wall:** Leverages a strict relational unique-constraint index (`unique_scan_id`). Handheld terminals retrying identical data packets due to Wi-Fi drops trigger an automatic `APIError (23505)` bypass, returning a clean `200 OK` to clear client queues while preserving database integrity.
*   **Zero-Leak Credential Injection:** Implements a protected API gateway route (`/api/v1/hub/config`) that injects Supabase environment credentials directly from secure local `.env` storage into browser memory at runtime, completely preventing secret leakage in public repositories.
*   **Unified HTML Application Server:** Features native response routing endpoints for `/terminal` and `/hub` to host and serve both production web clients natively from a single, lightweight server instance.
*   **Timezone-Aware Outbound Routing:** Implements strict, modern UTC datetime filters to compile and stream the last 24 hours of accumulated warehouse data into a consolidated CSV report for the outbound pipeline.
*   **Cross-Origin Security (CORS Engine):** Fully configured middleware array permitting asynchronous decoupled web clients to pipe data seamlessly across different network origins.

### 3. Offline-First AR Terminal (`scanner_app.html`)
A zero-install Progressive Web App interface optimizing direct floor-to-cloud logistics operations.
*   **Mobile AR MatrixGate Engine:** Powered by an integrated, lightweight `zxing` Multi-Format reader optimized for mobile Chrome and Android browsers to decode 1D/2D barcodes directly via hardware streams.
*   **Controlled Frame-Throttling (Thermal Shield):** Forces precise 300ms scanning analysis intervals instead of a raw 30fps stream. This prevents smartphone thermal throttling, drastically saves battery life, and reduces mobile CPU load by over 80%.
*   **Advanced Lens Binding:** Locks camera hardware constraints natively to the high-focus rear environment lenses with automatic autofocus to guarantee industrial scannability on the warehouse floor.
*   **Persistent Storage Guarantee:** Automatically requests and enforces native IndexedDB storage protection (`navigator.storage.persist()`), securing data with a legal OS-level deletion shield against low-memory garbage collection.
*   **Asynchronous FIFO Queue Jitter:** Network drops seamlessly transition the client into local-only caching mode. Once telemetry returns, the system pushes records chronologically (First-In-First-Out) with a randomized backoff jitter (1s - 3s) to prevent local network congestion.

### 4. Real-Time Dispatch Hub (`hub_dashboard.html`)
A live monitoring command center for warehouse dispatchers and management.
*   **Reactive WebSocket Stream:** Establishes a permanent, native Supabase WebSocket connection directly to the remote PostgreSQL `scan_events` table. New barcode arrivals pop up instantly on dispatch screens without page reloads.
*   **Fault-Tolerant JSON Parsing:** Implements dual-path key resolution (supporting both underscore and camelCase formatting) to ensure complete data-parsing compatibility across different browser runtimes like Firefox and Chrome.
*   **Performance-Optimized Rendering:** Restricts the active UI view to the last 10 incoming data rows using lightweight DOM mutation arrays to guarantee maximum browser rendering efficiency under high-volume stress.

## 🛠️ Technology Vector
*   **Backend Environment:** Python 3 (FastAPI, Uvicorn, Requests, Chardet, python-dotenv)
*   **Cloud Infrastructure:** Supabase & PostgreSQL (Ecosystem WebSockets & RLS)
*   **Frontend Web Shell:** Reactive Async/Await JavaScript, HTML5 Core (Canvas Layers), CSS3 Grid Architecture
*   **Mobile Decoder Framework:** ZXing (Zebra Crossing) Multi-Format Engine
*   **Data Transit Schema:** JSON API Payloads & Delimiter-Agnostic CSV Documents

## 🧪 Verified Simulation Benchmarks
This repository demonstrates complete stability under the following verified stress scenarios:
*   **Total Cloud Blackout:** Dropping the FastAPI process leaves local CSV data resting safely inside the agent watch folder with 0% asset dissipation. Processing catches up autonomously the second the cloud re-awakens.
*   **Wi-Fi Blind Spot Buffering & Browser Crash Resilience:** Simulating complete network severance flips the browser client into explicit offline execution mode, seamlessly queuing barcode payloads. Even a sudden application force-quit preserves the queue locally until telemetry is restored.
*   **Corrupt Zero-Byte Exports:** Bypasses empty structural artifacts generated by crashing legacy ERP systems without throwing unhandled internal faults.

## 🚀 Local Quickstart Guide

### 1. Provision Environment
Install all required architectural dependencies via your terminal:
```bash
python -m pip install fastapi uvicorn requests chardet python-dotenv
```

### 2. Execution Pipeline Order
1.  **Boot the Cloud Server:** 
    ```bash
    python cloud_backend.py
    ```
2.  **Expose the Secure HTTPS Tunnel (Optional for Mobile Testing):**
    ```bash
    ngrok http 8000
    ```
3.  **Awaken the Local Agent Daemon:** 
    ```bash
    python local_agent.py
    ```
4.  **Launch Frontends via Browser:**
    *   For Mobile AR Terminal: Navigate to `http://localhost:8000/terminal` (or your secure ngrok URL).
    *   For Real-Time Dispatch Hub: Navigate to `http://localhost:8000/hub`.

Drop sample `.csv` files into the auto-generated `watch_dir` workspace to witness the entire automated real-time data streaming pipeline in action!

