# Portfolio Service

Portfolio management and tracking microservice for AI Trading Platform.

## Features

- Real-time portfolio positions
- P&L calculation (realized/unrealized)
- Cost basis tracking with average cost method
- Portfolio value history
- Asset allocation breakdown
- Performance metrics (returns, total value)
- Transaction history
- Buy/sell stock operations

## API Endpoints

### Portfolio Management
- `GET /api/portfolio` - Get user's portfolio with current prices (requires auth)
- `POST /api/portfolio/buy` - Buy stock (requires auth)
- `POST /api/portfolio/sell` - Sell stock (requires auth)
- `GET /api/portfolio/transactions` - Get transaction history (requires auth)
- `GET /api/portfolio/performance` - Get performance metrics (requires auth)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
python main.py
```

The service will start on `http://localhost:8004`

## Example Usage

### Get Portfolio
```bash
curl http://localhost:8004/api/portfolio \
  -H "Authorization: Bearer <token>"
```

### Buy Stock
```bash
curl -X POST http://localhost:8004/api/portfolio/buy \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "ticker": "AAPL",
    "quantity": 10,
    "price": 150.00
  }'
```

### Sell Stock
```bash
curl -X POST http://localhost:8004/api/portfolio/sell \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "ticker": "AAPL",
    "quantity": 5,
    "price": 155.00
  }'
```

## Data Storage

Portfolio data is stored in `portfolios.json` file with the following structure:

```json
{
  "user_1": {
    "userId": "user_1",
    "cash": 95000.0,
    "positions": [
      {
        "ticker": "AAPL",
        "quantity": 10,
        "avgCostBasis": 150.00,
        "currentPrice": 155.00,
        "marketValue": 1550.00,
        "unrealizedPL": 50.00,
        "unrealizedPLPercent": 3.33,
        "addedAt": "2025-11-13T06:00:00.000Z"
      }
    ],
    "transactions": [
      {
        "id": "txn_1",
        "ticker": "AAPL",
        "type": "buy",
        "quantity": 10,
        "price": 150.00,
        "timestamp": "2025-11-13T06:00:00.000Z",
        "fees": 0.0
      }
    ],
    "totalValue": 96550.00,
    "totalPL": -3450.00,
    "totalPLPercent": -3.45
  }
}
```

## Notes

- Starting cash: $100,000
- Real-time prices fetched from yfinance
- Average cost basis method for position tracking
- No trading fees in current implementation
- Supports fractional shares

