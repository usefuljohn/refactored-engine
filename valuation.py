import json
import requests
import datetime
import csv
import os
from decimal import Decimal, getcontext
from pool_data_handler import get_pool_data, get_account_balance, get_all_account_balances, rpc_call

# Set precision
getcontext().prec = 28

# Configuration
PORTFOLIOS = [
    {"name": "USD", "config": "config_core.json", "output": "capital_history_usd.csv"},
    {"name": "TWENTIX", "config": "config_growth.json", "output": "capital_history_twentix.csv"},
    {"name": "BTWTY", "config": "config_btwty.json", "output": "capital_history_btwty.csv"},
    {"name": "BTWTY.EOS", "config": "config_btwty_eos.json", "output": "capital_history_btwty_eos.csv"},
    {"name": "USD^30D", "config": "config_usd_30d.json", "output": "capital_history_usd_30d.csv"}
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

def get_twentix_price_usd(config):
    """Determine TWENTIX price in USD using reference pools"""
    # Look for pools marked as price reference
    # Prefer USDC or USD
    
    candidates = []
    
    for pool in config.get("pools", []):
        if pool.get("is_price_reference"):
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

def process_credit_portfolio(portfolio, config, accounts):
    """Process a credit offer portfolio (TVL tracking)"""
    name = portfolio["name"]
    output_file = portfolio["output"]
    credit_offers = config.get("credit_offers", [])
    
    print(f"--- Processing Credit Offers for {name} ---")
    
    if not credit_offers:
        print("  No credit offers configured.")
        return Decimal(0), []
        
    ids = [offer["id"] for offer in credit_offers]
    
    # Fetch all objects in one batch
    # rpc_call("get_objects", [[id1, id2, ...]])
    objects = rpc_call("get_objects", [ids])
    
    if not objects:
        print("  Failed to fetch credit offer objects.")
        return Decimal(0), []
        
    total_tvl = Decimal(0)
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
        
        owner = obj.get("owner_account")
        is_owned = owner in accounts
        
        display_val = real_balance
        user_val = real_balance if is_owned else Decimal(0)
        
        print(f"{label:15} | TVL: ${display_val:,.2f} | Owner: {owner} | Included: {is_owned}")
        
        valuations.append({
            "pool": label, # Reusing 'pool' key for CSV consistency
            "share_percent": 100.0 if is_owned else 0.0,
            "value_usd": float(user_val)
        })
        
        total_tvl += user_val
        
    print("-" * 60)
    print(f"{name.upper()} USER VALUE: ${total_tvl:,.2f}")
    print("-" * 60)
    
    # Save to CSV
    # Reusing ensure_csv_headers - works the same, just different labels
    all_labels = [o.get("label", o["id"]) for o in credit_offers]
    final_headers = ensure_csv_headers(output_file, all_labels)
    
    row_data = {
        "Timestamp": datetime.datetime.now().isoformat(),
        "Accounts": ";".join(accounts) if accounts else "None",
        "Total Value USD": f"{total_tvl:.2f}"
    }
    
    for val in valuations:
        row_data[val["pool"]] = f"{val['value_usd']:.2f}"
        
    with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        if os.stat(output_file).st_size == 0:
            writer.writeheader()
        writer.writerow(row_data)
        print(f"Data saved to {output_file}")
        
    return total_tvl, valuations

def process_portfolio(portfolio, prices, accounts, user_balances):
    """Process a single portfolio configuration"""
    name = portfolio["name"]
    config_file = portfolio["config"]
    output_file = portfolio["output"]
    
    # Unpack prices
    twentix_price = prices.get("TWENTIX")
    btwty_eos_price = prices.get("BTWTY.EOS")
    btwty_price = prices.get("BTWTY")

    print(f"\n=== Processing Portfolio: {name} ===")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading {config_file}: {e}")
        return

    # Dispatcher for Portfolio Type
    if "credit_offers" in config:
        return process_credit_portfolio(portfolio, config, accounts)

    pools = config.get("pools", [])
    if not pools:
        print(f"  No pools configured for {name}.")
        return Decimal(0)

    # If global price isn't set, try to find it in this config (only if needed fallback)
    if not twentix_price:
         twentix_price = get_twentix_price_usd(config)
    
    if not twentix_price:
        # Final fallback
        twentix_price = Decimal("0.003")
        # Only warn if we actually might need it
        # print(f"  Using Hardcoded Safety Price: ${twentix_price}")

    total_portfolio_usd = Decimal(0)
    pool_valuations = []

    print(f"--- Processing Pools for {name} ---")
    
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
        
        print(f"{label:15} | Share: {share_ratio*100:6.4f}% | Pool TVL: ${pool_tvl_usd:12.2f} | Your Value: ${user_value_usd:10.2f}")
        
        pool_valuations.append({
            "pool": label,
            "share_percent": float(share_ratio * 100),
            "value_usd": float(user_value_usd)
        })
        
        total_portfolio_usd += user_value_usd

    print("-" * 60)
    print(f"{name.upper()} PORTFOLIO VALUE: ${total_portfolio_usd:,.2f}")
    print("-" * 60)
    
    # Save to CSV
    # Collect all possible pool labels from config to ensure full coverage
    all_pool_labels = [p["label"] for p in pools]
    
    final_headers = ensure_csv_headers(output_file, all_pool_labels)
    
    # Prepare row data
    row_data = {
        "Timestamp": datetime.datetime.now().isoformat(),
        "Accounts": ";".join(accounts),
        "Total Value USD": f"{total_portfolio_usd:.2f}"
    }
    
    for p_val in pool_valuations:
        p_label = p_val["pool"]
        p_val_usd = p_val['value_usd']
        
        if p_label in row_data:
            try:
                current_val = float(row_data[p_label])
                row_data[p_label] = f"{current_val + p_val_usd:.2f}"
            except ValueError:
                row_data[p_label] = f"{p_val_usd:.2f}"
        else:
            row_data[p_label] = f"{p_val_usd:.2f}"
    
    with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        
        # Header if new file (or if we just created it but it's empty)
        if os.stat(output_file).st_size == 0:
            writer.writeheader()
            
        writer.writerow(row_data)
        print(f"Data saved to {output_file}")
        
    return total_portfolio_usd, pool_valuations

def main():
    settings = load_user_settings()
    accounts = settings.get("accounts", [])
    
    print(f"Starting Valuation Model at {datetime.datetime.now()}")
    print(f"Tracking Accounts: {', '.join(accounts)}")
    
    if not accounts:
        print("No accounts configured. Please check user_settings.json")
        return

    # --- OPTIMIZATION START ---
    # Fetch all account balances once
    print("--- Fetching All Account Balances (Batch) ---")
    user_balances = {}
    for acct_id in accounts:
        print(f"  Fetching balances for {acct_id}...")
        user_balances[acct_id] = get_all_account_balances(acct_id)
    # --- OPTIMIZATION END ---

    # Pre-fetch price if possible to ensure consistency across portfolios
    # We'll peek at the Core config for this
    print("\n--- Establishing Reference Price ---")
    
    prices = {"TWENTIX": None, "BTWTY.EOS": None, "BTWTY": None}
    
    try:
        with open("config_core.json", "r") as f:
            core_config = json.load(f)
            prices["TWENTIX"] = get_twentix_price_usd(core_config)
            prices["BTWTY.EOS"] = get_btwty_eos_price_usd(core_config)
    except:
        pass

    prices["BTWTY"] = get_btwty_price_usd()
        
    grand_total = Decimal(0)
    
    for p in PORTFOLIOS:
        val, _ = process_portfolio(p, prices, accounts, user_balances)
        if val:
            grand_total += val
            
    print("\n" + "=" * 60)
    print(f"GRAND TOTAL (ALL PORTFOLIOS): ${grand_total:,.2f}")
    print("=" * 60)

    # Save Grand Total to CSV
    total_history_file = "capital_history.csv"
    file_exists = os.path.isfile(total_history_file)
    
    with open(total_history_file, 'a', newline='') as f:
        fieldnames = ["Timestamp", "Total Value USD"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow({
            "Timestamp": datetime.datetime.now().isoformat(),
            "Total Value USD": f"{grand_total:.2f}"
        })
        print(f"Grand Total saved to {total_history_file}")

if __name__ == "__main__":
    main()
