import json
import requests
import uuid
import time
import os
from solders.keypair import Keypair
from base58 import b58encode
from itertools import cycle

# === Konfigurasi ===
SOLANA_WALLETS_FILE = "solana_wallets.json"
LOG_FILE = "logs.txt"
SOLANA_RPC_URL = "https://api.devnet.solana.com"
CIRCLE_FAUCET_URL = "https://faucet.circle.com/api/graphql"
USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
PROXY_FILE = "proxies_valid.txt"

# === Proxy ===
def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE) as f:
        return [line.strip() for line in f if line.strip()]

proxies_list = load_proxies()
proxy_pool = cycle(proxies_list) if proxies_list else None

def get_proxy():
    if not proxy_pool:
        return None
    proxy = next(proxy_pool)
    return {
        "http": proxy,
        "https": proxy,
    }

# === Utilitas ===
def log(text):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.ctime()} - {text}\n")
    print(text)

def load_wallets():
    if not os.path.exists(SOLANA_WALLETS_FILE):
        return []
    with open(SOLANA_WALLETS_FILE) as f:
        return json.load(f)

def save_wallets(wallets):
    with open(SOLANA_WALLETS_FILE, "w") as f:
        json.dump(wallets, f, indent=2)

def get_sol_balance(public_key):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [public_key]
    }
    try:
        res = requests.post(SOLANA_RPC_URL, json=payload, proxies=get_proxy(), timeout=10)
        return res.json()["result"]["value"]
    except:
        return 0

def get_usdc_balance(public_key):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            public_key,
            {"mint": USDC_MINT},
            {"encoding": "jsonParsed"}
        ]
    }
    try:
        res = requests.post(SOLANA_RPC_URL, json=payload, proxies=get_proxy(), timeout=10)
        data = res.json()
        accounts = data.get("result", {}).get("value", [])
        if not accounts:
            return 0
        amount = int(accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
        return amount
    except:
        return 0

# === 1. Generate Wallet ===
def generate_wallets(n):
    wallets = []
    for _ in range(n):
        kp = Keypair()
        wallets.append({
            "public_key": str(kp.pubkey()),
            "private_key": list(kp.to_bytes()),
            "sol_claimed": False,
            "usdc_claimed": False
        })
    save_wallets(wallets)
    log(f"✅ {n} wallet Solana berhasil dibuat.")

# === 2. Claim Faucet SOL Devnet ===
def claim_sol(public_key):
    while True:
        balance = get_sol_balance(public_key)
        if balance > 100_000_000:  # > 0.1 SOL
            log(f"⏭️ Skip SOL: {public_key} (balance > 0.1)")
            return True

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "requestAirdrop",
            "params": [public_key, 1000000000]
        }
        try:
            res = requests.post(SOLANA_RPC_URL, json=payload, proxies=get_proxy(), timeout=10)
            result = res.json()
            if "result" in result:
                log(f"✅ SOL Claimed: {public_key}")
                return True
            else:
                log(f"🔁 Retry SOL: {public_key} (balance = {balance})")
                time.sleep(2)
        except Exception as e:
            log(f"❌ Error klaim SOL: {public_key} - {e}")
            time.sleep(2)

# === 3. Claim Faucet USDC Circle ===
def claim_usdc(public_key):
    while True:
        payload = {
            "operationName": "RequestToken",
            "variables": {
                "input": {
                    "destinationAddress": public_key,
                    "token": "USDC",
                    "blockchain": "SOL"
                }
            },
            "query": """
            mutation RequestToken($input: RequestTokenInput!) {
              requestToken(input: $input) {
                status
              }
            }
            """
        }
        try:
            res = requests.post(CIRCLE_FAUCET_URL, json=payload, proxies=get_proxy(), timeout=10)
            status = res.json()["data"]["requestToken"]["status"]
            log(f"✅ USDC Claimed ({status}): {public_key}")
            return True
        except Exception as e:
            usdc_balance = get_usdc_balance(public_key)
            log(f"🔁 Retry USDC: {public_key} (balance = {usdc_balance}) - {e}")
            time.sleep(3)

# === 4. Placeholder Kirim USDC ===
def send_usdc_placeholder(public_key, target_wallet):
    log(f"[PLACEHOLDER] Kirim USDC dari {public_key} ke {target_wallet}")

# === Menu CLI ===
def menu():
    while True:
        print("\n=== Solana Faucet Bot ===")
        print("1. Generate Wallets")
        print("2. Claim SOL Devnet Faucet")
        print("3. Claim USDC Faucet (Circle)")
        print("4. Claim USDC + Send to Target Wallet")
        print("5. Keluar")
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            jumlah = int(input("Jumlah wallet: "))
            generate_wallets(jumlah)

        elif choice == "2":
            wallets = load_wallets()
            for w in wallets:
                success = claim_sol(w["public_key"])
                if success:
                    w["sol_claimed"] = True
                    save_wallets(wallets)
                time.sleep(2)

        elif choice == "3":
            wallets = load_wallets()
            for w in wallets:
                success = claim_usdc(w["public_key"])
                if success:
                    w["usdc_claimed"] = True
                    save_wallets(wallets)
                time.sleep(5)

        elif choice == "4":
            target_wallet = input("Masukkan wallet tujuan (USDC): ")
            wallets = load_wallets()
            for w in wallets:
                success_sol = claim_sol(w["public_key"])
                if success_sol:
                    w["sol_claimed"] = True
                    save_wallets(wallets)
                time.sleep(2)

                success_usdc = claim_usdc(w["public_key"])
                if success_usdc:
                    w["usdc_claimed"] = True
                    save_wallets(wallets)
                time.sleep(2)

                send_usdc_placeholder(w["public_key"], target_wallet)
                time.sleep(5)

        elif choice == "5":
            break

        else:
            print("Pilihan tidak valid. Ulangi.")

menu()
