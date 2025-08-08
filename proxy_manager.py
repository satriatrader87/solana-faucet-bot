import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time

OUTPUT_FILE = "proxies_valid.txt"
TIMEOUT = 5

# === Fetch Proxies ===

def fetch_proxies_from_proxyscrape():
    print("[*] Mengambil proxy dari ProxyScrape...")
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=all&ssl=all&anonymity=all"
    proxies = []
    try:
        res = requests.get(url, timeout=10)
        proxies = [f"http://{line.strip()}" for line in res.text.split("\n") if line.strip()]
    except Exception as e:
        print(f"[!] Gagal dari ProxyScrape: {e}")
    return proxies

def fetch_proxies_from_free_proxy_list():
    print("[*] Mengambil proxy dari free-proxy-list.net ...")
    url = "https://free-proxy-list.net/"
    proxies = []

    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", attrs={"id": "proxylisttable"})
        if table is None:
            raise Exception("Table tidak ditemukan.")

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            https = cols[6].text.strip()
            if https.lower() == "no":  # hanya HTTP
                proxies.append(f"http://{ip}:{port}")
    except Exception as e:
        print(f"[!] Gagal mengambil dari free-proxy-list: {e}")

    return proxies

def fetch_proxies_from_geonode():
    print("[*] Mengambil proxy dari Geonode ...")
    url = "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc"
    proxies = []

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        for p in data["data"]:
            if "http" in p["protocols"]:
                proxies.append(f"http://{p['ip']}:{p['port']}")
    except Exception as e:
        print(f"[!] Gagal mengambil dari Geonode: {e}")

    return proxies

def fetch_all_proxies():
    proxies = []
    proxies += fetch_proxies_from_proxyscrape()
    proxies += fetch_proxies_from_free_proxy_list()
    proxies += fetch_proxies_from_geonode()
    print(f"[✓] Total proxy ditemukan: {len(proxies)}")
    return proxies

# === Validate Proxies ===

def check_proxy(proxy):
    try:
        res = requests.get("https://api.ipify.org", proxies={"http": proxy, "https": proxy}, timeout=TIMEOUT)
        if res.ok:
            print(f"[✓] VALID: {proxy} → IP: {res.text}")
            return proxy
    except:
        pass
    print(f"[x] INVALID: {proxy}")
    return None

def validate_proxies(proxies):
    print("[*] Memvalidasi proxy...")
    valid_proxies = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(check_proxy, proxy) for proxy in proxies]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                valid_proxies.append(result)

    return valid_proxies

# === Save to File ===

def save_valid_proxies(valid, filename):
    with open(filename, "w") as f:
        for proxy in valid:
            f.write(f"{proxy}\n")
    print(f"\n[✓] {len(valid)} proxy valid disimpan ke {filename}")

# === Main ===

def main():
    start = time.time()
    proxies = fetch_all_proxies()
    if not proxies:
        print("❌ Tidak ada proxy yang berhasil diambil.")
        return

    valid = validate_proxies(proxies)
    save_valid_proxies(valid, OUTPUT_FILE)

    print(f"\nSelesai dalam {round(time.time() - start, 2)} detik.")

if __name__ == "__main__":
    main()
