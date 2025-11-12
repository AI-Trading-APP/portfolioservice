"""
Portfolio Management Service
Tracks user holdings, P&L, positions, and portfolio performance
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
import os
import yfinance as yf
from collections import defaultdict

app = FastAPI(
    title="Portfolio Service",
    description="Portfolio management and tracking",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file
PORTFOLIOS_FILE = "portfolios.json"

# Models
class Position(BaseModel):
    ticker: str
    quantity: float
    avgCostBasis: float
    currentPrice: Optional[float] = None
    marketValue: Optional[float] = None
    unrealizedPL: Optional[float] = None
    unrealizedPLPercent: Optional[float] = None
    addedAt: str

class Transaction(BaseModel):
    id: str
    ticker: str
    type: str  # "buy" or "sell"
    quantity: float
    price: float
    timestamp: str
    fees: float = 0.0

class Portfolio(BaseModel):
    userId: str
    cash: float
    positions: List[Position]
    transactions: List[Transaction]
    totalValue: Optional[float] = None
    totalPL: Optional[float] = None
    totalPLPercent: Optional[float] = None

class AddPositionRequest(BaseModel):
    ticker: str
    quantity: float
    price: float

class RemovePositionRequest(BaseModel):
    ticker: str
    quantity: float
    price: float

# Helper functions
def load_portfolios() -> Dict:
    """Load portfolios from file"""
    if os.path.exists(PORTFOLIOS_FILE):
        with open(PORTFOLIOS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_portfolios(portfolios: Dict):
    """Save portfolios to file"""
    with open(PORTFOLIOS_FILE, 'w') as f:
        json.dump(portfolios, f, indent=2)

def get_current_price(ticker: str) -> float:
    """Get current stock price from yfinance"""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return 0.0
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return 0.0

def calculate_portfolio_metrics(portfolio: Dict) -> Dict:
    """Calculate portfolio metrics with current prices"""
    total_market_value = portfolio['cash']
    total_cost_basis = portfolio['cash']
    
    for position in portfolio['positions']:
        # Get current price
        current_price = get_current_price(position['ticker'])
        position['currentPrice'] = current_price
        
        # Calculate market value
        market_value = position['quantity'] * current_price
        position['marketValue'] = market_value
        
        # Calculate cost basis
        cost_basis = position['quantity'] * position['avgCostBasis']
        
        # Calculate unrealized P&L
        unrealized_pl = market_value - cost_basis
        position['unrealizedPL'] = unrealized_pl
        position['unrealizedPLPercent'] = (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0
        
        total_market_value += market_value
        total_cost_basis += cost_basis
    
    # Calculate total P&L
    portfolio['totalValue'] = total_market_value
    portfolio['totalPL'] = total_market_value - total_cost_basis
    portfolio['totalPLPercent'] = (portfolio['totalPL'] / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    return portfolio

def verify_token(authorization: Optional[str] = None) -> dict:
    """Simple token verification (matches other services)"""
    # For development, accept any token
    # In production, verify JWT token
    return {"user_id": "user_1"}  # Mock user

# Routes
@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "service": "Portfolio Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/api/portfolio", response_model=Portfolio)
def get_portfolio(token_data: dict = Depends(verify_token)):
    """Get user's portfolio with current prices"""
    user_id = token_data.get("user_id")
    portfolios = load_portfolios()

    # Initialize portfolio if doesn't exist
    if user_id not in portfolios:
        portfolios[user_id] = {
            "userId": user_id,
            "cash": 100000.0,  # Starting cash: $100,000
            "positions": [],
            "transactions": []
        }
        save_portfolios(portfolios)

    portfolio = portfolios[user_id]
    portfolio = calculate_portfolio_metrics(portfolio)

    return portfolio

@app.post("/api/portfolio/buy")
def buy_stock(request: AddPositionRequest, token_data: dict = Depends(verify_token)):
    """Buy stock and add to portfolio"""
    user_id = token_data.get("user_id")
    portfolios = load_portfolios()

    if user_id not in portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    portfolio = portfolios[user_id]

    # Calculate total cost
    total_cost = request.quantity * request.price

    # Check if enough cash
    if portfolio['cash'] < total_cost:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Deduct cash
    portfolio['cash'] -= total_cost

    # Find existing position or create new
    existing_position = None
    for pos in portfolio['positions']:
        if pos['ticker'] == request.ticker:
            existing_position = pos
            break

    if existing_position:
        # Update average cost basis
        total_quantity = existing_position['quantity'] + request.quantity
        total_cost_basis = (existing_position['quantity'] * existing_position['avgCostBasis']) + (request.quantity * request.price)
        existing_position['avgCostBasis'] = total_cost_basis / total_quantity
        existing_position['quantity'] = total_quantity
    else:
        # Add new position
        portfolio['positions'].append({
            "ticker": request.ticker,
            "quantity": request.quantity,
            "avgCostBasis": request.price,
            "addedAt": datetime.utcnow().isoformat()
        })

    # Add transaction
    transaction_id = f"txn_{len(portfolio['transactions']) + 1}"
    portfolio['transactions'].append({
        "id": transaction_id,
        "ticker": request.ticker,
        "type": "buy",
        "quantity": request.quantity,
        "price": request.price,
        "timestamp": datetime.utcnow().isoformat(),
        "fees": 0.0
    })

    save_portfolios(portfolios)

    return {"message": "Stock purchased successfully", "transactionId": transaction_id}

@app.post("/api/portfolio/sell")
def sell_stock(request: RemovePositionRequest, token_data: dict = Depends(verify_token)):
    """Sell stock from portfolio"""
    user_id = token_data.get("user_id")
    portfolios = load_portfolios()

    if user_id not in portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    portfolio = portfolios[user_id]

    # Find position
    position = None
    for pos in portfolio['positions']:
        if pos['ticker'] == request.ticker:
            position = pos
            break

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if position['quantity'] < request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient shares")

    # Calculate proceeds
    proceeds = request.quantity * request.price

    # Add cash
    portfolio['cash'] += proceeds

    # Update or remove position
    position['quantity'] -= request.quantity

    if position['quantity'] == 0:
        portfolio['positions'].remove(position)

    # Add transaction
    transaction_id = f"txn_{len(portfolio['transactions']) + 1}"
    portfolio['transactions'].append({
        "id": transaction_id,
        "ticker": request.ticker,
        "type": "sell",
        "quantity": request.quantity,
        "price": request.price,
        "timestamp": datetime.utcnow().isoformat(),
        "fees": 0.0
    })

    save_portfolios(portfolios)

    return {"message": "Stock sold successfully", "transactionId": transaction_id}

@app.get("/api/portfolio/transactions")
def get_transactions(token_data: dict = Depends(verify_token)):
    """Get transaction history"""
    user_id = token_data.get("user_id")
    portfolios = load_portfolios()

    if user_id not in portfolios:
        return {"transactions": []}

    return {"transactions": portfolios[user_id]['transactions']}

@app.get("/api/portfolio/performance")
def get_performance(token_data: dict = Depends(verify_token)):
    """Get portfolio performance metrics"""
    user_id = token_data.get("user_id")
    portfolios = load_portfolios()

    if user_id not in portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    portfolio = portfolios[user_id]
    portfolio = calculate_portfolio_metrics(portfolio)

    # Calculate additional metrics
    initial_value = 100000.0  # Starting cash
    current_value = portfolio['totalValue']
    total_return = ((current_value - initial_value) / initial_value) * 100

    return {
        "initialValue": initial_value,
        "currentValue": current_value,
        "totalReturn": total_return,
        "totalPL": portfolio['totalPL'],
        "totalPLPercent": portfolio['totalPLPercent'],
        "cash": portfolio['cash'],
        "investedValue": current_value - portfolio['cash']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)

