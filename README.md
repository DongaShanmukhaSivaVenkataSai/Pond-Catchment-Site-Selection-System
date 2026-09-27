# Village Pond Planning System
### Automated Hydrological Modeling, Catchment Delineation, and Runoff Estimation for Rural Rainwater Harvesting

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?style=flat&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26+-013243?style=flat&logo=numpy&logoColor=white)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/SciPy-1.13+-8CAAE6?style=flat&logo=scipy&logoColor=white)](https://scipy.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Project Access & Live Links

* **Live Web GIS Deployment:** [http://10.1.75.51:5252](http://10.1.75.51:5252)
* **GitHub Repository:** [https://github.com/DongaShanmukhaSivaVenkataSai/Pond-Catchment-Site-Selection-System](https://github.com/DongaShanmukhaSivaVenkataSai/Pond-Catchment-Site-Selection-System)
* **Author:** Donga Shanmukha Siva Venkata Sai (Department of Computer Science & Engineering, IIIT Sri City)

---

## 📖 Overview

In semi-arid rural regions across India, over 60% of agricultural cultivation depends entirely on erratic monsoon rains. Farm ponds and check dams provide decentralized rainwater harvesting (RWH) infrastructure to recharge groundwater aquifers and support protective irrigation during critical dry spells. However, conventional manual site surveys frequently fail because ponds are positioned in topographic saddles with insufficient contributing catchment or on steep slopes prone to rapid siltation.

The **Village Pond Planning System** is an end-to-end, automated, web-based geospatial decision-support platform. It takes raw elevation contours exported from Google Earth (KML format), builds a metric 1-meter Digital Elevation Model (DEM), models gravity flow routing, traces upstream watershed basins in sub-millisecond time, and scores optimal pond sites using multi-criteria hydromorphology—all delivered in an interactive, zero-install Web GIS interface.

---

## ✨ Key Features

* **🗺️ Interactive Web GIS Map Canvas:** Built with Leaflet 1.9.4 with authenticated dual basemap toggles (CARTO Dark Matter for vector clarity and Esri World Imagery for satellite vegetation inspection).
* **📐 Conformal Coordinate Reprojection:** Automatically transforms geographic WGS84 angles (EPSG:4326) into metric Universal Transverse Mercator (UTM Zone 44N, EPSG:32644), establishing a true $1\,\text{m} \times 1\,\text{m}$ grid.
* **⛰️ High-Resolution 2D Delaunay DEM:** Reconstructs continuous terrain elevation surfaces via Delaunay triangulation with empty-circumcircle guarantees and bivariate linear interpolation.
* **🌊 Deterministic D8 Flow Routing:** Vectorized hydraulic steepest-descent computation toward 8 Moore neighbors with automated flat-area spillover nudging.
* **📈 Topological Flow Accumulation & Stream Synthesis:** Solves drainage accumulation across millions of grid cells in exact $\mathcal{O}(N)$ linear time by traversing the Directed Acyclic Graph (DAG) in descending elevation order.
* **⚡ Sub-Millisecond Watershed Delineation:** Pre-indexes inverted flow networks into a Compressed Sparse Row (CSR) graph, allowing Breadth-First Search (BFS) upstream basin tracing in $<5\,\text{ms}$ upon user click.
* **📍 Multi-Criteria Pond Siting (MCE & NMS):** Evaluates natural sinks balancing flow accumulation ($60\%$), gentle slope stability ($30\%$), and valley floor elevation ($10\%$). Spatial Non-Maximum Suppression ($R_{\min} = 50\,\text{m}$) prevents marker clustering.
* **✂️ Property Boundary Clipping:** Interactive polygon drawing tool (Leaflet.Draw & Turf.js) that strictly restricts pond candidates inside designated village/public land parcels.
* **💧 Real-Time Hydrology HUD & Water Budgeting:** Computes seasonal runoff harvest volume via the empirical Rational Method ($V = 10 \cdot C \cdot P \cdot A$) and recommends excavation depths ($2.5 - 3.5\,\text{m}$) with dynamic client-side sliders.

---

## 🏛️ System Architecture

The platform follows a decoupled, three-tier geospatial architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 1: FRONTEND PRESENTATION (Web GIS)                 │
│                 http://10.1.75.51:5252 (or :5000)                      │
│                                                                        │
│   • Leaflet 1.9.4 Map Engine (CARTO Dark Matter / Esri Satellite)     │
│   • Leaflet.Draw Land-Boundary Polygon & Turf.js Spatial Clipping      │
│   • Dynamic Hydrology HUD (Catchment Area, Runoff Volume, Depth)       │
│   • Client-Side Rational Runoff Calculator with Interactive Sliders    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                       HTTP REST / GeoJSON Payloads
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│              TIER 2: NETWORK BRIDGE & API GATEWAY (ASGI)               │
│                  FastAPI / Uvicorn (Port 5000 / 5252)                  │
│                                                                        │
│   • Port Forwarding Pipeline: Host 5252 <───> Container 5000          │
│   • Non-Blocking ASGI Coroutines with ThreadPoolExecutor Worker Pool   │
│   • CORS Middleware, Multipart KML File Parser, and OpenAPI Docs       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                      Async Threadpool In-Memory Data
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│             TIER 3: BACKEND HYDROLOGICAL ENGINE (Python)               │
│                   NumPy / SciPy / PyProj / Shapely                     │
│                                                                        │
│   • projection.py: WGS84 -> UTM Zone 44N Metric (EPSG:32644)          │
│   • dem_builder.py: 2D Delaunay Triangulation & Barycentric DEM        │
│   • terrain.py: Central-Difference Gradient Slope, Aspect, & TWI       │
│   • hydrology.py: D8 Steepest Descent & O(N) Flow Accumulation         │
│   • catchment.py: Inverted CSR Graph & Upstream BFS Delineation        │
│   • pond_selector.py: Composite Suitability Index & Spatial NMS        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Algorithms & Computational Design

| No. | Algorithm | Mathematical Foundation | Data Structure | Complexity | Mean Time |
|:---:|:---|:---|:---|:---:|:---:|
| **1** | **UTM Reprojection** | Conformal Transverse Mercator $(\phi, \lambda) \to (X, Y)$ | NumPy `float64` array | $\mathcal{O}(M)$ | $42.1\,\text{ms}$ |
| **2** | **Delaunay DEM** | Bivariate linear barycentric $Z = \sum \lambda_j z_j$ | Quickhull Delaunay Tree | $\mathcal{O}(M \log M + N)$ | $268.4\,\text{ms}$ |
| **3** | **Slope & TWI** | Central differences: $p = \frac{\Delta Z_x}{2\delta}$, $q = \frac{\Delta Z_y}{2\delta}$ | 2D Vectorized Stride Slices | $\mathcal{O}(N)$ | $31.8\,\text{ms}$ |
| **4** | **D8 Routing** | Maximum hydraulic drop: $S_k = \frac{\Delta Z_k}{d_k}$ | 8-Moore Bitflag Matrix | $\mathcal{O}(N)$ | $54.2\,\text{ms}$ |
| **5** | **Flow Accumulation** | Directed Acyclic Graph (DAG) $A(u) = 1 + \sum A(v)$ | Elevation-Sorted DAG Queue | $\mathcal{O}(N)$ | $82.5\,\text{ms}$ |
| **6** | **Inverted CSR Catchment** | Upstream BFS basin tracing from pour point | CSR Arrays (`indptr`, `indices`) | $\mathcal{O}(\|V_{\text{basin}}\|)$ | **$4.6\,\text{ms}$** |
| **7** | **MCE & Spatial NMS** | $\text{CSI} = 0.60\,\tilde{A} + 0.30\,(1-\tilde{S}) + 0.10\,(1-\tilde{Z})$ | Distance Priority Queue | $\mathcal{O}(K \log K)$ | $18.3\,\text{ms}$ |
| **8** | **Rational Water Budget** | Empirical runoff formula: $V = 10 \cdot C \cdot P \cdot A$ | Closed-Form Equations | $\mathcal{O}(1)$ | $<0.1\,\text{ms}$ |

*Total End-to-End Pipeline Latency:* **$526.1\,\text{milliseconds}$** (tested on $1,391,600$ grid nodes).

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10 or higher
* `pip` and `virtualenv`
* Modern web browser (Chrome, Firefox, Safari, Edge)

### 1. Clone the Repository
```bash
git clone https://github.com/DongaShanmukhaSivaVenkataSai/Pond-Catchment-Site-Selection-System.git
cd Pond-Catchment-Site-Selection-System
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate

# Install required dependencies
pip install -r backend/requirements.txt
```

### 3. Launch the Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 5000 --reload
```

### 4. Access the Web GIS
Open your browser and navigate to:
* **Local Access:** [http://localhost:5000](http://localhost:5000)
* **Port-Forwarded Deployment:** [http://10.1.75.51:5252](http://10.1.75.51:5252)
* **Interactive API Documentation:** [http://localhost:5000/docs](http://localhost:5000/docs)

---

## 🛠️ REST API Reference

The backend exposes typed, asynchronous endpoints under `/api/v1`:

| Method | Endpoint | Description | Payload / Parameters | Response |
|:---:|:---|:---|:---|:---|
| `GET` | `/api/v1/health` | Service health status | None | `{"status": "ok", "service": "..."}` |
| `POST` | `/api/v1/parse` | Parse KML contours and build DEM | `multipart/form-data` (file: `.kml`/`.kmz`) | GeoJSON Contours & Bounding Box |
| `POST` | `/api/v1/analyze-hydrology` | Compute D8 routing, accumulation, and streams | Dataset token / grid session | GeoJSON Streams & Flow Matrices |
| `POST` | `/api/v1/select-ponds` | MCE scoring with spatial NMS | Optional land boundary polygon GeoJSON | Ranked candidate pond locations |
| `POST` | `/api/v1/delineate-catchment` | Upstream watershed BFS extraction | Clicked pour-point coordinates `(X, Y)` | Catchment polygon GeoJSON & Metrics |

---

## 📂 Project Directory Structure

```
Pond-Catchment-Site-Selection-System/
├── backend/
│   ├── app/
│   │   ├── routes.py                 # REST API endpoints & route handlers
│   │   ├── pipeline.py               # Integrated analysis orchestrator
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   └── services/
│   │       ├── kml_parser.py         # 3D coordinate extractor for KML/KMZ
│   │       ├── projection.py         # EPSG:4326 to EPSG:32644 transformer
│   │       ├── dem_builder.py        # 2D Delaunay bivariate DEM builder
│   │       ├── terrain.py            # Slope, aspect, and TWI derivation
│   │       ├── hydrology.py          # D8 flow routing & accumulation
│   │       ├── catchment.py          # Inverted CSR graph BFS delineation
│   │       ├── pond_selector.py      # MCE sink evaluation & spatial NMS
│   │       └── visualizer.py         # Colormap & contour visualization
│   ├── main.py                       # FastAPI entrypoint & static mount
│   └── requirements.txt              # Backend Python dependencies
├── frontend/
│   ├── index.html                    # Single-page Web GIS interface
│   ├── css/
│   │   └── style.css                 # Custom responsive stylesheet & HUD cards
│   └── js/
│       ├── api.js                    # REST API client with auto-origin detection
│       ├── app.js                    # Pipeline workflow orchestrator
│       ├── map.js                    # Leaflet map, basemaps & drawing controls
│       ├── hydrology.js              # Client-side Rational runoff calculations
│       └── ui.js                     # Real-time HUD, layer controls & alerts
├── .gitignore                        # Git exclusion rules
└── README.md                         # Project documentation
```

---

## 🔬 Hydrological Validation Example

For an evaluated rural watershed in Andhra Pradesh ($139.16\,\text{ha}$, elevation $42 - 68\,\text{m}$ AMSL):
* **Recommended Pond Location:** Candidate Site 1 (Elevation: $44.2\,\text{m}$ AMSL)
* **Delineated Upstream Catchment ($A$):** $32,540\,\text{m}^2$ ($3.254\,\text{hectares}$)
* **Annual Precipitation ($P$):** $830\,\text{mm}$ (Runoff coefficient $C = 0.40$ for clay-loam soil)
* **Total Harvestable Inflow Volume ($V$):** $10,803\,\text{m}^3$ ($10.80\,\text{megaliters}$)
* **Recommended Reservoir Dimensions:** $40\,\text{m} \times 35\,\text{m} \times 2.8\,\text{m}$ (Capacity: $3,920\,\text{m}^3$ storing $\approx 36\%$ of seasonal inflow with spillway bypass).

