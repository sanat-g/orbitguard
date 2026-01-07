# OrbitGuard

**OrbitGuard** is a planetary defense alerting system that evaluates known Near-Earth Objects (NEOs) using NASA/JPL close-approach data.  
It is designed as a **backend engineering project**, focusing on **job processing, data ingestion, computation, and explainable system outputs** — with a simplified physics model that can be extended for larger-scale analysis.

## What OrbitGuard Does

OrbitGuard answers a single question:

**“Given what we already know, which objects pass close to Earth within a specific time window?”**

It:
- Ingests real NASA/JPL close-approach (CAD) datasets
- Queues scan requests as persistent jobs
- Executes scans asynchronously via a background worker
- Flags close approaches within a configurable distance threshold
- Produces risk outputs with explanation 

OrbitGuard **does not discover new objects** and **does not ingest telescope data**.

## Core Architecture

OrbitGuard follows a **job-based scanning model** similar to production batch-processing systems.

### 1. Data Ingestion
- Pulls close-approach data from the **NASA/JPL CAD API**
- Stores raw JSON and CSV for traceability
- Parses and normalizes data into a SQLite database

### 2. Scan Jobs
A scan job represents a request like:

“Scan all known objects between time T₁ and T₂ and flag anything within X km of Earth.”

Each job stores:
- Time window
- Distance threshold
- Status lifecycle (PENDING → RUNNING → SUCCEEDED / FAILED)
- Retry attempts and error state

Creating a job **does not block the API**.

### 3. Background Worker
A separate worker does the following:
- Claims pending scan jobs
- Evaluates all relevant close-approach events
- Computes risk scores
- Creates scan results
- Marks jobs complete or retryable on failure

This isolates long-running computation from HTTP requests.

### 4. Risk Events (Outputs)
Each scan may produce zero or more **Risk Events**, containing:
- Object identifier
- Time of closest approach
- Minimum distance to Earth
- Risk score
- Structured explanation payload

## Physics Model (MVP Scope)

- Uses **NASA/JPL close-approach data directly**
- Earth treated as origin
- No orbit propagation or n-body simulation
- Focused on correctness, determinism, and explainability

The physics layer is intentionally simplified to keep the project **software-engineering-centric**.

## Tech Stack

**Backend**
- Python 3
- FastAPI
- SQLAlchemy ORM
- SQLite

**Data**
- NASA/JPL Close-Approach Data (CAD API)
- CSV + JSON ingestion pipeline

**Frontend (MVP)**
- Static HTML/CSS/JS UI for interacting with the API

## Running OrbitGuard Locally

### 1. Create virtual environment & install dependencies, then run the following:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m orbitguard.db.init_db
python -m orbitguard.ingest.download_cad
python -m orbitguard.ingest.ingest_cad_csv
uvicorn orbitguard.api.main:app --reload

In a seperate terminal, launch the ui by running:
cd ui
python -m http.server 5500

Submit a job request, then in a new terminal, run:
python -m orbitguard.worker.run


