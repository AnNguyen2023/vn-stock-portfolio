# AI Coding Guidelines for VN Stock Portfolio

## Architecture Overview
This is a Vietnamese stock portfolio management system with:
- **Backend**: FastAPI (Python) with SQLAlchemy ORM, PostgreSQL database
- **Frontend**: Next.js 16 (React 19) with Tailwind CSS
- **Data Source**: Real-time stock prices from VPS Datafeed API (`https://bgapidatafeed.vps.com.vn/getliststockdata/{symbols}`)

## Key Domain Rules
- **Currency**: All prices stored in VND (Vietnamese Dong)
- **Price Input**: Users enter prices as decimals (e.g., 25.0 for 25,000 VND), but backend multiplies by 1000 for storage
- **Fees**: Default transaction fee rate = 0.15% (0.0015), tax rate = 0.1% (0.001) on sales
- **Settlement**: T+2 trading cycle (stocks settle 2 days after transaction)
- **Interest**: Lazy calculation on cash balance (calculated when accessed, not continuously)

## Database Schema (PostgreSQL)
- `asset_summary`: Cash balance, total deposited, fee rates
- `ticker_holdings`: Current positions with average cost basis
- `stock_transactions`: Buy/sell history with fees and taxes
- `cash_flow`: Deposits, withdrawals, dividends, custody fees
- `realized_profit`: Profit/loss from closed positions
- `daily_snapshots`: End-of-day NAV tracking

## Development Workflow
1. **Backend Setup**:
   - Install dependencies: `pip install -r requirements.txt`
   - Set up PostgreSQL database `vn_stock_db` (see `.env`)
   - Run: `uvicorn main:app --reload` (serves on :8000)
   - Reset DB: `python reset_db.py` (destructive)

2. **Frontend Setup**:
   - Install: `npm install`
   - Run: `npm run dev` (serves on :3000)
   - API calls proxy to `http://localhost:8000`

3. **CORS**: Backend allows `http://localhost:3000` for development

## Code Patterns
- **API Responses**: Use Vietnamese messages (e.g., "Nạp tiền thành công")
- **Error Handling**: HTTPException for insufficient funds, invalid tickers
- **Date Handling**: Use `datetime.now().date()` for settlement dates
- **Enums**: `TransactionType.BUY/SELL`, `CashFlowType.DEPOSIT/WITHDRAW/INTEREST`
- **Frontend State**: Privacy toggles for timeline/order history (default hidden)

## Common Tasks
- **Add New Transaction Type**: Update `models.py` enum, add to `main.py` endpoint, update `schemas.py`
- **Modify Fee Calculation**: Change in `main.py` buy/sell logic, affects `total_cost_vnd`
- **Add UI Component**: Use Lucide React icons, Tailwind classes, modal pattern from existing forms
- **Database Migration**: Manual schema changes (no Alembic), backup data before altering tables

## Testing
- Manual testing via `/docs` (FastAPI Swagger UI)
- Frontend hot-reload, backend requires restart for schema changes
- Stock prices update via `crawler.get_current_prices()` function

## Deployment Notes
- Environment variables in `.env` (DATABASE_URL)
- No production CORS origins configured yet
- VPS API may have rate limits for price data</content>
<parameter name="filePath">e:\vn-stock-portfolio\.github\copilot-instructions.md