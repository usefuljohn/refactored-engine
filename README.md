# BitShares Portfolio Valuation & Tracker

A Python-based tool for tracking and valuing cryptocurrency portfolios on the BitShares blockchain. This application monitors Liquidity Pools (LPs), wallet assets, and Credit Offers, providing real-time USD valuation based on on-chain data.

It features two primary modes:
*   **Private Mode:** Tracks your specific account balances, LP shares, and calculates your personal portfolio value.
*   **Public Mode:** Displays global statistics (Total Value Locked - TVL) for configured pools and offers, without requiring user account data.

## Features

*   **Dual Operation Modes:**
    *   **Private:** User-centric tracking (Balances, LP Shares, Staking).
    *   **Public:** Ecosystem-centric tracking (Global Pool TVL, Offer TVL).
*   **Multi-Portfolio Support:** Distinct tracking for different strategies (USD Stable, TWENTIX Growth, BTWTY, etc.).
*   **Liquidity Pool Valuation:**
    *   Calculates Total Value Locked (TVL) for configured pools.
    *   Smart price discovery:
        *   **Direct:** Uses stablecoin (USDT, USDC) pairs for immediate valuation.
        *   **Reference:** Derives asset prices (e.g., TWENTIX, BTWTY) from specific reference pools.
        *   **Indirect:** Traces price paths (Asset -> Reference Asset -> USD) for complex pairs.
*   **Credit Offer Tracking:** Monitors TVL and ownership of BitShares credit offers.
*   **Graphical User Interface (GUI):**
    *   User-friendly dashboard built with `tkinter`.
    *   **Mode Switcher:** Toggle between Private (User) and Public (Global) views instantly.
    *   Tabbed views for different portfolios.
    *   "Pot of Gold" visualizer for XAUT (Gold) pool monitoring.
*   **Data Logging:**
    *   **Private Mode:** Saves personal total value to `capital_history.csv`.
    *   **Public Mode:** Saves global TVL to `capital_history_global.csv`.
*   **Robust Networking:**
    *   Connects to multiple public BitShares RPC nodes with automatic failover.

## Installation

### Prerequisites
*   Python 3.x
*   `pip` (Python package installer)

### Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

*(Note: The main dependency is `requests` for API calls. `tkinter` is usually included with standard Python installations.)*

## Usage

### Graphical Interface (Recommended)
Run the GUI for an interactive dashboard:

```bash
python gui_valuation.py
```

1.  **Select Mode:** Use the radio buttons at the top to choose **Private** or **Public**.
2.  **Configure Accounts (Private Mode Only):** Enter your BitShares account name(s) (comma-separated) and click "Save & Scan".
3.  **Refresh:** Click "Refresh Data" to fetch the latest on-chain values.

### Command Line / Headless
Run the valuation script directly for one-time updates or cron jobs.

**Private Mode (User Portfolio):**
```bash
python valuation.py --mode private
```
*Calculates your share of the pools and saves to `capital_history.csv`.*

**Public Mode (Global Stats):**
```bash
python valuation.py --mode public
```
*Calculates the total TVL of all pools and saves to `capital_history_global.csv`.*

*(Running `python valuation.py` without arguments defaults to private mode).*

## Configuration

### User Settings
Account settings are stored in `user_settings.json` (Private Mode only). You can edit this file directly or use the GUI.
```json
{
    "accounts": ["1.2.x", "1.2.y"],
    "account_names": ["account-name-1", "account-name-2"]
}
```

### Portfolio Configuration
Portfolios are defined in specific JSON files:
*   `config_core.json`: Core USD/Stablecoin pools.
*   `config_growth.json`: High-growth/TWENTIX pools.
*   `config_btwty.json`: BTWTY asset ecosystem.
*   `config_liquid.json`: Wallet asset tracking.
*   `config_staking.json`: Staking balance tracking.
*   `config_usd_30d.json`: 30-day USD strategies.

Each config file defines the pools to track:
```json
{
    "pools": [
        {
            "id": "1.19.xxx",
            "asset_a": { "symbol": "SYMBOL", "precision": 5 },
            "asset_b": { "symbol": "USDT", "precision": 6 },
            "label": "Pool Label"
        }
    ]
}
```

## Output Files

The application generates CSV files for historical tracking:

*   **`capital_history.csv`**: (Private Mode) Grand total of your user portfolio over time.
*   **`capital_history_global.csv`**: (Public Mode) Grand total of global TVL over time.
*   `capital_history_*.csv`: Detailed breakdowns for specific portfolios (re-used for both modes).

## File Structure

*   `valuation.py`: Core logic for calculating portfolio values, handling modes, and generating CSV reports.
*   `gui_valuation.py`: Tkinter-based GUI with mode switching.
*   `pool_data_handler.py`: Handles BitShares RPC connections and raw data fetching.
*   `config_*.json`: Configuration files for different portfolio strategies.
