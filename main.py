
import json
import requests
import uuid
import time
import os
from solana.keypair import Keypair
from solana.publickey import PublicKey
from base58 import b58encode

# === Konfigurasi ===
SOLANA_WALLETS_FILE = "solana_wallets.json"
LOG_FILE = "logs.txt"
SOLANA_RPC_URL = "https://api.devnet.solana.com"
CIRCLE_FAUCET_URL = "https://faucet.circle.com/api/graphql"
USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"


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


# === 1. Generate Wallet ===

def generate_wallets(n):
    wallets = []
    for _ in range(n):
        kp = Keypair()
        wallets.append({
            "public_key": str(kp.public_key),
            "private_key": list(kp.secret_key),
            "sol_claimed": False
        })
    save_wallets(wallets)
    log(f"✅ {n} wallet Solana berhasil dibuat.")


# === 2. Claim Faucet SOL Devnet ===

def claim_sol(public_key):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "requestAirdrop",
        "params": [public_key, 1000000000]  # 1 SOL
    }
    try:
        res = requests.post(SOLANA_RPC_URL, json=payload)
        result = res.json()
        if "result" in result:
            log(f"✅ SOL Claimed: {public_key}")
            return True
        else:
            log(f"❌ Gagal klaim SOL: {public_key} - {result}")
            return False
    except Exception as e:
        log(f"❌ Error klaim SOL: {public_key} - {e}")
        return False


# === 3. Claim Faucet USDC Circle ===

def claim_usdc(public_key):
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
        }
        """
    }
    try:
        res = requests.post(CIRCLE_FAUCET_URL, json=payload)
        data = res.json()
        status = data["data"]["requestToken"]["status"]
        log(f"✅ USDC Claimed ({status}): {public_key}")
        return True
    except Exception as e:
        log(f"❌ Error klaim USDC: {public_key} - {e}")
        return False


# === 4. (Placeholder) Send USDC ===
# (Akan diimplementasi penuh jika diminta)

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
                if not w.get("sol_claimed", False):
                    success = claim_sol(w["public_key"])
                    if success:
                        w["sol_claimed"] = True
                        save_wallets(wallets)
                    time.sleep(2)

        elif choice == "3":
            wallets = load_wallets()
            for w in wallets:
                claim_usdc(w["public_key"])
                time.sleep(5)

        elif choice == "4":
            target_wallet = input("Masukkan wallet tujuan (USDC): ")
            wallets = load_wallets()
            for w in wallets:
                if not w.get("sol_claimed", False):
                    success = claim_sol(w["public_key"])
                    if success:
                        w["sol_claimed"] = True
                        save_wallets(wallets)
                    time.sleep(2)
                claim_usdc(w["public_key"])
                send_usdc_placeholder(w["public_key"], target_wallet)
                time.sleep(5)

        elif choice == "5":
            break

        else:
            print("Pilihan tidak valid. Ulangi.")

menu()
