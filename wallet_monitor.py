import requests
from send_telegram import send_telegram_message

# Wallet addresses to monitor (multiple per coin)
wallets = {
    "Bitcoin": [
        {
            "address": "bc1ql49ydapnjafl5t2cp9zqpjwe6pdgmxy98859v2",
            "label": "Robinhood Cold Wallet",
            "threshold": 0.10
        },
        {
            "address": "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
            "label": "Bitfinex Cold Wallet",
            "threshold": 1.0
        }
    ],
    "Ethereum": [
        {
            "address": "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
            "label": "Vitalik’s Wallet",
            "threshold": 10
        },
        {
            "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "label": "Binance ETH Reserve",
            "threshold": 50
        }
    ],
    "Solana": [
        {
            "address": "4eD1xXy8ry9fwjyzSRRDCvQ9hBqD4doK6sWWCxt1TxGv",
            "label": "Example SOL Wallet",
            "threshold": 100
        }
    ],
    "Dogecoin": [
        {
            "address": "DBXu2kgc3xtvCUWFcxFE3r9hEYgmuaaCyD",
            "label": "Dogecoin Whale #1",
            "threshold": 50000
        }
    ]
}


def get_bitcoin_balance(address):
    url = f"https://blockchain.info/q/addressbalance/{address}"
    response = requests.get(url)
    response.raise_for_status()
    return int(response.text) / 1e8  # Convert from satoshis


def get_ethereum_balance(address):
    url = f"https://api.ethplorer.io/getAddressInfo/{address}?apiKey=freekey"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data["ETH"]["balance"]


def get_solana_balance(address):
    url = "https://api.mainnet-beta.solana.com"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["result"]["value"] / 1e9


def get_dogecoin_balance(address):
    url = f"https://dogechain.info/api/v1/address/balance/{address}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return float(data["balance"])


def check_wallets():
    print("\n\U0001F50D Checking wallet balances...")

    for coin, wallet_list in wallets.items():
        for info in wallet_list:
            label = info.get("label", "Unlabeled")
            try:
                if coin == "Bitcoin":
                    balance = get_bitcoin_balance(info["address"])
                elif coin == "Ethereum":
                    balance = get_ethereum_balance(info["address"])
                elif coin == "Solana":
                    balance = get_solana_balance(info["address"])
                elif coin == "Dogecoin":
                    balance = get_dogecoin_balance(info["address"])
                else:
                    print(f"❌ Unsupported coin: {coin}")
                    continue

                print(f"{coin} | {label}: {balance:.4f}")

                if balance >= info["threshold"]:
                    alert = f"🚨 {coin} wallet '{label}' balance crossed threshold!\nBalance: {balance:.4f} >= {info['threshold']}"
                    send_telegram_message(alert)

            except Exception as e:
                print(f"⚠️ Could not retrieve {coin} ({label}) balance: {e}")


if __name__ == "__main__":
    check_wallets()
