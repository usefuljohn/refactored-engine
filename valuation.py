import json
import requests
import datetime
import csv
import os
from decimal import Decimal, getcontext
from pool_data_handler import get_pool_data, get_account_balance, get_all_account_balances, rpc_call

# Set precision
getcontext().prec = 28

# Enable ANSI escape codes on Windows
if os.name == 'nt':
    os.system('color')

class Style:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def fmt_money(value):
    """Format decimal/float as money string with green color."""
    return f"{Style.GREEN}${value:,.2f}{Style.RESET}"

def fmt_header(text):
    return f"{Style.CYAN}{Style.BOLD}{text}{Style.RESET}"

# Configuration
PORTFOLIOS = [
    {"name": "USD", "config": "config_core.json", "output": "capital_history_usd.csv"},
    {"name": "TWENTIX", "config": "config_growth.json", "output": "capital_history_twentix.csv"},
    {"name": "BTWTY", "config": "config_btwty.json", "output": "capital_history_btwty.csv"},
    {"name": "XBTSX.STH", "config": "config_xbtsx_sth.json", "output": "capital_history_xbtsx_sth.csv"},
    {"name": "Liquid", "config": "config_liquid.json", "output": "capital_history_liquid.csv"},
    {"name": "Staking", "config": "config_staking.json", "output": "capital_history_staking.csv"},
    {"name": "USD^30D", "config": "config_usd_30d.json", "output": "capital_history_usd_30d.csv"},
    {"name": "BTS Portfolio", "config": "config_bts.json", "output": "capital_history_bts.csv"},
    {"name": "BTC Portfolio", "config": "config_btc.json", "output": "capital_history_btc.csv"}
]

def load_user_settings():
    """Load user settings including accounts."""
    settings_file = "user_settings.json"
    defaults = {"accounts": []} # Default to empty
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    return defaults

def get_object(object_id):
    """Fetch a single object from the blockchain"""
    res = rpc_call("get_objects", [[object_id]])
    if res and len(res) > 0:
        return res[0]
    return None

def get_asset_supply(asset_id):
    """Get the current supply of an asset"""
    # 1. Get Asset Object
    asset_obj = get_object(asset_id)
    if not asset_obj:
        return Decimal(0), 0
        
    precision = asset_obj.get("precision", 0)
    dynamic_id = asset_obj.get("dynamic_asset_data_id")
    
    # 2. Get Dynamic Data
    dynamic_obj = get_object(dynamic_id)
    if not dynamic_obj:
        return Decimal(0), precision
        
    current_supply_raw = Decimal(dynamic_obj.get("current_supply", 0))
    return current_supply_raw / (Decimal(10) ** precision), precision

def get_bts_price_usd(config):
    """Determine BTS price in USD using reference pools"""
    candidates = []
    
    # Priority: Check 1.19.48 specifically as requested
    priority_pool_id = "1.19.48"
    
    # First pass: Look for priority pool in config or fetch it directly if needed
    # But usually we rely on config. Let's iterate config.
    
    found_priority = False
    
    for pool in config.get("pools", []):
        # Check for Priority Pool OR marked reference
        if pool["id"] == priority_pool_id or pool.get("is_price_reference"):
            
            p_data = get_pool_data(pool["id"])
            if not p_data:
                continue
            
            # Identify BTS side
            sym_a = pool["asset_a"]["symbol"]
            sym_b = pool["asset_b"]["symbol"]
            
            if "BTS" not in (sym_a, sym_b):
                continue
                
            is_bts_a = sym_a == "BTS"
            
            # Get precisions
            prec_a = pool["asset_a"]["precision"]
            prec_b = pool["asset_b"]["precision"]
            
            bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
            bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
            
            if bal_a == 0 or bal_b == 0:
                continue
            
            # We want Price of 1 BTS in USD
            # Price = USD_Side / BTS_Side
            
            price = Decimal(0)
            usd_sym = ""
            
            if is_bts_a:
                # BTS is A, Other is B (presumably USD/Stable)
                price = bal_b / bal_a
                usd_sym = sym_b
            else:
                # BTS is B, Other is A
                price = bal_a / bal_b
                usd_sym = sym_a
                
            print(f"  Reference Price from {usd_sym} ({pool['id']}): ${price:.6f}")
            
            if pool["id"] == priority_pool_id:
                # If we found the priority pool, we can just return this (or add to candidates with high weight)
                # Let's return it immediately as it is the "Gold Standard" for BTS price here
                print(f"  > Using Priority Pool {priority_pool_id} for BTS Price: ${price:.6f}")
                return price
            
            candidates.append(price)
            
    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average BTS Price: ${avg_price:.6f}")
        return avg_price
        
    print("  ! No price reference found for BTS.")
    return None

def get_btc_price_usd(config):
    """Determine XBTSX.BTC price in USD using reference pools"""
    candidates = []
    
    for pool in config.get("pools", []):
        if pool.get("is_price_reference"):
            # Check for XBTSX.BTC
            if "XBTSX.BTC" not in (pool["asset_a"]["symbol"], pool["asset_b"]["symbol"]):
                continue

            p_data = get_pool_data(pool["id"])
            if not p_data:
                continue
                
            is_btc_a = pool["asset_a"]["symbol"] == "XBTSX.BTC"
            
            # Get precisions
            prec_a = pool["asset_a"]["precision"]
            prec_b = pool["asset_b"]["precision"]
            
            bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
            bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
            
            if bal_a == 0 or bal_b == 0:
                continue
                
            if is_btc_a:
                # Pair is XBTSX.BTC / USD
                # Price of 1 BTC = USD_Bal / BTC_Bal = bal_b / bal_a
                price = bal_b / bal_a
                label = pool["asset_b"]["symbol"]
            else:
                # Pair is USD / XBTSX.BTC
                # Price of 1 BTC = USD_Bal / BTC_Bal = bal_a / bal_b
                price = bal_a / bal_b
                label = pool["asset_a"]["symbol"]
            
            print(f"  Reference Price from {label} ({pool['id']}): ${price:.6f}")
            candidates.append(price)
            
    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average XBTSX.BTC Price: ${avg_price:.6f}")
        return avg_price
        
    return None

def get_twentix_price_usd(config):
    """Determine TWENTIX price in USD using reference pools"""
    # Look for pools marked as price reference
    # Prefer USDC or USD
    
    candidates = []
    
    for pool in config.get("pools", []):
        if pool.get("is_price_reference"):
            # Safety Check: Ensure this is actually a TWENTIX pool
            if "TWENTIX" not in (pool["asset_a"]["symbol"], pool["asset_b"]["symbol"]):
                continue

            # Check which side is TWENTIX (Asset A or B)
            # We want Price = USD_Amount / TWENTIX_Amount
            
            p_data = get_pool_data(pool["id"])
            if not p_data:
                continue
                
            is_twentix_a = pool["asset_a"]["symbol"] == "TWENTIX"
            
            # Get precisions
            prec_a = pool["asset_a"]["precision"]
            prec_b = pool["asset_b"]["precision"]
            
            bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
            bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
            
            if bal_a == 0 or bal_b == 0:
                continue
                
            if is_twentix_a:
                # Pair is TWENTIX / USD
                # Price of 1 TWENTIX = USD_Bal / TWENTIX_Bal = bal_b / bal_a
                price = bal_b / bal_a
                label = pool["asset_b"]["symbol"]
            else:
                # Pair is USD / TWENTIX
                # Price of 1 TWENTIX = USD_Bal / TWENTIX_Bal = bal_a / bal_b
                price = bal_a / bal_b
                label = pool["asset_a"]["symbol"]
            
            print(f"  Reference Price from {pool['label']}: ${price:.6f}")
            candidates.append(price)
            
    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average TWENTIX Price: ${avg_price:.6f}")
        return avg_price
        
    print("  ! No price reference found in this config. Trying fallback...")
    return None

def get_xbtsx_sth_price_usd(config):
    """Determine XBTSX.STH price in USD using reference pools"""
    candidates = []
    
    for pool in config.get("pools", []):
        if pool.get("is_price_reference"):
            # Check for XBTSX.STH
            if "XBTSX.STH" not in (pool["asset_a"]["symbol"], pool["asset_b"]["symbol"]):
                continue

            p_data = get_pool_data(pool["id"])
            if not p_data:
                continue
                
            is_sth_a = pool["asset_a"]["symbol"] == "XBTSX.STH"
            
            # Get precisions
            prec_a = pool["asset_a"]["precision"]
            prec_b = pool["asset_b"]["precision"]
            
            bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
            bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
            
            if bal_a == 0 or bal_b == 0:
                continue
                
            if is_sth_a:
                # Pair is XBTSX.STH / USD
                # Price of 1 STH = USD_Bal / STH_Bal = bal_b / bal_a
                price = bal_b / bal_a
                label = pool["asset_b"]["symbol"]
            else:
                # Pair is USD / XBTSX.STH
                # Price of 1 STH = USD_Bal / STH_Bal = bal_a / bal_b
                price = bal_a / bal_b
                label = pool["asset_a"]["symbol"]
            
            print(f"  Reference Price from {pool['label']}: ${price:.6f}")
            candidates.append(price)
            
    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average XBTSX.STH Price: ${avg_price:.6f}")
        return avg_price
        
    return None

def get_btwty_eos_price_usd(config):
    """Determine BTWTY.EOS price in USD using 'A' pools"""
    candidates = []
    
    for pool in config.get("pools", []):
        if pool.get("label") == "A":
            p_data = get_pool_data(pool["id"])
            if not p_data:
                continue
                
            is_stable_a = is_stable_asset(pool["asset_a"]["symbol"])
            is_stable_b = is_stable_asset(pool["asset_b"]["symbol"])
            
            # Get precisions
            prec_a = pool["asset_a"]["precision"]
            prec_b = pool["asset_b"]["precision"]
            
            bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
            bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
            
            if bal_a == 0 or bal_b == 0:
                continue
                
            # We want Price of 1 BTWTY.EOS in USD
            # Price = Stable / BTWTY.EOS
            
            price = Decimal(0)
            if is_stable_a:
                # A is Stable, B is BTWTY.EOS
                price = bal_a / bal_b
            elif is_stable_b:
                # B is Stable, A is BTWTY.EOS
                price = bal_b / bal_a
                
            if price > 0:
                print(f"  Reference Price from Pool A ({pool['id']}): ${price:.6f}")
                candidates.append(price)

    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average BTWTY.EOS Price: ${avg_price:.6f}")
        return avg_price
        
    return None

def get_btwty_price_usd():
    """Determine BTWTY price in USD using 1.19.116 and 1.19.110"""
    # Hardcoded reference pools per request
    ref_pools = [
        {"id": "1.19.116", "asset_a": "BTWTY", "prec_a": 5, "asset_b": "XBTSX.USDC", "prec_b": 6},
        {"id": "1.19.110", "asset_a": "BTWTY", "prec_a": 5, "asset_b": "HONEST.USD", "prec_b": 4}
    ]
    
    candidates = []
    
    for pool in ref_pools:
        p_data = get_pool_data(pool["id"])
        if not p_data:
            continue
            
        prec_a = pool["prec_a"]
        prec_b = pool["prec_b"]
        
        bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
        bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
        
        if bal_a == 0 or bal_b == 0:
            continue
            
        # Price of 1 BTWTY (Asset A) in USD (Asset B)
        # Price = USD / BTWTY = bal_b / bal_a
        price = bal_b / bal_a
        print(f"  Reference Price from {pool['asset_b']} ({pool['id']}): ${price:.6f}")
        candidates.append(price)

    if candidates:
        avg_price = sum(candidates) / len(candidates)
        print(f"  > Average BTWTY Price: ${avg_price:.6f}")
        return avg_price
    
    return None

# Known Stablecoin Symbols/Substrings to check
STABLECOINS = ["USDT", "USDC", "HONEST.USD", "XBTSX.USDC", "USD"]

def is_stable_asset(symbol):
    """Check if asset symbol indicates a stablecoin"""
    # Exact match or endswith for things like "XBTSX.USDC"
    # Actually, let's just check if the known strings are in the symbol
    for s in STABLECOINS:
        if s == symbol or symbol.endswith(f".{s}") or symbol == s:
            return True
    return False

def ensure_csv_headers(filename, current_pool_labels):
    """
    Ensures the CSV file has the correct headers including Timestamp, Accounts, Total Value USD,
    and all current pool labels. Preserves existing data and columns.
    """
    base_headers = ["Timestamp", "Accounts", "Total Value USD"]
    
    # If file doesn't exist, just return the full new header list
    if not os.path.exists(filename):
        return base_headers + current_pool_labels

    existing_headers = []
    # Read existing headers
    try:
        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            try:
                existing_headers = next(reader)
            except StopIteration:
                pass
    except Exception as e:
        print(f"Warning: Could not read existing headers from {filename}: {e}")

    # Calculate new headers (preserving order of existing, adding new ones at end)
    new_headers = list(existing_headers)
    
    # 1. Ensure Base Headers are present
    for h in base_headers:
        if h not in new_headers:
            # If "Accounts" is missing, insert it after Timestamp if possible
            if h == "Accounts" and "Timestamp" in new_headers:
                 idx = new_headers.index("Timestamp") + 1
                 new_headers.insert(idx, h)
            else:
                 new_headers.append(h)

    # 2. Add any new pool labels that aren't in headers yet
    for label in current_pool_labels:
        if label not in new_headers:
            new_headers.append(label)

    # If headers changed, rewrite the file
    if new_headers != existing_headers:
        print(f"Updating CSV headers for {filename}...")
        rows = []
        if existing_headers:
            with open(filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=new_headers)
            writer.writeheader()
            for row in rows:
                # Remove extra fields (None key from DictReader) and keys not in new_headers
                clean_row = {k: v for k, v in row.items() if k in new_headers and k is not None}
                writer.writerow(clean_row)
                
    return new_headers

def find_twentix_price_for_asset(target_asset_symbol, all_pools_config):
    """
    Attempts to find the price of 'target_asset_symbol' in terms of TWENTIX
    by looking for a direct pair in the provided pools configuration.
    Returns: Price of 1 unit of Target Asset in TWENTIX (Decimal) or None
    """
    for pool in all_pools_config:
        p_a = pool["asset_a"]["symbol"]
        p_b = pool["asset_b"]["symbol"]
        
        # We are looking for a pair (Target, TWENTIX) or (TWENTIX, Target)
        if target_asset_symbol not in (p_a, p_b):
            continue
            
        other_asset = p_b if p_a == target_asset_symbol else p_a
        if other_asset != "TWENTIX":
            continue
            
        # Found a pairing pool!
        # Calculate price
        p_data = get_pool_data(pool["id"])
        if not p_data:
            continue
            
        prec_a = pool["asset_a"]["precision"]
        prec_b = pool["asset_b"]["precision"]
        
        bal_a = Decimal(p_data["balance_a"]) / (Decimal(10) ** prec_a)
        bal_b = Decimal(p_data["balance_b"]) / (Decimal(10) ** prec_b)
        
        if bal_a == 0 or bal_b == 0:
            continue

        # Price = TWENTIX Amount / Target Asset Amount
        if p_a == "TWENTIX":
            # Asset A is TWENTIX, Asset B is Target
            # Price = bal_a / bal_b
            return bal_a / bal_b
        else:
            # Asset B is TWENTIX, Asset A is Target
            # Price = bal_b / bal_a
            return bal_b / bal_a
            
    return None

def process_credit_portfolio(portfolio, config, accounts, prices=None, mode="private"):
    """Process a credit offer portfolio (TVL tracking)"""
    name = portfolio["name"]
    output_file = portfolio["output"]
    credit_offers = config.get("credit_offers", [])
    
    print(fmt_header(f"--- Processing Credit Offers for {name} ---"))
    
    if not credit_offers:
        print("  No credit offers configured.")
        return Decimal(0), Decimal(0), []
        
    ids = [offer["id"] for offer in credit_offers]
    
    # Fetch all objects in one batch
    # rpc_call("get_objects", [[id1, id2, ...]])
    objects = rpc_call("get_objects", [ids])
    
    if not objects:
        print("  Failed to fetch credit offer objects.")
        return Decimal(0), Decimal(0), []
        
    total_user_tvl = Decimal(0)
    total_global_tvl = Decimal(0)
    valuations = []
    
    # Create a map for easy lookup if order isn't guaranteed (though usually it is)
    # But get_objects returns list in same order as request.
    
    for i, offer_conf in enumerate(credit_offers):
        obj = objects[i]
        label = offer_conf.get("label", offer_conf["id"])
        
        if not obj:
            print(f"  {label}: Object not found")
            continue
            
        # Check balance
        # Credit offer object has 'total_balance'
        raw_balance = Decimal(obj.get("total_balance", 0))
        precision = offer_conf["precision"]
        
        real_balance = raw_balance / (Decimal(10) ** precision)
        
        # Determine price
        price = Decimal(1)
        asset_symbol = offer_conf.get("asset_symbol")
        if asset_symbol and prices and asset_symbol in prices and prices[asset_symbol]:
             price = prices[asset_symbol]
        
        usd_value = real_balance * price

        owner = obj.get("owner_account")
        is_owned = owner in accounts
        
        # display_val = usd_value
        user_val = usd_value if is_owned else Decimal(0)
        
        valuations.append({
            "pool": label, # Reusing 'pool' key for CSV consistency
            "share_percent": 100.0 if is_owned else 0.0,
            "value_usd": float(user_val),
            "raw_tvl_usd": float(usd_value),
            "owner": owner,
            "is_owned": is_owned
        })
        
        total_user_tvl += user_val
        total_global_tvl += usd_value

    # Sort valuations by value_usd descending
    valuations.sort(key=lambda x: x["raw_tvl_usd"], reverse=True)

    # Print sorted valuations
    for v in valuations:
        val_str = fmt_money(v['raw_tvl_usd'])
        if mode == "private":
            print(f"{v['pool']:15} | TVL: {val_str:20} | Owner: {v['owner']} | Included: {v['is_owned']}")
        else:
            print(f"{v['pool']:15} | Global TVL: {val_str}")
        
    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    print(f"{name.upper()} GLOBAL TVL: {fmt_money(total_global_tvl)}")
    if mode == "private":
        print(f"{name.upper()} USER VALUE: {fmt_money(total_user_tvl)}")
    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    
    return total_user_tvl, total_global_tvl, valuations

def process_csv_portfolio(portfolio, config, accounts, prices):
    """Process a portfolio defined by a CSV file of balances."""
    name = portfolio["name"]
    output_file = portfolio["output"]
    csv_file = config.get("csv_file")
    
    print(fmt_header(f"--- Processing CSV Balances for {name} ---"))
    
    if not csv_file or not os.path.exists(csv_file):
        print(f"  CSV file not found: {csv_file}")
        return Decimal(0), Decimal(0), []
        
    total_val_usd = Decimal(0)
    valuations = []
    
    try:
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                acct_id = row.get("Account ID", "").strip()
                
                # Only process if account is in our tracked list
                if acct_id not in accounts:
                    continue
                    
                symbol = row.get("Symbol", "").strip()
                balance_str = row.get("Balance", "0").strip()
                try:
                    balance = Decimal(balance_str)
                except:
                    print(f"  Invalid balance for {acct_id}: {balance_str}")
                    continue
                    
                # Determine Price
                price = Decimal(0)
                if symbol == "BTS" and prices.get("BTS"):
                    price = prices["BTS"]
                elif symbol in prices and prices[symbol]:
                     price = prices[symbol]
                else:
                    # Fallback or Todo: Handle other assets
                    print(f"  No price found for {symbol}")
                
                usd_value = balance * price
                
                # Create a label for the UI
                label = f"{symbol} (Staking)"
                
                valuations.append({
                    "pool": label, # Reusing 'pool' for UI column compatibility
                    "share_percent": 100.0,
                    "value_usd": float(usd_value),
                    "balance": float(balance),
                    "price": float(price)
                })
                
                total_val_usd += usd_value
                
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        return Decimal(0), Decimal(0), []

    # Sort valuations by value_usd descending
    valuations.sort(key=lambda x: x["value_usd"], reverse=True)

    # Print sorted valuations
    for v in valuations:
        val_str = fmt_money(v['value_usd'])
        print(f"{v['pool']:15} | Balance: {v['balance']:,.2f} | Price: ${v['price']:.6f} | Value: {val_str}")

    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    print(f"{name.upper()} VALUE: {fmt_money(total_val_usd)}")
    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    
    return total_val_usd, Decimal(0), valuations

def process_wallet_assets_portfolio(portfolio, config, accounts, prices, user_balances):
    """Process a portfolio of liquid wallet assets."""
    name = portfolio["name"]
    output_file = portfolio["output"]
    assets = config.get("assets", [])
    
    print(fmt_header(f"--- Processing Liquid Assets for {name} ---"))
    
    if not assets:
        print("  No assets configured.")
        return Decimal(0), Decimal(0), []
        
    total_val_usd = Decimal(0)
    valuations = []
    
    # Iterate over configured assets
    for asset_conf in assets:
        asset_id = asset_conf["id"]
        symbol = asset_conf["symbol"]
        precision = asset_conf["precision"]
        
        # Determine Price
        price = Decimal(0)
        
        if "fixed_price" in asset_conf:
             price = Decimal(asset_conf["fixed_price"])
        elif "price_reference" in asset_conf:
             ref = asset_conf["price_reference"]
             if ref in prices and prices[ref]:
                 price = prices[ref]
        
        # Calculate Balance across all accounts
        total_balance = Decimal(0)
        
        for acct_id in accounts:
            if acct_id in user_balances:
                raw_bal = user_balances[acct_id].get(asset_id, "0")
                total_balance += Decimal(raw_bal) / (Decimal(10) ** precision)
                
        usd_value = total_balance * price
        
        # Add to valuations if we have a definition, even if value is 0, to track headers?
        # Better to only add if we have something to report or at least keep consistency.
        # existing logic usually adds row data based on keys.
        
        if total_balance > -1: # Always show for now
            valuations.append({
                "pool": symbol, 
                "share_percent": 100.0,
                "value_usd": float(usd_value),
                "balance": float(total_balance),
                "price": float(price)
            })
            total_val_usd += usd_value

    # Sort valuations by value_usd descending
    valuations.sort(key=lambda x: x["value_usd"], reverse=True)

    # Print sorted valuations
    for v in valuations:
        val_str = fmt_money(v['value_usd'])
        print(f"{v['pool']:15} | Balance: {v['balance']:,.4f} | Price: ${v['price']:.6f} | Value: {val_str}")

    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    print(f"{name.upper()} VALUE: {fmt_money(total_val_usd)}")
    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    
    return total_val_usd, Decimal(0), valuations

def process_portfolio(portfolio, prices, accounts, user_balances, mode="private"):
    """Process a single portfolio configuration"""
    name = portfolio["name"]
    config_file = portfolio["config"]
    output_file = portfolio["output"]
    
    # Unpack prices
    twentix_price = prices.get("TWENTIX")
    btwty_eos_price = prices.get("BTWTY.EOS")
    btwty_price = prices.get("BTWTY")
    bts_price = prices.get("BTS")
    xbtsx_sth_price = prices.get("XBTSX.STH")
    btc_price = prices.get("XBTSX.BTC")

    print(fmt_header(f"\n=== Processing Portfolio: {name} ==="))
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading {config_file}: {e}")
        return Decimal(0), Decimal(0), []

    # Dispatcher for Portfolio Type
    if config.get("type") == "csv_balances":
        return process_csv_portfolio(portfolio, config, accounts, prices)

    if config.get("type") == "wallet_assets":
        return process_wallet_assets_portfolio(portfolio, config, accounts, prices, user_balances)

    if "credit_offers" in config:
        return process_credit_portfolio(portfolio, config, accounts, prices, mode=mode)

    pools = config.get("pools", [])
    if not pools:
        print(f"  No pools configured for {name}.")
        return Decimal(0), Decimal(0), []

    # If global price isn't set, try to find it in this config (only if needed fallback)
    if not twentix_price:
         twentix_price = get_twentix_price_usd(config)
    
    if not twentix_price:
        # Final fallback
        twentix_price = Decimal("0.003")
        # Only warn if we actually might need it
        # print(f"  Using Hardcoded Safety Price: ${twentix_price}")

    total_portfolio_usd = Decimal(0)
    total_pool_tvl_usd = Decimal(0)
    pool_valuations = []

    print(fmt_header(f"--- Processing Pools for {name} ---"))
    
    for pool_conf in pools:
        pool_id = pool_conf["id"]
        label = pool_conf["label"]
        
        # Fetch Pool Data
        pool_obj = get_pool_data(pool_id)
        if not pool_obj:
            print(f"Skipping {label} ({pool_id}): No data")
            continue
            
        share_asset_id = pool_obj.get("share_asset")
        
        # Get Total Supply of LP Token
        total_supply, share_prec = get_asset_supply(share_asset_id)
        
        if total_supply == 0:
            print(f"Skipping {label}: Zero supply")
            continue
            
        # Get User Balances (Using Cached Data)
        user_balance_total = Decimal(0)
        for account in accounts:
            # Check cached balances for this account
            if account in user_balances:
                bal_raw = user_balances[account].get(share_asset_id, "0")
                user_balance_total += Decimal(bal_raw) / (Decimal(10) ** share_prec)
        
        # We now allow zero balance to show up in the report (as 0% share)
        # if user_balance_total == 0:
        #    continue
            
        # --- VALUATION LOGIC ---
        pool_tvl_usd = Decimal(0)
        
        asset_a_sym = pool_conf["asset_a"]["symbol"]
        asset_b_sym = pool_conf["asset_b"]["symbol"]
        prec_a = pool_conf["asset_a"]["precision"]
        prec_b = pool_conf["asset_b"]["precision"]
        
        balance_a = Decimal(pool_obj["balance_a"]) / (Decimal(10) ** prec_a)
        balance_b = Decimal(pool_obj["balance_b"]) / (Decimal(10) ** prec_b)

        # Method 1: Stablecoin x 2
        if is_stable_asset(asset_a_sym):
            pool_tvl_usd = balance_a * 2
            # print(f"  > {label}: Valued via {asset_a_sym} x 2")
        elif is_stable_asset(asset_b_sym):
            pool_tvl_usd = balance_b * 2
            # print(f"  > {label}: Valued via {asset_b_sym} x 2")
        else:
            # Custom: BTWTY.EOS Valuation (from USD portfolio "A" pools)
            if btwty_eos_price and ("BTWTY.EOS" == asset_a_sym or "BTWTY.EOS" == asset_b_sym):
                if asset_a_sym == "BTWTY.EOS":
                    pool_tvl_usd = (balance_a * btwty_eos_price) * 2
                else:
                    pool_tvl_usd = (balance_b * btwty_eos_price) * 2

            # Custom: BTWTY Valuation
            elif btwty_price and (asset_a_sym == "BTWTY" or asset_b_sym == "BTWTY"):
                if asset_a_sym == "BTWTY":
                    pool_tvl_usd = (balance_a * btwty_price) * 2
                else:
                    pool_tvl_usd = (balance_b * btwty_price) * 2

            # Custom: BTS Valuation
            elif bts_price and (asset_a_sym == "BTS" or asset_b_sym == "BTS"):
                if asset_a_sym == "BTS":
                    pool_tvl_usd = (balance_a * bts_price) * 2
                else:
                    pool_tvl_usd = (balance_b * bts_price) * 2
            
            # Custom: XBTSX.STH Valuation
            elif xbtsx_sth_price and (asset_a_sym == "XBTSX.STH" or asset_b_sym == "XBTSX.STH"):
                if asset_a_sym == "XBTSX.STH":
                    pool_tvl_usd = (balance_a * xbtsx_sth_price) * 2
                else:
                    pool_tvl_usd = (balance_b * xbtsx_sth_price) * 2

            # Custom: XBTSX.BTC Valuation
            elif btc_price and (asset_a_sym == "XBTSX.BTC" or asset_b_sym == "XBTSX.BTC"):
                if asset_a_sym == "XBTSX.BTC":
                    pool_tvl_usd = (balance_a * btc_price) * 2
                else:
                    pool_tvl_usd = (balance_b * btc_price) * 2

            # Method 2: TWENTIX Reference (Direct)
            elif asset_a_sym == "TWENTIX" or asset_b_sym == "TWENTIX":
                is_twentix_a = asset_a_sym == "TWENTIX"
                if is_twentix_a:
                    pool_tvl_usd = (balance_a * 2) * twentix_price
                else:
                    pool_tvl_usd = (balance_b * 2) * twentix_price
            else:
                # Method 3: Indirect Reference via TWENTIX
                # Try to find a path: Asset A -> TWENTIX -> USD
                price_a_in_twentix = find_twentix_price_for_asset(asset_a_sym, pools)
                
                if price_a_in_twentix:
                     # Value of Asset A side in TWENTIX = Balance A * Price(A->TWENTIX)
                     val_a_in_twentix = balance_a * price_a_in_twentix
                     pool_tvl_usd = (val_a_in_twentix * 2) * twentix_price
                     # print(f"  > {label}: Indirect val via {asset_a_sym}->TWENTIX")
                else:
                    # Try Asset B
                    price_b_in_twentix = find_twentix_price_for_asset(asset_b_sym, pools)
                    if price_b_in_twentix:
                        val_b_in_twentix = balance_b * price_b_in_twentix
                        pool_tvl_usd = (val_b_in_twentix * 2) * twentix_price
                        # print(f"  > {label}: Indirect val via {asset_b_sym}->TWENTIX")
                    else:
                        print(f"  Warning: {label} has no Stablecoin, TWENTIX, or resolvable path. Skipping valuation.")
                        continue

        # User Share
        share_ratio = user_balance_total / total_supply
        user_value_usd = pool_tvl_usd * share_ratio
        
        # Store for sorting
        pool_valuations.append({
            "pool": label,
            "share_percent": float(share_ratio * 100),
            "value_usd": float(user_value_usd),
            "pool_tvl_usd": float(pool_tvl_usd)
        })
        
        total_portfolio_usd += user_value_usd
        total_pool_tvl_usd += pool_tvl_usd

    # Sort by value_usd descending, or pool_tvl if user value is 0 (public mode)
    if mode == "private":
        pool_valuations.sort(key=lambda x: x["value_usd"], reverse=True)
    else:
        pool_valuations.sort(key=lambda x: x["pool_tvl_usd"], reverse=True)

    # Print sorted
    for v in pool_valuations:
        tvl_str = fmt_money(v['pool_tvl_usd'])
        val_str = fmt_money(v['value_usd'])
        if mode == "private":
            print(f"{v['pool']:15} | Share: {v['share_percent']:6.4f}% | Pool TVL: {tvl_str:20} | Your Value: {val_str}")
        else:
            print(f"{v['pool']:15} | Pool TVL: {tvl_str}")

    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    print(f"{name.upper()} GLOBAL TVL:      {fmt_money(total_pool_tvl_usd)}")
    if mode == "private":
        print(f"{name.upper()} PORTFOLIO VALUE: {fmt_money(total_portfolio_usd)}")
    print(f"{Style.DIM}" + "-" * 60 + f"{Style.RESET}")
    
    return total_portfolio_usd, total_pool_tvl_usd, pool_valuations

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BitShares Portfolio Valuation")
    parser.add_argument("--mode", choices=["private", "public"], default="private", help="Mode: private (user accounts) or public (global stats)")
    args = parser.parse_args()

    mode = args.mode
    print(fmt_header(f"Starting Valuation Model ({mode.upper()} MODE) at {datetime.datetime.now()}"))

    accounts = []
    if mode == "private":
        settings = load_user_settings()
        accounts = settings.get("accounts", [])
        print(f"Tracking Accounts: {', '.join(accounts)}")
        if not accounts:
            print("No accounts configured for private mode. Please check user_settings.json")
            return
    else:
        print("Running in Public Mode. Ignoring user accounts.")

    # --- OPTIMIZATION START ---
    # Fetch all account balances once (only for private mode)
    print(fmt_header("--- Fetching Balances ---"))
    user_balances = {}
    if accounts:
        for acct_id in accounts:
            print(f"  Fetching balances for {acct_id}...")
            user_balances[acct_id] = get_all_account_balances(acct_id)
    # --- OPTIMIZATION END ---

    # Pre-fetch price if possible to ensure consistency across portfolios
    # We'll peek at the Core config for this
    print(fmt_header("\n--- Establishing Reference Price ---"))
    
    prices = {"TWENTIX": None, "BTWTY.EOS": None, "BTWTY": None, "XBTSX.STH": None, "XBTSX.BTC": None}
    
    # Get BTWTY.EOS price from Core Config
    try:
        with open("config_core.json", "r") as f:
            core_config = json.load(f)
            prices["BTWTY.EOS"] = get_btwty_eos_price_usd(core_config)
    except Exception as e:
        print(f"Error loading config_core.json for prices: {e}")

    # Get TWENTIX price from Growth Config (TWENTIX Portfolio)
    try:
        with open("config_growth.json", "r") as f:
            growth_config = json.load(f)
            prices["TWENTIX"] = get_twentix_price_usd(growth_config)
    except Exception as e:
        print(f"Error loading config_growth.json for prices: {e}")

    # Get XBTSX.STH price from XBTSX.STH Portfolio Config
    try:
        with open("config_xbtsx_sth.json", "r") as f:
            sth_config = json.load(f)
            prices["XBTSX.STH"] = get_xbtsx_sth_price_usd(sth_config)
    except Exception as e:
        print(f"Error loading config_xbtsx_sth.json for prices: {e}")

    prices["BTWTY"] = get_btwty_price_usd()

    # Get BTS price from BTS Portfolio Config
    try:
        with open("config_bts.json", "r") as f:
            bts_config = json.load(f)
            prices["BTS"] = get_bts_price_usd(bts_config)
    except Exception as e:
        print(f"Error loading config_bts.json for prices: {e}")

    # Get XBTSX.BTC price from BTC Portfolio Config
    try:
        with open("config_btc.json", "r") as f:
            btc_config = json.load(f)
            prices["XBTSX.BTC"] = get_btc_price_usd(btc_config)
    except Exception as e:
        print(f"Error loading config_btc.json for prices: {e}")
        
    grand_total_user = Decimal(0)
    grand_total_global = Decimal(0)
    
    for p in PORTFOLIOS:
        val_user, val_global, _ = process_portfolio(p, prices, accounts, user_balances, mode=mode)
        if val_user:
            grand_total_user += val_user
        if val_global:
            grand_total_global += val_global
            
    print("\n" + f"{Style.BOLD}{Style.CYAN}" + "=" * 60 + f"{Style.RESET}")
    if mode == "private":
        print(f"{Style.BOLD}GRAND TOTAL (USER):   {Style.GREEN}${grand_total_user:,.2f}{Style.RESET}")
    print(f"{Style.BOLD}GRAND TOTAL (GLOBAL): {Style.GREEN}${grand_total_global:,.2f}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}" + "=" * 60 + f"{Style.RESET}")

    # Save to CSV
    if mode == "private":
        total_history_file = "capital_history.csv"
        file_exists = os.path.isfile(total_history_file)
        
        with open(total_history_file, 'a', newline='') as f:
            fieldnames = ["Timestamp", "Total Value USD"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow({
                "Timestamp": datetime.datetime.now().isoformat(),
                "Total Value USD": f"{grand_total_user:.2f}"
            })
            print(f"User Grand Total saved to {total_history_file}")
            
    else: # Public Mode
        total_history_file = "capital_history_global.csv"
        file_exists = os.path.isfile(total_history_file)
        
        with open(total_history_file, 'a', newline='') as f:
            fieldnames = ["Timestamp", "Global TVL USD"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow({
                "Timestamp": datetime.datetime.now().isoformat(),
                "Global TVL USD": f"{grand_total_global:.2f}"
            })
            print(f"Global Grand Total saved to {total_history_file}")

if __name__ == "__main__":
    main()
