# Production Architecture: Investment Portfolio System (Refined)

This document outlines the detailed architecture for the investment portfolio management system, specifically tailored to the project's production environment.

## System Architecture Diagram

```mermaid
graph TD
    subgraph Client_Environment["Client Environment"]
        Browser["Web Browser (React Client)"]
    end

    subgraph Frontend_Deployment["Frontend Deployment (Next.js)"]
        NextApp["Next.js App"]
        NextServer["Next.js Server (SSR/ISR)"]
    end

    subgraph Backend_Deployment["Backend Deployment (FastAPI)"]
        Uvicorn["Uvicorn ASGI Server"]
        FastAPI["FastAPI Application"]
    end

    subgraph API_Management["API Management & Routing"]
        Gateway["Cloud Gateway / Reverse Proxy"]
        RateLimiter["Redis (Rate Limiter)"]
    end

    subgraph Realtime_Infrastructure["Real-time Infrastructure"]
        RedisPubSub["Redis (Pub/Sub)"]
        WS_Server["WebSocket Handler (FastAPI)"]
    end

    subgraph Persistence_Layer["Managed Persistence Layer"]
        Pooler["Supabase Connection Pooler (PgBouncer)"]
        PostgreSQL["Supabase PostgreSQL"]
        RedisCache["Redis (Application Cache)"]
    end

    subgraph Background_Processing["Async Background processing"]
        WorkerQueue["Task Queue (Celery/RQ)"]
        Workers["Python Workers"]
    end

    subgraph Third_Party["External Services"]
        MarketData["Market Data APIs (VNStock)"]
        AuthService["Supabase Auth (JWT)"]
    end

    %% Data Flows
    Browser <--> |"HTTPS/WSS"| Gateway
    Gateway --> |"Fetch Assets"| NextApp
    Gateway --> |"API Requests"| Uvicorn
    Uvicorn --> FastAPI
    
    FastAPI --> |"Rate Limit Check"| RateLimiter
    FastAPI --> |"DB Access"| Pooler
    Pooler --> PostgreSQL
    FastAPI <--> |"Cache Read/Write"| RedisCache
    
    FastAPI --> |"Job Dispatch"| WorkerQueue
    WorkerQueue --> |"Task Consumption"| Workers
    
    MarketData --> |"Price Ingestion"| Workers
    Workers --> |"Persist State"| Pooler
    Workers --> |"Publish Update"| RedisPubSub
    
    RedisPubSub --> |"Broadcast Sub"| WS_Server
    WS_Server --> |"Real-time Push"| Browser
    
    Browser --> |"Auth Session"| AuthService
    FastAPI --> |"Verify JWT"| AuthService

    %% Legend
    classDef sync fill:#f9f,stroke:#333,stroke-width:2px;
    classDef async fill:#9cf,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef infra fill:#eee,stroke:#999,stroke-width:1px;

    class FastAPI,Uvicorn,NextApp,Gateway,Pooler,PostgreSQL sync;
    class Workers,RedisPubSub,WS_Server,WorkerQueue async;
    class RateLimiter,RedisCache,AuthService,MarketData infra;
```

---

## Component Explanation

### 1. **Next.js Frontend (Separate Deployment)**
- **Role**: Client-side application and Server-Side Rendering (SSR).
- **Deployment**: Deployed as a standalone service (e.g., Vercel or independent container).
- **Function**: Manages UI state, handles user interactions, and initiates WebSocket connections for live data.

### 2. **FastAPI Backend (Served by Uvicorn)**
- **Runtime**: **Uvicorn ASGI Server** handles concurrency and manages the lifecycle of the FastAPI application.
- **FastAPI**: Manages RESTful endpoints, business logic for portfolio tracking, and integration with secondary services.

### 3. **Redis: Cache & Rate Limiting**
- **Rate Limiter**: Integrated into the API middleware to prevent abuse and manage external API quotas (e.g., limiting stock data requests per user).
- **Application Cache**: Stores transient data like market summaries and popular ticker metadata to minimize database round-trips.

### 4. **Supabase Connection Pooler (PgBouncer)**
- **Purpose**: Acts as a proxy between the Backend and PostgreSQL. It manages a "pool" of active connections to the database.
- **Benefit**: Essential for serverless or containerized environments where many short-lived connections can overwhelm the database's native connection limit.

### 5. **WebSocket Infrastructure**
- **Protocol**: `wss://` for secure live updates.
- **Flow**: Background workers ingest price data from **VNStock**, push it to **Redis Pub/Sub**, and the FastAPI WebSocket handler broadcasts it immediately to subscribed browsers.

---

## Internal Component Breakdown

### 1. FastAPI Backend Internals
The backend is structured for high modularity and async data handling.

```mermaid
graph LR
    subgraph FastAPI_Internal["FastAPI Application"]
        Middlewares["Middlewares (Auth, Rate Limit, CORS)"]
        Routers["APIs Routers (/auth, /portfolio, /market)"]
        Deps["Dependencies (DB Session, User Auth)"]
        Services["Business Services (Calculation, Logic)"]
        Schemas["Pydantic Schemas (Validation)"]
        Models[SQLAlchemy/SQLModel]
    end

    Uvicorn --> Middlewares
    Middlewares --> Routers
    Routers --> Deps
    Deps --> Services
    Services --> Models
    Services --> Schemas
    Models --> Pooler
```

### 2. Next.js Frontend Internals
The frontend uses a modern React architecture for state and real-time updates.

```mermaid
graph TD
    subgraph NextJS_Layers["Next.js Structure"]
        AppRouter["App Router (Pages & Layouts)"]
        subgraph Components["Component Layer"]
            UI["shadcn/ui (Static/Layout)"]
            ClientComponents["Client Components (Dynamic)"]
        end
        subgraph State_Management["State & Data"]
            ReactQuery["React Query (Server State)"]
            Zustand["Zustand (Global Client State)"]
            WS_Hook["useWebSocket Hook"]
        end
    end

    AppRouter --> ClientComponents
    ClientComponents --> UI
    ClientComponents --> ReactQuery
    ClientComponents --> Zustand
    WS_Hook --> Zustand
```

### 3. Background Worker & Data Pipeline
The engine that keeps market data fresh.

```mermaid
graph LR
    subgraph Worker_Process["Python Worker Environment"]
        TaskHandler["Task Handler (Celery Worker)"]
        subgraph Pipelines["Data Processing"]
            Fetcher["External API Fetcher"]
            Aggregator["OHLC Aggregator"]
            Relay["Broadcaster (Redis Pub/Sub)"]
        end
    end

    Queue["Worker Queue"] --> TaskHandler
    TaskHandler --> Fetcher
    Fetcher --> Aggregator
    Aggregator --> Relay
    Aggregator --> Pooler
```

---

## Data Flow Explanation (Deep Dive)

### **The "Live Ticker" Pipeline (Asynchronous)**
1. **Sync Worker**: Periodically fetches prices from **External APIs**.
2. **Update Store**: Worker saves the new price to **Supabase** (via Pooler) for persistence.
3. **Notify Channel**: Worker publishes a JSON payload to a **Redis Channel** (e.g., `ticker:VNM`).
4. **Broadcast**: The **FastAPI WebSocket Server** (listening on that channel) pushes the message to all clients currently watching that ticker.

### **Authenticated API Request (Synchronous)**
1. **Gateway**: Passes the request + JWT header to **Uvicorn**.
2. **Rate Limit**: FastAPI checks **Redis** to see if the user has exceeded their request quota.
3. **Auth Check**: FastAPI verifies the **JWT** with **Supabase Auth**.
4. **Logic**: FastAPI executes business logic, fetching data via the **Supabase Pooler**.
5. **Response**: Result is returned through the Gateway to the Browser.
