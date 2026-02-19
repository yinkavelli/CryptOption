import ccxt
import json

def inspect_binance_options():
    exchange = ccxt.binance({
        'options': {'defaultType': 'option'} # Options are often under future/delivery endpoints
        # 'options': {'defaultType': 'option'} might be better if supported directly
    })
    
    try:
        # Load markets
        print("Loading markets...")
        markets = exchange.load_markets()
        
        # Find the first option market
        option_market = None
        for symbol, market in markets.items():
            if market.get('option'): # Check if it's explicitly marked as option
                option_market = market
                print(f"Found option market: {symbol}")
                break
            # Fallback check
            if 'info' in market and 'e' in market['info'] and 'O' in market['info'].get('s', ''):
                 # Heuristic for some older API versions or raw info check
                 pass

        if option_market:
            print(json.dumps(option_market, indent=2, use_decimal=True, default=str))
        else:
            print("No option markets found with default config.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_binance_options()
