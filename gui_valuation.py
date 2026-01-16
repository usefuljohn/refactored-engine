import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
from decimal import Decimal
import valuation
from valuation import get_asset_supply
from pool_data_handler import resolve_account_name, get_all_account_balances, get_pool_data, get_account_balance

class PortfolioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BitShares Portfolio Valuation")
        self.root.geometry("800x650") # Slightly taller
        
        self.gold_price = Decimal(0)

        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # --- Settings Frame ---
        settings_frame = ttk.LabelFrame(root, text="Account Configuration", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Account Names (comma separated):").pack(side=tk.LEFT)
        
        self.account_entry = ttk.Entry(settings_frame)
        self.account_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.save_btn = ttk.Button(settings_frame, text="Save & Scan", command=self.save_accounts)
        self.save_btn.pack(side=tk.LEFT)
        
        # Load initial settings into Entry
        self.current_settings = self.load_settings()
        initial_names = ", ".join(self.current_settings.get("account_names", []))
        self.account_entry.insert(0, initial_names)
        
        # --- Header ---
        header_frame = ttk.Frame(root, padding="10")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, text="Liquidity Pool Portfolio", font=("Helvetica", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(header_frame, text="Refresh Data", command=self.start_refresh)
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # --- XAUT TVL (Pot of Gold) ---
        tvl_frame = ttk.Frame(root, padding="5")
        tvl_frame.pack(fill=tk.X, padx=10)
        
        # 1. Gold Price Section
        frame_pool = ttk.Frame(tvl_frame)
        frame_pool.pack(side=tk.LEFT, padx=10)
        
        canvas_pool = tk.Canvas(frame_pool, width=50, height=50, highlightthickness=0)
        canvas_pool.pack(side=tk.LEFT)
        self.draw_pot_of_gold(canvas_pool)
        
        lbl_pool_frame = ttk.Frame(frame_pool)
        lbl_pool_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(lbl_pool_frame, text="Gold Price (USD/oz)", font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.tvl_value_label = ttk.Label(lbl_pool_frame, text="Fetching...", font=("Helvetica", 11), foreground="darkgreen")
        self.tvl_value_label.pack(anchor=tk.W)

        # Separator
        ttk.Separator(tvl_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=20)

        # 2. Grand Total Gold Visualization
        frame_user = ttk.Frame(tvl_frame)
        frame_user.pack(side=tk.LEFT, padx=10)

        # Wider canvas for stacking gold
        self.gold_canvas = tk.Canvas(frame_user, width=300, height=80, highlightthickness=0)
        self.gold_canvas.pack(side=tk.LEFT)
        
        lbl_user_frame = ttk.Frame(frame_user)
        lbl_user_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(lbl_user_frame, text="Grand Total (USD)", font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.user_share_label = ttk.Label(lbl_user_frame, text="Wait for Scan...", font=("Helvetica", 11), foreground="blue")
        self.user_share_label.pack(anchor=tk.W)
        
        # Start Gold Price Fetch
        threading.Thread(target=self.fetch_gold_price, daemon=True).start()

        # --- Tabs ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        # USD Tab
        self.usd_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.usd_frame, text="USD Portfolio")
        self.usd_tree = self.create_treeview(self.usd_frame)
        
        # TWENTIX Tab
        self.growth_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.growth_frame, text="TWENTIX Portfolio")
        self.growth_tree = self.create_treeview(self.growth_frame)

        # BTWTY.EOS Tab
        self.btwty_eos_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.btwty_eos_frame, text="BTWTY.EOS Portfolio")
        self.btwty_eos_tree = self.create_treeview(self.btwty_eos_frame)
        
        # BTS Tab
        self.bts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bts_frame, text="BTS Portfolio")
        self.bts_tree = self.create_treeview(self.bts_frame)

        # --- Footer ---
        footer_frame = ttk.Frame(root, padding="10")
        footer_frame.pack(fill=tk.X)
        
        self.usd_total_label = ttk.Label(footer_frame, text="USD Total: $0.00", font=("Helvetica", 10))
        self.usd_total_label.pack(anchor=tk.W)
        
        self.growth_total_label = ttk.Label(footer_frame, text="TWENTIX Total: $0.00", font=("Helvetica", 10))
        self.growth_total_label.pack(anchor=tk.W)

        self.btwty_eos_total_label = ttk.Label(footer_frame, text="BTWTY.EOS Total: $0.00", font=("Helvetica", 10))
        self.btwty_eos_total_label.pack(anchor=tk.W)
        
        self.bts_total_label = ttk.Label(footer_frame, text="BTS Total: $0.00", font=("Helvetica", 10))
        self.bts_total_label.pack(anchor=tk.W)
        
        ttk.Separator(footer_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        self.grand_total_label = ttk.Label(footer_frame, text="GRAND TOTAL: $0.00", font=("Helvetica", 14, "bold"))
        self.grand_total_label.pack(anchor=tk.E)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def draw_pot_of_gold(self, canvas):
        canvas.create_arc(5, 20, 45, 45, start=180, extent=180, fill="#333", outline="black")
        canvas.create_line(5, 20, 45, 20, fill="black", width=2)
        canvas.create_oval(10, 15, 20, 25, fill="gold", outline="goldenrod")
        canvas.create_oval(20, 12, 30, 22, fill="gold", outline="goldenrod")
        canvas.create_oval(30, 15, 40, 25, fill="gold", outline="goldenrod")
        canvas.create_oval(15, 20, 25, 30, fill="gold", outline="goldenrod")
        canvas.create_oval(25, 20, 35, 30, fill="gold", outline="goldenrod")

    def fetch_gold_price(self):
        try:
            pool_id = "1.19.473" # XAUT/USDT
            pool_data = get_pool_data(pool_id)
            
            if not pool_data:
                 self.root.after(0, lambda: self.update_gold_price_label("Error"))
                 return

            # Calculate Gold Price (USD per XAUT)
            id_usdt = "1.3.5589"
            id_xaut = "1.3.6139" # From our check
            
            balance_usdt = Decimal(0)
            balance_xaut = Decimal(0)
            
            prec_usdt = 6
            prec_xaut = 6
            
            if pool_data.get("asset_a") == id_usdt:
                balance_usdt = Decimal(pool_data["balance_a"])
                balance_xaut = Decimal(pool_data["balance_b"])
            elif pool_data.get("asset_b") == id_usdt:
                balance_usdt = Decimal(pool_data["balance_b"])
                balance_xaut = Decimal(pool_data["balance_a"])
            
            real_usdt = balance_usdt / Decimal(10**prec_usdt)
            real_xaut = balance_xaut / Decimal(10**prec_xaut)
            
            price = Decimal(0)
            if real_xaut > 0:
                price = real_usdt / real_xaut
            
            self.gold_price = price
            self.root.after(0, lambda: self.update_gold_price_label(f"${price:,.2f}"))

        except Exception as e:
            print(f"Gold Price Error: {e}")
            self.root.after(0, lambda: self.update_gold_price_label("Error"))

    def update_gold_price_label(self, price_text):
        self.tvl_value_label.config(text=price_text)

    def draw_gold_stacks(self, canvas, ounces):
        canvas.delete("all")
        
        # Limit ounces to avoid crash if something is wrong
        count = int(ounces)
        if count <= 0:
            return
        if count > 500: # Cap visual at 500
            count = 500
            
        # Draw "Gold Bars" or "Coins"
        # Let's do small gold rectangles
        
        bar_w = 10
        bar_h = 5
        spacing_x = 2
        spacing_y = 2
        
        # Grid parameters
        start_x = 5
        start_y = 75 # Start from bottom? No, canvas height is 80.
        
        # Let's stack them from bottom left
        # We have height 80. 
        # Max bars vertically = 80 / (5+2) = ~11
        
        rows = 10
        cols = 0
        
        for i in range(count):
            col = i // rows
            row = i % rows
            
            x1 = start_x + (col * (bar_w + spacing_x))
            y1 = 70 - (row * (bar_h + spacing_y)) # 70 is base y
            
            x2 = x1 + bar_w
            y2 = y1 + bar_h
            
            # Simple Gold Bar
            canvas.create_rectangle(x1, y1, x2, y2, fill="gold", outline="#B8860B")


    def load_settings(self):
        settings_file = "user_settings.json"
        defaults = {"accounts": [], "account_names": []}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return defaults

    def save_accounts(self):
        raw_text = self.account_entry.get()
        names = [n.strip() for n in raw_text.split(",") if n.strip()]
        
        if not names:
            messagebox.showwarning("Input Error", "Please enter at least one account name.")
            return

        self.save_btn.config(state=tk.DISABLED)
        self.status_var.set("Resolving account names...")
        
        threading.Thread(target=self._resolve_and_save, args=(names,), daemon=True).start()

    def _resolve_and_save(self, names):
        resolved_ids = []
        valid_names = []
        failed_names = []

        for name in names:
            # Simple caching check could go here, but RPC is fast enough usually
            aid = resolve_account_name(name)
            if aid:
                resolved_ids.append(aid)
                valid_names.append(name)
            else:
                failed_names.append(name)
        
        if failed_names:
            msg = f"Could not find accounts: {', '.join(failed_names)}\nProceeding with valid ones."
            self.root.after(0, lambda: messagebox.showwarning("Account Lookup", msg))
        
        if not resolved_ids:
            self.root.after(0, lambda: self.finish_save([], [], "No valid accounts found."))
            return

        # Save to file
        settings = {
            "accounts": resolved_ids,
            "account_names": valid_names
        }
        
        try:
            with open("user_settings.json", "w") as f:
                json.dump(settings, f, indent=4)
            self.current_settings = settings
            self.root.after(0, lambda: self.finish_save(valid_names, resolved_ids, "Settings saved. Scanning..."))
        except Exception as e:
            msg = f"Error saving settings: {e}"
            self.root.after(0, lambda: self.finish_save([], [], msg))

    def finish_save(self, valid_names, ids, status_msg):
        self.save_btn.config(state=tk.NORMAL)
        self.status_var.set(status_msg)
        
        # Update entry with valid names only to keep it clean
        if valid_names:
             self.account_entry.delete(0, tk.END)
             self.account_entry.insert(0, ", ".join(valid_names))
             # Trigger refresh immediately
             self.start_refresh()

    def create_treeview(self, parent):
        cols = ("Pool", "Share %", "Pool TVL", "Your Value")
        tree = ttk.Treeview(parent, columns=cols, show='headings')
        
        for col in cols:
            tree.heading(col, text=col, command=lambda _col=col: self.treeview_sort_column(tree, _col, False))
            tree.column(col, width=150)
            
        tree.column("Pool", width=200)
        tree.column("Share %", width=100, anchor=tk.CENTER)
        tree.column("Pool TVL", width=150, anchor=tk.E)
        tree.column("Your Value", width=150, anchor=tk.E)
        
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return tree

    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        try:
            # Clean data for sorting (remove $, %, ,)
            def clean_val(val):
                v = val.replace('$', '').replace('%', '').replace(',', '').strip()
                return float(v) if v else 0.0
            
            l.sort(key=lambda t: clean_val(t[0]), reverse=reverse)
        except ValueError:
            # Fallback to string sort
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # Reverse sort next time
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def start_refresh(self):
        self.refresh_btn.config(state=tk.DISABLED)
        self.status_var.set("Fetching data from BitShares blockchain...")
        
        # Clear existing data
        for row in self.usd_tree.get_children():
            self.usd_tree.delete(row)
        for row in self.growth_tree.get_children():
            self.growth_tree.delete(row)
        for row in self.btwty_eos_tree.get_children():
            self.btwty_eos_tree.delete(row)
        for row in self.bts_tree.get_children():
            self.bts_tree.delete(row)
            
        thread = threading.Thread(target=self.run_valuation)
        thread.daemon = True
        thread.start()

    def run_valuation(self):
        try:
            # Re-use logic from valuation.py
            
            # Get Accounts from settings
            accounts = self.current_settings.get("accounts", [])
            if not accounts:
                 self.root.after(0, lambda: self.finish_refresh("No accounts configured."))
                 return

            # 0. Fetch Balances
            user_balances = {}
            for acct_id in accounts:
                user_balances[acct_id] = get_all_account_balances(acct_id)

            # 1. Get Prices
            prices = {"TWENTIX": None, "BTWTY.EOS": None, "BTWTY": None}
            try:
                with open("config_core.json", "r") as f:
                    core_config = json.load(f)
                    prices["TWENTIX"] = valuation.get_twentix_price_usd(core_config)
                    prices["BTWTY.EOS"] = valuation.get_btwty_eos_price_usd(core_config)
            except Exception as e:
                print(f"Config error: {e}")

            # Fetch BTWTY Price
            try:
                prices["BTWTY"] = valuation.get_btwty_price_usd()
            except Exception as e:
                print(f"BTWTY Price error: {e}")
                
            grand_total = Decimal(0)
            usd_total = Decimal(0)
            growth_total = Decimal(0)
            btwty_eos_total = Decimal(0)
            bts_total = Decimal(0)

            # Fetch BTS Price
            try:
                with open("config_bts.json", "r") as f:
                    bts_config = json.load(f)
                    prices["BTS"] = valuation.get_bts_price_usd(bts_config)
            except Exception as e:
                print(f"BTS Price error: {e}")
            
            # 2. Process Portfolios
            for p in valuation.PORTFOLIOS:
                # p is {"name": "USD", ...}
                total_val, details = valuation.process_portfolio(p, prices, accounts, user_balances)
                
                if total_val:
                    grand_total += total_val
                    
                    if p["name"] == "USD":
                        usd_total = total_val
                        self.update_tree(self.usd_tree, details)
                    elif p["name"] == "TWENTIX":
                        growth_total = total_val
                        self.update_tree(self.growth_tree, details)
                    elif p["name"] == "BTWTY.EOS":
                        btwty_eos_total = total_val
                        self.update_tree(self.btwty_eos_tree, details)
                    elif p["name"] == "BTS Portfolio":
                        bts_total = total_val
                        self.update_tree(self.bts_tree, details)
            
            # 3. Update UI Labels
            self.root.after(0, lambda: self.update_labels(usd_total, growth_total, btwty_eos_total, bts_total, grand_total))
            self.root.after(0, lambda: self.finish_refresh("Data Updated Successfully"))
            
        except Exception as e:
            msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.finish_refresh(msg))

    def update_tree(self, tree, data):
        # Schedule the UI update on the main thread
        def _update():
            for item in data:
                tree.insert("", tk.END, values=(
                    item["pool"],
                    f"{item['share_percent']:.4f}%",
                    f"${Decimal(item['value_usd']) / (Decimal(item['share_percent'])/100) if item['share_percent'] > 0 else 0:,.2f}", # Reverse calc TVL or pass it? 
                    # Actually details doesn't pass TVL directly, let's just use the value
                    f"${item['value_usd']:,.2f}"
                ))
        self.root.after(0, _update)

    def update_labels(self, usd, growth, btwty_eos, bts, grand):
        self.usd_total_label.config(text=f"USD Total: ${usd:,.2f}")
        self.growth_total_label.config(text=f"TWENTIX Total: ${growth:,.2f}")
        self.btwty_eos_total_label.config(text=f"BTWTY.EOS Total: ${btwty_eos:,.2f}")
        self.bts_total_label.config(text=f"BTS Total: ${bts:,.2f}")
        self.grand_total_label.config(text=f"GRAND TOTAL: ${grand:,.2f}")
        
        # Update Gold Viz Label
        self.user_share_label.config(text=f"${grand:,.2f}")
        
        # Calculate Ounces
        ounces = 0
        if self.gold_price > 0:
            ounces = grand / self.gold_price
            
        self.draw_gold_stacks(self.gold_canvas, ounces)

    def finish_refresh(self, message):
        self.status_var.set(message)
        self.refresh_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = PortfolioGUI(root)
    root.mainloop()
