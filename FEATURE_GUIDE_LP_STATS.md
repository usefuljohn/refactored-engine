# Implementation Guide: BitShares Liquidity Pool Statistics (Volume & Yield)

This guide outlines the technical steps required to upgrade the current valuation engine to fetch and calculate **24h Volume** and **Annualized Yield (APY)** for BitShares Liquidity Pools.

**Prerequisites:**
- Access to a **BitShares Full Node** with the `liquidity_pool` and `account_history` (or specific LP history) plugins enabled.
- Python environment with `websocket-client` (recommended for stateful API calls) or `requests` (if using a sticky HTTP session).

---

## 1. Architectural Upgrade: Stateful RPC Client

The current system uses stateless HTTP requests to the "Database API" (ID 0). Accessing historical data requires a stateful session to:
1.  **Login** to the node.
2.  **Request Access** to the `history` API.
3.  **Obtain the `history_api_id`** (dynamic ID, unlike Database API which is always 0).
4.  **Execute Calls** using this unique API ID.

**Recommendation:** Switch from simple HTTP `post` to a WebSocket client or a Persistent HTTP Session class that handles the handshake.

### Protocol Flow
1.  **Connect**
2.  `call(1, "login", ["", ""])` -> Returns `true`
3.  `call(1, "history", [])` -> Returns `history_api_id` (e.g., `2` or `3`)
4.  `call(history_api_id, "get_liquidity_pool_history", [pool_id, ...])`

---

## 2. Data Retrieval Strategy

### Method: `get_liquidity_pool_history`
This API method retrieves the ledger of operations affecting a specific pool.

**Parameters:**
- `pool_id`: The ID of the pool (e.g., `1.19.469`).
- `start`: Timestamp (ISO8601) - *Start of search window (newest)*.
- `stop`: Timestamp (ISO8601) - *End of search window (oldest)*.
- `limit`: Integer (e.g., 100).

**Fetching 24h Data:**
You must iterate backwards from "now" until you reach a timestamp older than 24 hours.
1.  Call `get_history` with `start = now`, `limit = 100`.
2.  Check the timestamp of the last operation received.
3.  If timestamp > (now - 24h), call again with `start = last_timestamp`, accumulating results.
4.  Stop when `timestamp < (now - 24h)` or no more results.

---

## 3. Data Processing & Calculation

### A. Filter Operations
We are interested primarily in **Exchange Operations** (swaps).
- **Operation ID:** `59` (liquidity_pool_exchange) *[Note: Verify ID on specific chain version]*
- **Structure:**
  ```json
  {
    "op": [
      59, 
      {
        "pool": "1.19.469",
        "account": "1.2.x",
        "amount_in": { "amount": 100000, "asset_id": "1.3.0" },
        "amount_out": { "amount": 95000, "asset_id": "1.3.1" },
        "fee": { ... } 
      }
    ],
    "block_num": 12345,
    "block_time": "2026-01-18T10:00:00"
  }
  ```

### B. Calculate Volume (24h)
1.  Identify the **USD-pegged side** of the pool (or convert one side to USD).
2.  Sum the `amount_in` (if it matches the USD asset) or `amount_out` (converted to USD) for all exchange operations in the 24h window.
3.  **Result:** `24h_Volume_USD`.

### C. Calculate Fees Earned
The pool earns fees on every swap. The fee rate is defined in the pool object (`taker_fee_percent`).
- **Fee Rate:** Usually expressed in basis points or hundredths of a percent (e.g., `15` might mean 0.15%).
- **Calculation:** `Fees_USD = 24h_Volume_USD * (taker_fee_percent / Scaling_Factor)`

### D. Calculate Yield (APY)
1.  **Projected Annual Fees:** `Fees_USD * 365`
2.  **Current TVL:** `Total Value Locked` (already calculated in your system).
3.  **APY:** `(Projected Annual Fees / Current TVL) * 100`

---

## 4. Implementation Logic (Pseudo-Code)

```python
class EnhancedBitSharesClient:
    def __init__(self, node_url):
        self.ws = connect(node_url)
        self.login()
        self.history_api_id = self.get_history_api()

    def get_24h_volume(self, pool_id, pool_assets):
        cutoff = datetime.now() - timedelta(hours=24)
        history = []
        last_op_time = datetime.now()
        
        # Pagination Loop
        while last_op_time > cutoff:
            batch = self.call(self.history_api_id, "get_liquidity_pool_history", 
                              [pool_id, last_op_time, ..., 100])
            if not batch: break
            
            history.extend(batch)
            last_op_time = parse_time(batch[-1]['block_time'])

        # Aggregation
        volume_usd = 0
        for op in history:
            if op['type'] == 'exchange':
                # Normalize amount to USD using your existing price oracle
                vol = normalize_to_usd(op['amount_in'], pool_assets)
                volume_usd += vol
                
        return volume_usd

# Integration in Valuation.py
def process_pool_metrics(pool_id):
    # 1. Existing TVL Calc
    tvl = get_tvl(pool_id)
    
    # 2. New Volume Calc
    vol_24h = client.get_24h_volume(pool_id)
    
    # 3. Yield Calc
    fee_rate = pool_obj['taker_fee_percent'] / 10000 # Assuming basis points
    fees_24h = vol_24h * fee_rate
    apy = (fees_24h * 365) / tvl
    
    return vol_24h, apy
```

## 5. Summary of Deliverables

1.  **`rpc_client.py`**: New module replacing simple `requests` calls with a class managing API IDs.
2.  **`pool_history.py`**: Logic to fetch and paginate 24h history.
3.  **`valuation.py` (Update)**:
    - Call `pool_history` for each pool.
    - Display Volume and Yield columns in the output.
    - Export new metrics to CSV.
