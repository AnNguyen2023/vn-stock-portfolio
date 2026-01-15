# 🛠 Setup & Installation Guide

Follow these steps to get the **Invest Journal** stack running on your local machine.

## 📋 Prerequisites
- **Python 3.11+**
- **Node.js 20+** (pnpm recommended)
- **PostgreSQL 15+**
- **Redis** (Local or Cloud instance)

---

## 🔧 Backend Setup
1.  **Navigate to backend**:
    ```bash
    cd backend
    ```
2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment**:
    - Create a `.env` file based on the provided template.
    - Set `DATABASE_URL`, `REDIS_URL`, and VPS credentials.
5.  **Run Migrations & Start**:
    ```bash
    python main.py
    ```

---

## 🎨 Frontend Setup
1.  **Navigate to frontend**:
    ```bash
    cd frontend
    ```
2.  **Install Dependencies**:
    ```bash
    npm install  # or pnpm install
    ```
3.  **Configure Environment**:
    - Create `.env.local` with `NEXT_PUBLIC_API_URL`.
4.  **Start Development Server**:
    ```bash
    npm run dev
    ```

---

## 🐳 Docker Deployment (Recommended for Demo)
If you have Docker installed, you can spin up the entire stack with one command:

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)

---

## ⚠️ Troubleshooting
- **Market Data Not Updating**: Check your VPS API credentials in `backend/.env`.
- **Database Connection Refused**: Ensure PostgreSQL is running and the user has correct permissions.
- **Redis Error**: Verify Redis is accessible for the Pub/Sub messaging system.
