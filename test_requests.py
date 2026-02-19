import ccxt
import requests
import json
import pandas as pd

def test_manual_request():
    url = "https://eapi.binance.com/eapi/v1/ticker"
    try:
        response = requests.get(url)
        data = response.json()
        print(f"Manual Request status: {response.status_code}")
        if response.status_code == 200:
            print(f"Items returned: {len(data)}")
            if len(data) > 0:
                print("First item sample:")
                print(json.dumps(data[0], indent=2))
        else:
            print(response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_manual_request()
