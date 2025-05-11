import requests

def test_connection(url, name):
    print(f"🔗 Testing {name}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"✅ {name} OK | Status {response.status_code}")
    except Exception as e:
        print(f"❌ {name} FAILED: {e}")

# Bitcoin (Blockchain.com)
test_connection("https://blockchain.info/q/getreceivedbyaddress/1EzwoHtiXB4iFwedPr49iywjZn2nnekhoj", "Bitcoin")

# Ethereum (Etherscan)
test_connection("https://api.etherscan.io/api", "Ethereum")

# Dogecoin (Dogechain)
test_connection("https://dogechain.info/api/v1/address/balance/DBXu2kgc3xtvCUWFcxFE3r9hEYgmuaaCyD", "Dogecoin")

# Solana (Solana RPC via public node)
test_connection("https://api.mainnet-beta.solana.com", "Solana")
