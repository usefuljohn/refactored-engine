# BitShares Portfolio Valuation Engine

A comprehensive Python-based valuation engine for the BitShares blockchain. This tool calculates the real-time USD value of complex portfolios, including Liquidity Pool (LP) positions, Credit Offers (Lending), Liquid Wallet Assets, and Cold Storage/Staking balances.

## Key Features

*   **Multi-Portfolio Support**: Organizes assets into distinct strategies (e.g., USD Yield, Growth/TWENTIX, BTWTY Ecosystem, Staking).
*   **Smart LP Valuation**:
    *   Automatically values Liquidity Pool tokens based on the underlying assets.
    *   Uses a "2x Stablecoin" or "2x Reference Asset" strategy for accurate TVL calculation.
    *   Handles indirect pricing paths (e.g., Asset -> TWENTIX -> USD).
*   **Credit Offer Tracking**: Values active Credit Offers (Lending positions) in USD^30D portfolios.
*   **Historical Logging**: Exports valuation data to `capital_history.csv` for time-series tracking.
*   **Customizable Price Feeds**: Define specific pools as price references for illiquid or complex assets.
*   **Batch Processing**: Optimized RPC calls to fetch balances for multiple accounts efficiently.

## Project Structure

*   **`valuation.py`**: The main entry point. Orchestrates the valuation logic, pricing strategies, and report generation.
*   **`pool_data_handler.py`**: Handles blockchain interactions (RPC calls), data fetching, and caching to minimize network load.
*   **`fetch_symbols.py`**: Utility to fetch and cache asset symbols/precisions.
*   **`user_settings.json`**: Stores user-specific configurations (Account IDs).
*   **`config_*.json`**: Portfolio-specific configurations defining which pools, assets, or offers to track.

## Configuration

### 1. User Settings
Create or edit `user_settings.json` to include the BitShares Account IDs you want to track:

```json
{
    "accounts": [
        "1.2.xxxxxx",
        "1.2.yyyyyy"
    ]
}
```

### 2. Portfolio Configurations
The engine uses modular JSON files for each portfolio strategy:

*   **`config_core.json` (USD)**: Stablecoin LPs and core value storage.
*   **`config_growth.json` (TWENTIX)**: High-growth LPs paired with TWENTIX.
*   **`config_usd_30d.json`**: Credit Offers (Lending markets).
*   **`config_btwty.json`**: BTWTY ecosystem pools.
*   **`config_liquid.json`**: Liquid wallet assets (balances held directly in wallet).
*   **`config_staking.json`**: Offline or external staking balances (loaded via CSV).

## Usage

### Prerequisites
*   Python 3.x
*   Internet connection (to reach BitShares Public Nodes)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Valuation
```bash
python valuation.py
```

## Output

The script provides a color-coded console output breaking down:
1.  **Reference Prices**: Derived prices for core assets (BTS, TWENTIX, BTWTY).
2.  **Portfolio Breakdown**: Detailed list of assets/pools per portfolio with User Share %, Pool TVL, and User Value in USD.
3.  **Grand Total**: The aggregated USD value of all configured portfolios.
4.  **CSV Export**: Appends the total value and timestamp to `capital_history.csv`.

## Valuation Logic

*   **Liquidity Pools**: `(Balance_Side_A_or_B * Price * 2) * (User_Balance / Total_Supply)`
*   **Credit Offers**: `Balance * Price`
*   **Liquid Assets**: `Wallet_Balance * Price`
*   **Prices**:
    *   Stablecoins (USDT, USDC, HONEST.USD) are treated as $1.00 reference (or close to it).
    *   Volatile assets (BTS, TWENTIX) are priced via weighted averages of specific reference pools defined in configs.