# BitShares Portfolio Valuation & Tracker

A Python-based tool for tracking and valuing cryptocurrency portfolios on the BitShares blockchain. This application specializes in monitoring Liquidity Pools (LPs) and Credit Offers across multiple strategies, providing real-time valuation in USD based on on-chain data.

## Features

*   **Multi-Portfolio Support:** Distinct tracking for six specific strategies:
    *   **USD:** Core Stablecoin strategies (`config_core.json`)
    *   **TWENTIX:** High-growth strategies (`config_growth.json`)
    *   **BTWTY:** BTWTY asset ecosystem (`config_btwty.json`)
    *   **BTWTY.EOS:** BTWTY.EOS specific pools (`config_btwty_eos.json`)
    *   **USD^30D:** 30-Day USD strategies (`config_usd_30d.json`)
    *   **BTS Portfolio:** BTS-based positions (`config_bts.json`)
*   **Liquidity Pool Valuation:**
    *   Calculates Total Value Locked (TVL) for configured pools.
    *   Determines user share value based on LP token holdings.
    *   **Smart Price Discovery:**
        *   **Direct:** Uses stablecoin (USDT, USDC) pairs for immediate valuation.
        *   **Reference:** Derives asset prices (e.g., TWENTIX, BTWTY, BTS) from specific reference pools.
        *   **Indirect:** Traces price paths (Asset -> Reference Asset -> USD) for complex pairs.
*   **Credit Offer Tracking:** Monitors TVL and ownership of BitShares credit offers.
*   **Graphical User Interface (GUI):**
    *   User-friendly dashboard built with `tkinter`.
    *   Tabbed views for different portfolios.
    *   **"Pot of Gold" Visualizer:** Tracks XAUT (Gold) pool price and visualizes portfolio value in gold ounces.
    *   Easy account management (add/remove BitShares account names).
*   **Data Logging:**
    *   **`capital_history.csv`:** Tracks the grand total value of all portfolios over time.
    *   **Individual Reports:** Saves detailed history for each portfolio (e.g., `capital_history_usd.csv`, `capital_history_twentix.csv`).
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

*(Note: The primary dependency is `requests` for blockchain API calls. `tkinter` is used for the GUI and is typically included with standard Python installations.)*

## Usage

### Graphical Interface (Recommended)
Run the GUI for an interactive dashboard:

```bash
python gui_valuation.py
```

1.  **Configure Accounts:** Enter your BitShares account name(s) in the top field (comma-separated) and click "Save & Scan".
2.  **Refresh:** Click "Refresh Data" to fetch the latest on-chain values.
3.  **View Data:** Navigate through the tabs (USD Portfolio, TWENTIX Portfolio, etc.) to see your positions and pool details.

### Command Line / Headless
Run the valuation script directly for a one-time update or cron job:

```bash
python valuation.py
```
This will fetch the latest data, print a summary to the console, and append the results to the CSV logs.

## Configuration

### User Settings
Account settings are stored in `user_settings.json`. You can edit this file directly or use the GUI.
```json
{
    "accounts": ["1.2.xxxx", "1.2.yyyy"],
    "account_names": ["account-name-1", "account-name-2"]
}
```

### Portfolio Configuration
Portfolios are defined in specific `config_*.json` files. Each file defines the pools or credit offers to track:

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
*   `capital_history.csv`: **Grand Total** of all portfolios combined.
*   `capital_history_usd.csv`
*   `capital_history_twentix.csv`
*   `capital_history_btwty.csv`
*   `capital_history_btwty_eos.csv`
*   `capital_history_usd_30d.csv`
*   `capital_history_bts.csv`

## File Structure

*   `valuation.py`: Core logic for calculating portfolio values and generating CSV reports.
*   `gui_valuation.py`: Tkinter-based GUI for the application.
*   `pool_data_handler.py`: Handles BitShares RPC connections and raw data fetching.
*   `fetch_symbols.py`: Utility to fetch asset symbols.
*   `config_*.json`: Configuration files for different portfolio strategies.
