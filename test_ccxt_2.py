import ccxt
import json

def test_config(config_name, options):
    print(f"\nTesting config: {config_name}")
    try:
        exchange = ccxt.binance(options)
        markets = exchange.load_markets()
        print(f"Loaded {len(markets)} markets")
        
        option_count = 0
        for s, m in markets.items():
            if m.get('option') or m.get('type') == 'option':
                option_count += 1
                if option_count == 1:
                    print("Sample Option Market:")
                    print(json.dumps(m, indent=2, default=str))
        
        print(f"Total Option Markets found: {option_count}")
        return option_count > 0
    except Exception as e:
        print(f"Error: {e}")
        return False

configs = [
    ("Default (Spot)", {}),
    ("Future", {'options': {'defaultType': 'future'}}),
    ("Delivery", {'options': {'defaultType': 'delivery'}}),
    ("Option", {'options': {'defaultType': 'option'}}), # This is the standard ccxt way for options
]

for name, opts in configs:
    if test_config(name, opts):
        break
