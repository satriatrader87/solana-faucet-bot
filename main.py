import json
import requests
import uuid
import time
import os
import threading
from solders.keypair import Keypair
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
        accounts = res.json().get("result", {}).get("value", [])
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

# === 2. Claim SOL ===
def claim_sol_thread(w):
    while True:
        balance = get_sol_balance(w["public_key"])
        if balance > 100_000_000:
            log(f"⏭️ Skip SOL: {w['public_key']} (balance > 0.1)")
            return

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "requestAirdrop",
            "params": [w["public_key"], 1000000000]
        }

        try:
            requests.post(SOLANA_RPC_URL, json=payload, proxies=get_proxy(), timeout=10)
            log(f"🔁 Retry or success SOL: {w['public_key']}")
        except Exception as e:
            log(f"❌ Error klaim SOL: {w['public_key']} - {e}")
        time.sleep(5)

# === 3. Claim USDC ===
def claim_usdc_thread(w):
    while True:
        balance = get_usdc_balance(w["public_key"])
        if balance > 0:
            log(f"✅ USDC Claimed: {w['public_key']} (balance: {balance})")
            return

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }

        payload = {
            "operationName": "RequestToken",
            "variables": {
                "input": {
                    "destinationAddress": w["public_key"],
                    "token": "USDC",
                    "blockchain": "SOL"
                }
            },
            "query": """mutation RequestToken($input: RequestTokenInput!) {
              requestToken(input: $input) {
                amount
                blockchain
                contractAddress
                currency
                destinationAddress
                explorerLink
                hash
                status
                __typename
              }
            }"""
        }

        try:
            res = requests.post(CIRCLE_FAUCET_URL, json=payload, headers=headers, proxies=get_proxy(), timeout=10)
            data = res.json()
            status = data.get("data", {}).get("requestToken", {}).get("status")

            if status == "CONFIRMED":
                log(f"✅ USDC Claimed (confirmed): {w['public_key']}")
                return
            else:
                log(f"🔁 Retry USDC: {w['public_key']}")
                time.sleep(5)

        except Exception as e:
            log(f"❌ Error klaim USDC: {w['public_key']} - {e}")
            time.sleep(5)

# === 4. Placeholder Kirim USDC ===
def send_usdc_placeholder(from_wallet, to_wallet):
    log(f"[PLACEHOLDER] Kirim USDC dari {from_wallet} ke {to_wallet}")

# === Menu CLI ===
def menu():
    while True:
        print("\n=== Solana Faucet Bot ===")
        print("1. Generate Wallets")
        print("2. Claim SOL Faucet (Multithreaded)")
        print("3. Claim USDC Faucet (Multithreaded)")
        print("4. Kirim USDC ke Wallet Tujuan (Placeholder)")
        print("5. Keluar")
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            jumlah = int(input("Jumlah wallet: "))
            generate_wallets(jumlah)

        elif choice == "2":
            wallets = load_wallets()
            threads = []
            for w in wallets:
                t = threading.Thread(target=claim_sol_thread, args=(w,))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        elif choice == "3":
            wallets = load_wallets()
            threads = []
            for w in wallets:
                t = threading.Thread(target=claim_usdc_thread, args=(w,))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        elif choice == "4":
            to_wallet = input("Masukkan wallet tujuan (USDC): ")
            wallets = load_wallets()
            for w in wallets:
                send_usdc_placeholder(w["public_key"], to_wallet)

        elif choice == "5":
            break

        else:
            print("Pilihan tidak valid. Ulangi.")

if __name__ == "__main__":
    menu()
