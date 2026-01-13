# BitShares Portfolio Valuation & Tracker

A Python-based tool for tracking and valuing cryptocurrency portfolios on the BitShares blockchain. This application specializes in monitoring Liquidity Pools (LPs) and Credit Offers across multiple strategies, providing real-time valuation in USD based on on-chain data.

## Features

*   **Multi-Portfolio Support:** distinct tracking for different strategies (USD Stable, TWENTIX Growth, BTWTY, etc.).
*   **Liquidity Pool Valuation:**
    *   Calculates Total Value Locked (TVL) for configured pools.
    *   Determines user share value based on LP token holdings.
    *   Smart price discovery:
        *   **Direct:** Uses stablecoin (USDT, USDC) pairs for immediate valuation.
        *   **Reference:** Derives asset prices (e.g., TWENTIX, BTWTY) from specific reference pools.
        *   **Indirect:** Traces price paths (Asset -> Reference Asset -> USD) for complex pairs.
*   **Credit Offer Tracking:** Monitors TVL and ownership of BitShares credit offers.
*   **Graphical User Interface (GUI):**
    *   User-friendly dashboard built with `tkinter`.
    *   Tabbed views for different portfolios.
    *   "Pot of Gold" visualizer for XAUT (Gold) pool monitoring.
    *   Easy account management (add/remove BitShares account names).
*   **Data Logging:**
    *   Automatically saves historical valuation data to CSV files (`capital_history.csv`).
    *   Tracks individual pool performance and grand totals over time.
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

1.  **Configure Accounts:** Enter your BitShares account name(s) in the top field (comma-separated) and click "Save & Scan".
2.  **View Data:** Navigate through the tabs (USD Portfolio, TWENTIX Portfolio, etc.) to see your positions.
3.  **Refresh:** Click "Refresh Data" to fetch the latest on-chain values.

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
    "accounts": ["1.2.x", "1.2.y"],
    "account_names": ["account-name-1", "account-name-2"]
}
```

### Portfolio Configuration
Portfolios are defined in specific JSON files:
*   `config_core.json`: Core USD/Stablecoin pools.
*   `config_growth.json`: High-growth/TWENTIX pools.
*   `config_btwty.json`: BTWTY asset ecosystem.
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

## Output

The application generates CSV files for historical tracking:
*   `capital_history.csv`: Grand total of all portfolios over time.
*   `capital_history_usd.csv`, `capital_history_twentix.csv`, etc.: Detailed breakdowns for specific portfolios.

## File Structure

*   `valuation.py`: Core logic for calculating portfolio values and generating CSV reports.
*   `gui_valuation.py`: Tkinter-based GUI for the application.
*   `pool_data_handler.py`: Handles BitShares RPC connections and raw data fetching.
*   `fetch_symbols.py`: Utility to fetch asset symbols.
*   `config_*.json`: Configuration files for different portfolio strategies.

This tool automates the valuation of your BitShares Liquidity Pool (LP) holdings across multiple accounts and portfolios ("Core" and "TWENTIX").

## Features

*   **Multi-Account Tracking:** Aggregates balances from multiple BitShares accounts.
*   **Dual Portfolios:** Separates assets into "Core" (Stable) and "TWENTIX" (Speculative) categories.
*   **Automated Valuation:** 
    *   Uses "Stablecoin x 2" method for pools containing USDT/USDC.
    *   Uses "TWENTIX Reference Price" for other pools.
*   **Data Persistence:** Saves history to CSV files (`capital_history_usd.csv` and `capital_history_twentix.csv`).
*   **GUI:** Includes a graphical interface for easy viewing.

## Setup

1.  **Install Python:** Ensure you have Python 3.x installed.
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

*   **Accounts:** Edited in `valuation.py` (variable `ACCOUNTS`).
*   **Portfolios:**
    *   `config_core.json`: Configuration for Core assets.
    *   `config_growth.json`: Configuration for TWENTIX assets.
    *   `config_btwty_eos.json`: Configuration for BTWTY.EOS assets.

## Usage

### 1. Command Line Interface (CLI)
Run the script to generate CSV reports and see the output in the console:

```bash
python valuation.py
```

### 2. Graphical User Interface (GUI)
Launch the visual dashboard:

```bash
python gui_valuation.py
```
*   Click **"Refresh Data"** to fetch the latest data.
*   Switch tabs to view details for Core vs. TWENTIX vs. BTWTY.EOS.

## Output Files
*   `capital_history_usd.csv`
*   `capital_history_twentix.csv`
*   `capital_history_btwty_eos.csv`

## Technical Notes
*   `COMS.py` and `gui.py` are legacy tools for Credit Offer management and are not required for the valuation workflow.