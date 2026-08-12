# GridPilot VPP
An AI-driven Virtual Power Plant (VPP) Aggregation and Digital Twin Platform.

## 🚀 Project Overview

**GridPilot** is a production-grade enterprise software platform designed to manage, simulate, and optimize portfolios of distributed energy resources (DERs) like grid-scale battery energy storage systems (BESS). It solves the complex mathematical challenge of deciding *when* to charge, *when* to discharge, and *when* to provide ancillary services across multiple distinct assets simultaneously to maximize total portfolio profit against volatile wholesale electricity markets.

This project was built from scratch and demonstrates advanced full-stack engineering, mathematical optimization, distributed task queues, and modern multi-tenant cloud architecture.

---

## 🧠 Core Engineering Highlights

### 1. 2D Multi-Asset Mathematical Optimization
Unlike simple scripts that optimize a single battery, GridPilot utilizes **Google OR-Tools (GLOP Linear Solver)** to dynamically generate and solve a massive 2D matrix of constraints (Assets × Time). 
- **The Objective:** Maximize total VPP profit across Energy Arbitrage and Ancillary Services over a 24-hour horizon.
- **The Constraints:** It simultaneously respects individual physical battery constraints (Max Power, Max Energy Capacity, State of Charge continuity) while also enforcing strict **site-wide grid constraints** (e.g., ensuring the combined output of 5 batteries never exceeds the site's total grid interconnection limit).

### 2. Distributed Asynchronous Task Architecture
Energy optimization is computationally heavy. To ensure the frontend remains highly responsive, GridPilot implements a robust distributed task queue:
- **FastAPI** handles the lightweight web routing and authentication.
- **Celery & Redis** act as the message broker and background worker pool. When a user runs a backtest or live dispatch, FastAPI pushes the heavy OR-Tools matrix calculation to a Celery worker.
- **React Polling:** The frontend uses custom React Hooks to asynchronously poll the Celery task ID until the math is solved, entirely preventing browser freezes or HTTP timeouts.

### 3. True Multi-Tenant SaaS Architecture
GridPilot is designed as a B2B SaaS platform.
- **PostgreSQL Database:** Every asset, user, and simulation record is strictly bound to an `Organization` via Foreign Keys.
- **Automated Provisioning:** Upon signup, the backend automatically provisions a unique, mathematically isolated Workspace for the new user.
- **JWT Authentication:** Secure stateless authentication (PyJWT, bcrypt) ensures that users can only ever query and optimize assets belonging to their specific cryptographic token.

### 4. Interactive Data Visualization
The frontend is built using **Next.js** and styled with **Tailwind CSS** using modern, glassmorphic design principles.
- Complex energy market data is visualized using **Recharts (ComposedChart)**.
- It beautifully overlays stacked bar charts (individual battery dispatches) on top of line charts (Market Price and Aggregate State of Charge) to make dense mathematical schedules easily digestible by human operators.

---

## 🛠 Tech Stack

**Backend:**
- **Python 3.11** (Core Logic)
- **FastAPI** (Async Web Framework)
- **Google OR-Tools** (Linear Programming Solver)
- **Celery + Redis** (Distributed Task Queue)
- **SQLAlchemy (AsyncPG) + PostgreSQL** (Relational Database)
- **PyJWT & Passlib/Bcrypt** (Authentication)

**Frontend:**
- **Next.js (React 18)** (App Router)
- **Tailwind CSS** (Styling)
- **Recharts** (Data Visualization)
- **Lucide React** (Iconography)

---

## ⚙️ Deployment & Setup (Local)

To run this platform locally:

1. **Start the Redis Broker & PostgreSQL DB:**
   Ensure you have a local Redis server running on port `6379` and PostgreSQL on `5432`.

2. **Start the FastAPI Server:**
   ```bash
   cd e:\gridpilot
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Start the Celery Background Worker:**
   ```bash
   cd e:\gridpilot
   python -m celery -A app.worker.celery_app worker --loglevel=info -P solo
   ```

4. **Start the Next.js Frontend:**
   ```bash
   cd e:\gridpilot\frontend
   npm run dev
   ```

*(Note: In preparation for cloud deployment, all hardcoded localhost API endpoints have been upgraded to utilize the `NEXT_PUBLIC_API_URL` environment variable.)*
