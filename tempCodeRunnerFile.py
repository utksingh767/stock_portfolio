import sqlite3
import requests
import json
import os
from datetime import datetime

class StockPortfolio:
    def __init__(self, db_name='portfolio.db'):
        self.db_name = db_name
        self.usd_to_inr_rate = None
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                quantity INTEGER NOT NULL,
                buy_price REAL NOT NULL,
                currency TEXT NOT NULL,
                date_added TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_usd_to_inr_rate(self):
        """Get current USD to INR exchange rate"""
        try:
            if self.usd_to_inr_rate is None:
                url = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                data = response.json()
                
                if 'chart' in data and data['chart']['result'] and len(data['chart']['result']) > 0:
                    result = data['chart']['result'][0]
                    self.usd_to_inr_rate = result['meta']['regularMarketPrice']
                else:
                    self.usd_to_inr_rate = 83.0  # Fallback rate
            
            return self.usd_to_inr_rate
        except Exception:
            return 83.0  # Fallback rate
    
    def detect_stock_type(self, symbol):
        """Detect if stock is Indian or International"""
        indian_suffixes = ['.NS', '.BO']
        
        # Check if already has Indian suffix
        if any(symbol.endswith(suffix) for suffix in indian_suffixes):
            return 'indian', symbol
        
        # List of common Indian stock symbols (without suffix)
        indian_stocks = [
            'TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'ITC', 'HINDUNILVR',
            'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'LT', 'ASIANPAINT', 'MARUTI', 'HCLTECH',
            'WIPRO', 'TECHM', 'TITAN', 'ULTRACEMCO', 'NESTLEIND', 'POWERGRID',
            'TATAMOTORS', 'M&M', 'ONGC', 'NTPC', 'COALINDIA', 'JSWSTEEL', 'TATASTEEL',
            'HINDALCO', 'BAJFINANCE', 'BAJAJFINSV', 'AXISBANK', 'SUNPHARMA', 'DRREDDY'
        ]
        
        if symbol.upper() in indian_stocks:
            return 'indian', f"{symbol}.NS"
        else:
            return 'international', symbol
    
    def get_stock_price(self, symbol):
        """Get current stock price using Yahoo Finance API (free) - supports both Indian and International stocks"""
        try:
            stock_type, api_symbol = self.detect_stock_type(symbol)
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{api_symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if 'chart' in data and data['chart']['result'] and len(data['chart']['result']) > 0:
                result = data['chart']['result'][0]
                if 'regularMarketPrice' in result['meta']:
                    current_price = result['meta']['regularMarketPrice']
                    currency = 'INR' if stock_type == 'indian' else 'USD'
                    return current_price, currency
                else:
                    return None, None
            else:
                return None, None
                
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None, None
    
    def get_company_name(self, symbol):
        """Get company name from Yahoo Finance - supports both Indian and International stocks"""
        try:
            stock_type, api_symbol = self.detect_stock_type(symbol)
                
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={api_symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if 'quotes' in data and len(data['quotes']) > 0:
                return data['quotes'][0].get('longname', symbol)
            else:
                return symbol
                
        except Exception:
            return symbol
    
    def add_stock(self, symbol, quantity, buy_price):
        """Add a stock to portfolio"""
        symbol = symbol.upper()
        stock_type, api_symbol = self.detect_stock_type(symbol)
        
        # Get company name from API
        company_name = self.get_company_name(symbol)
        
        # Determine currency
        currency = 'INR' if stock_type == 'indian' else 'USD'
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stocks (symbol, company_name, quantity, buy_price, currency, date_added)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, company_name, quantity, buy_price, currency, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        currency_symbol = '₹' if currency == 'INR' else '$'
        stock_flag = '🇮🇳' if stock_type == 'indian' else '🌍'
        print(f"✅ {stock_flag} Added {quantity} shares of {symbol} at {currency_symbol}{buy_price:.2f} each ({currency})")
    
    def view_portfolio(self):
        """Display current portfolio with live prices in both currencies"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM stocks ORDER BY date_added DESC')
        stocks = cursor.fetchall()
        conn.close()
        
        if not stocks:
            print("📈 Your portfolio is empty. Add some stocks first!")
            return
        
        # Get exchange rate
        usd_to_inr = self.get_usd_to_inr_rate()
        
        print("\n" + "="*95)
        print("📊 YOUR GLOBAL STOCK PORTFOLIO")
        print(f"💱 USD to INR Rate: {usd_to_inr:.2f}")
        print("="*95)
        print(f"{'Flag':<4} {'Symbol':<10} {'Company':<18} {'Qty':<5} {'Buy Price':<12} {'Current':<12} {'Value':<14} {'P&L':<14}")
        print("-"*95)
        
        total_invested_inr = 0
        total_current_inr = 0
        
        for stock in stocks:
            # Handle both old and new database schema
            if len(stock) == 6:  # Old schema without currency
                id, symbol, company, quantity, buy_price, date_added = stock
                stock_type, _ = self.detect_stock_type(symbol)
                currency = 'INR' if stock_type == 'indian' else 'USD'
            else:  # New schema with currency
                id, symbol, company, quantity, buy_price, currency, date_added = stock
            
            current_price, price_currency = self.get_stock_price(symbol)
            
            if current_price:
                # Convert everything to INR for total calculation
                if currency == 'USD':
                    invested_inr = quantity * buy_price * usd_to_inr
                    buy_price_display = f"${buy_price:.2f}"
                    flag = "🌍"
                else:
                    invested_inr = quantity * buy_price
                    buy_price_display = f"₹{buy_price:.2f}"
                    flag = "🇮🇳"
                
                if price_currency == 'USD':
                    current_value_inr = quantity * current_price * usd_to_inr
                    current_price_display = f"${current_price:.2f}"
                    value_display = f"₹{current_value_inr:,.2f}"
                else:
                    current_value_inr = quantity * current_price
                    current_price_display = f"₹{current_price:.2f}"
                    value_display = f"₹{current_value_inr:,.2f}"
                
                pnl_inr = current_value_inr - invested_inr
                pnl_percent = (pnl_inr / invested_inr) * 100
                
                total_invested_inr += invested_inr
                total_current_inr += current_value_inr
                
                # Color coding for P&L
                pnl_color = "🟢" if pnl_inr >= 0 else "🔴"
                
                print(f"{flag:<4} {symbol:<10} {company[:17]:<18} {quantity:<5} {buy_price_display:<12} {current_price_display:<12} {value_display:<14} {pnl_color}₹{pnl_inr:>11.2f}")
            else:
                flag = "🇮🇳" if currency == 'INR' else "🌍"
                currency_symbol = "₹" if currency == 'INR' else "$"
                print(f"{flag:<4} {symbol:<10} {company[:17]:<18} {quantity:<5} {currency_symbol}{buy_price:<11.2f} {'N/A':<12} {'N/A':<14} {'N/A':<14}")
        
        print("-"*95)
        total_pnl_inr = total_current_inr - total_invested_inr
        total_pnl_percent = (total_pnl_inr / total_invested_inr) * 100 if total_invested_inr > 0 else 0
        
        pnl_emoji = "🟢" if total_pnl_inr >= 0 else "🔴"
        
        print(f"💰 Total Invested: ₹{total_invested_inr:,.2f} (${total_invested_inr/usd_to_inr:,.2f})")
        print(f"📈 Current Value:  ₹{total_current_inr:,.2f} (${total_current_inr/usd_to_inr:,.2f})")
        print(f"{pnl_emoji} Total P&L:     ₹{total_pnl_inr:,.2f} ({total_pnl_percent:+.2f}%)")
        print("="*95)
    
    def delete_stock(self, stock_id):
        """Delete a stock from portfolio"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT symbol, company_name, quantity FROM stocks WHERE id = ?', (stock_id,))
        result = cursor.fetchone()
        
        if result:
            symbol, company, quantity = result
            cursor.execute('DELETE FROM stocks WHERE id = ?', (stock_id,))
            conn.commit()
            print(f"🗑️ Successfully deleted {quantity} shares of {symbol} ({company}) from portfolio")
        else:
            print("❌ Stock not found with that ID")
        
        conn.close()
    
    def list_stocks_with_ids(self):
        """List all stocks with their IDs for deletion"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM stocks ORDER BY id')
        stocks = cursor.fetchall()
        conn.close()
        
        if not stocks:
            print("📈 Your portfolio is empty.")
            return False
        
        print("\n📋 Your Stocks (for deletion):")
        print(f"{'ID':<4} {'Flag':<4} {'Symbol':<10} {'Company':<20} {'Quantity':<8} {'Buy Price':<12} {'Date Added':<12}")
        print("-"*75)
        
        for stock in stocks:
            # Handle both old and new database schema
            if len(stock) == 6:  # Old schema
                id, symbol, company, quantity, buy_price, date_added = stock
                stock_type, _ = self.detect_stock_type(symbol)
                currency = 'INR' if stock_type == 'indian' else 'USD'
            else:  # New schema
                id, symbol, company, quantity, buy_price, currency, date_added = stock
            
            flag = "🇮🇳" if currency == 'INR' else "🌍"
            currency_symbol = "₹" if currency == 'INR' else "$"
            date_short = date_added.split()[0] if ' ' in date_added else date_added[:10]
            print(f"{id:<4} {flag:<4} {symbol:<10} {company[:19]:<20} {quantity:<8} {currency_symbol}{buy_price:<11.2f} {date_short:<12}")
        
        return True
    
    def clear_all_data(self):
        """Delete all stocks from portfolio with confirmation"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Check if there are any stocks
        cursor.execute('SELECT COUNT(*) FROM stocks')
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📈 Your portfolio is already empty.")
            conn.close()
            return
        
        # Show summary of what will be deleted
        cursor.execute('SELECT symbol, company_name, quantity, currency FROM stocks ORDER BY symbol')
        stocks = cursor.fetchall()
        
        print(f"\n⚠️  WARNING: This will permanently delete all {count} stocks from your portfolio!")
        print("\n🗑️ The following stocks will be deleted:")
        print("-" * 60)
        
        inr_count = usd_count = 0
        for symbol, company, quantity, currency in stocks:
            flag = "🇮🇳" if currency == 'INR' else "🌍"
            print(f"  {flag} {symbol} ({company[:25]}) - {quantity} shares")
            if currency == 'INR':
                inr_count += 1
            else:
                usd_count += 1
        
        print("-" * 60)
        print(f"📊 Total: {inr_count} Indian stocks, {usd_count} International stocks")
        print("\n⚠️  This action cannot be undone!")
        
        confirmation = input("\nType 'DELETE ALL' (in caps) to confirm: ").strip()
        
        if confirmation == 'DELETE ALL':
            cursor.execute('DELETE FROM stocks')
            conn.commit()
            print(f"\n🗑️ Successfully deleted all {count} stocks from your portfolio!")
            print("💾 Your portfolio is now empty.")
        else:
            print("❌ Operation cancelled. No data was deleted.")
        
        conn.close()
    
    def delete_multiple_stocks(self):
        """Delete multiple stocks by ID"""
        if not self.list_stocks_with_ids():
            return
        
        print("\n🗑️ Delete Multiple Stocks")
        print("Enter stock IDs to delete (comma-separated, e.g., 1,3,5)")
        print("Or type 'cancel' to go back")
        
        ids_input = input("\nEnter IDs: ").strip()
        
        if ids_input.lower() == 'cancel':
            print("❌ Operation cancelled.")
            return
        
        try:
            # Parse and validate IDs
            stock_ids = [int(id.strip()) for id in ids_input.split(',') if id.strip()]
            
            if not stock_ids:
                print("❌ No valid IDs entered.")
                return
            
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Get details of stocks to be deleted
            placeholders = ','.join(['?' for _ in stock_ids])
            cursor.execute(f'SELECT id, symbol, company_name, quantity FROM stocks WHERE id IN ({placeholders})', stock_ids)
            stocks_to_delete = cursor.fetchall()
            
            if not stocks_to_delete:
                print("❌ No stocks found with the provided IDs.")
                conn.close()
                return
            
            print(f"\n📋 Found {len(stocks_to_delete)} stock(s) to delete:")
            for id, symbol, company, quantity in stocks_to_delete:
                print(f"  • ID {id}: {symbol} ({company}) - {quantity} shares")
            
            confirm = input(f"\nConfirm deletion of {len(stocks_to_delete)} stock(s)? (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                # Delete the stocks
                cursor.execute(f'DELETE FROM stocks WHERE id IN ({placeholders})', stock_ids)
                deleted_count = cursor.rowcount
                conn.commit()
                print(f"🗑️ Successfully deleted {deleted_count} stock(s) from portfolio!")
            else:
                print("❌ Deletion cancelled.")
            
            conn.close()
            
        except ValueError:
            print("❌ Please enter valid numeric IDs separated by commas.")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def get_portfolio_stats(self):
        """Get portfolio statistics"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), currency FROM stocks GROUP BY currency')
        stats = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM stocks')
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return stats, total_count

def main():
    portfolio = StockPortfolio()
    
    while True:
        print("\n🌍 GLOBAL STOCK PORTFOLIO TRACKER")
        print("1. 📊 View Portfolio")
        print("2. ➕ Add Stock (Indian/International)")
        print("3. 🗑️ Delete Single Stock")
        print("4. 🗑️ Delete Multiple Stocks")
        print("5. 🧹 Clear All Data")
        print("6. 📈 Portfolio Stats")
        print("7. 🚪 Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            portfolio.view_portfolio()
        
        elif choice == '2':
            try:
                print("\n📈 Add New Stock:")
                print("🇮🇳 Indian stocks: TCS, INFY, RELIANCE, HDFCBANK, ITC")
                print("🌍 International: AAPL, GOOGL, TSLA, MSFT, NVDA")
                
                symbol = input("\nEnter stock symbol: ").strip().upper()
                if not symbol:
                    print("❌ Please enter a valid symbol")
                    continue
                
                stock_type, _ = portfolio.detect_stock_type(symbol)
                currency = 'INR' if stock_type == 'indian' else 'USD'
                currency_symbol = '₹' if currency == 'INR' else '$'
                flag = '🇮🇳' if stock_type == 'indian' else '🌍'
                
                print(f"{flag} Detected as {stock_type.title()} stock ({currency})")
                
                quantity = int(input("Enter quantity: "))
                buy_price = float(input(f"Enter buy price per share: {currency_symbol}"))
                
                portfolio.add_stock(symbol, quantity, buy_price)
                
            except ValueError:
                print("❌ Please enter valid numbers for quantity and price")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == '3':
            if portfolio.list_stocks_with_ids():
                try:
                    stock_id = int(input("\nEnter ID of stock to delete: "))
                    portfolio.delete_stock(stock_id)
                except ValueError:
                    print("❌ Please enter a valid ID number")
        
        elif choice == '4':
            portfolio.delete_multiple_stocks()
        
        elif choice == '5':
            portfolio.clear_all_data()
        
        elif choice == '6':
            stats, total_count = portfolio.get_portfolio_stats()
            
            print(f"\n📊 Portfolio Statistics:")
            print("-" * 30)
            
            if total_count == 0:
                print("📈 Portfolio is empty")
            else:
                print(f"📈 Total Stocks: {total_count}")
                for count, currency in stats:
                    flag = "🇮🇳" if currency == 'INR' else "🌍"
                    print(f"  {flag} {currency} stocks: {count}")
        
        elif choice == '7':
            print("👋 Thanks for using Global Stock Portfolio Tracker!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-7.")

if __name__ == "__main__":
    main()