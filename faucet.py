import requests
import json
import time
import random
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed

# Inisialisasi colorama untuk warna log
init()

# Pharos Testnet konfigurasi
WEB3_PROVIDER = "https://testnet.dplabs-internal.com"
FAUCET_URL = "https://api.pharosnetwork.xyz/faucet/daily"
LOGIN_URL = "https://api.pharosnetwork.xyz/user/login"
INVITE_CODE = "gfLSEaGI1Tw4wdEN"

# Headers untuk request API
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ja-ID,ja;q=0.9,id-ID;q=0.8,id;q=0.7,en-ID;q=0.6,en-US;q=0.5,en;q=0.4",
    "Origin": "https://testnet.pharosnetwork.xyz",
    "Referer": "https://testnet.pharosnetwork.xyz/",
    "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
}

# Inisialisasi Web3
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# Banner
BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}╔════════════════════════════════════════════════╗
║     🌟 PHAROS BOT - Auto Claim & Transfer      ║
║  Automate Pharos Network faucet and transfers  ║
║    Developed by: https://t.me/sentineldiscus   ║
╚════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

# Fungsi untuk membaca proxy dari proxy.txt
def load_proxies():
    try:
        if not os.path.exists("proxy.txt"):
            print(f"{Fore.YELLOW}File proxy.txt tidak ditemukan, berjalan tanpa proxy{Style.RESET_ALL}")
            return []
        with open("proxy.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies:
            print(f"{Fore.YELLOW}File proxy.txt kosong, berjalan tanpa proxy{Style.RESET_ALL}")
        return proxies
    except Exception as e:
        print(f"{Fore.RED}Gagal membaca proxy.txt: {str(e)}{Style.RESET_ALL}")
        return []

# Fungsi untuk memilih proxy berikutnya
class ProxyManager:
    def __init__(self):
        self.proxies = load_proxies()
        self.current_index = 0
    
    def get_proxy_for_address(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        proxy_dict = {"http": proxy, "https": proxy}
        print(f"{Fore.BLUE}Menggunakan proxy: {proxy}{Style.RESET_ALL}")
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy_dict

# Inisialisasi ProxyManager
proxy_manager = ProxyManager()

# Fungsi untuk memeriksa koneksi RPC
def check_rpc_connection():
    try:
        if w3.is_connected():
            print(f"{Fore.GREEN}Terhubung ke RPC: {WEB3_PROVIDER}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Gagal terhubung ke RPC: {WEB3_PROVIDER}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error saat memeriksa RPC: {str(e)}{Style.RESET_ALL}")
        return False

# Fungsi untuk generate wallet baru
def generate_wallet():
    account = Account.create()
    address = account.address
    private_key = account._private_key.hex()
    return address, private_key

# Fungsi untuk membuat signature
def create_signature(private_key, message="pharos"):
    try:
        account = w3.eth.account.from_key(private_key)
        message_hash = encode_defunct(text=message)
        signed_message = w3.eth.account.sign_message(message_hash, private_key=private_key)
        return signed_message.signature.hex(), account.address
    except Exception as e:
        print(f"{Fore.RED}Gagal membuat signature: {str(e)}{Style.RESET_ALL}")
        return None, None

# Fungsi untuk menyimpan wallet ke faucet.json
def save_wallet(address, private_key):
    wallet_data = {}
    if os.path.exists("faucet.json"):
        with open("faucet.json", "r") as f:
            wallet_data = json.load(f)
    
    wallet_data[address] = {"private_key": private_key}
    
    with open("faucet.json", "w") as f:
        json.dump(wallet_data, f, indent=4)

# Fungsi untuk login dan mendapatkan JWT dengan retry
def login(address, signature, proxy, retries=3):
    login_params = {
        "address": address,
        "signature": signature,
        "invite_code": INVITE_CODE
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(LOGIN_URL, headers=HEADERS, params=login_params, proxies=proxy)
            if response.status_code == 200 and response.json().get("code") == 0:
                print(f"{Fore.GREEN}Login berhasil untuk {address}{Style.RESET_ALL}")
                return response.json().get("data").get("jwt")
            print(f"{Fore.RED}Login gagal (Percobaan {attempt+1}/{retries}): {response.json()}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Gagal login dengan proxy (Percobaan {attempt+1}/{retries}): {str(e)}{Style.RESET_ALL}")
        
        if attempt < retries - 1:
            print(f"{Fore.YELLOW}Menunggu 2 detik sebelum retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Gagal login setelah {retries} percobaan{Style.RESET_ALL}")
    return None

# Fungsi untuk klaim faucet dengan retry
def claim_faucet(address, private_key):
    signature, recovered_address = create_signature(private_key)
    if not signature or recovered_address.lower() != address.lower():
        print(f"{Fore.RED}Gagal membuat signature atau address tidak cocok: Diharapkan {address}, Didapat {recovered_address}{Style.RESET_ALL}")
        return False
    
    proxy = proxy_manager.get_proxy_for_address()
    
    jwt = login(address, signature, proxy)
    if not jwt:
        print(f"{Fore.RED}Gagal login{Style.RESET_ALL}")
        return False
    
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt}"
    
    for attempt in range(3):
        try:
            response = requests.post(f"{FAUCET_URL}?address={address}", headers=headers, proxies=proxy)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Berhasil klaim faucet untuk {address}{Style.RESET_ALL}")
                return True
            print(f"{Fore.RED}Gagal klaim faucet (Percobaan {attempt+1}/3): {response.json()}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Gagal klaim faucet dengan proxy (Percobaan {attempt+1}/3): {str(e)}{Style.RESET_ALL}")
        
        if attempt < 2:
            print(f"{Fore.YELLOW}Menunggu 2 detik sebelum retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Gagal klaim faucet setelah 3 percobaan{Style.RESET_ALL}")
    return False

# Fungsi untuk membaca private keys dari faucet.json
def read_private_keys():
    try:
        if not os.path.exists("faucet.json"):
            print(f"{Fore.RED}File faucet.json tidak ditemukan{Style.RESET_ALL}")
            return []
        
        with open("faucet.json", "r") as f:
            wallet_data = json.load(f)
        
        private_keys = [(addr, data["private_key"]) for addr, data in wallet_data.items()]
        if not private_keys:
            print(f"{Fore.RED}Tidak ada private keys di faucet.json{Style.RESET_ALL}")
        return private_keys
    except Exception as e:
        print(f"{Fore.RED}Gagal membaca faucet.json: {str(e)}{Style.RESET_ALL}")
        return []

# Fungsi untuk mendapatkan saldo PHRS
def get_balance(address):
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_phrs = w3.from_wei(balance_wei, "ether")
        return balance_wei, balance_phrs
    except Exception as e:
        print(f"{Fore.RED}Gagal mendapatkan saldo untuk {address}: {str(e)}{Style.RESET_ALL}")
        return 0, 0

# Fungsi untuk transfer PHRS
def transfer_phrs(private_key, to_address, amount_wei):
    try:
        account = w3.eth.account.from_key(private_key)
        from_address = account.address
        
        nonce = w3.eth.get_transaction_count(from_address, "pending")
        gas_price = w3.eth.gas_price
        gas_limit = 21000
        
        tx = {
            "from": from_address,
            "to": to_address,
            "value": amount_wei,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": 688688
        }
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"{Fore.GREEN}Tx Hash: {w3.to_hex(tx_hash)}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Transfer gagal untuk {from_address}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Gagal transfer dari {from_address}: {str(e)}{Style.RESET_ALL}")
        return False

# Fungsi untuk validasi alamat Ethereum
def is_valid_address(address):
    return w3.is_address(address)

# Fungsi untuk mendapatkan alamat penerima
def get_recipient_address():
    while True:
        address = input(f"{Fore.YELLOW}Masukkan alamat penerima (Ethereum address): {Style.RESET_ALL}").strip()
        if is_valid_address(address):
            return w3.to_checksum_address(address)
        print(f"{Fore.RED}Alamat tidak valid, pastikan alamat Ethereum benar{Style.RESET_ALL}")

# Fungsi untuk mendapatkan input opsi utama
def get_main_option():
    while True:
        print(f"{Fore.YELLOW}Pilih opsi:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. Claim Faucet{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. Transfer Faucet{Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}Masukkan pilihan (1/2): {Style.RESET_ALL}")
        if choice in ["1", "2"]:
            return choice
        print(f"{Fore.RED}Pilihan tidak valid, masukkan 1 atau 2{Style.RESET_ALL}")

# Fungsi untuk mendapatkan jumlah klaim faucet
def get_claim_count():
    while True:
        try:
            count = int(input(f"{Fore.YELLOW}Masukkan jumlah klaim faucet yang diinginkan: {Style.RESET_ALL}"))
            if count <= 0:
                print(f"{Fore.RED}Jumlah klaim harus lebih dari 0{Style.RESET_ALL}")
                continue
            print(f"{Fore.GREEN}Akan melakukan {count} klaim faucet{Style.RESET_ALL}")
            return count
        except ValueError:
            print(f"{Fore.RED}Masukkan angka yang valid{Style.RESET_ALL}")

# Fungsi untuk mendapatkan jumlah worker threads
def get_worker_count():
    while True:
        try:
            count = int(input(f"{Fore.YELLOW}Masukkan jumlah worker threads (1-10): {Style.RESET_ALL}"))
            if 1 <= count <= 10:
                print(f"{Fore.GREEN}Menggunakan {count} worker threads{Style.RESET_ALL}")
                return count
            print(f"{Fore.RED}Jumlah worker harus antara 1 dan 10{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Masukkan angka yang valid{Style.RESET_ALL}")

# Fungsi untuk mendapatkan opsi transfer
def get_transfer_option():
    while True:
        print(f"{Fore.YELLOW}Pilih opsi transfer:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. Transfer semua PHRS{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. Transfer random (0.05 - 0.09 PHRS){Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}Masukkan pilihan (1/2): {Style.RESET_ALL}")
        if choice in ["1", "2"]:
            return choice
        print(f"{Fore.RED}Pilihan tidak valid, masukkan 1 atau 2{Style.RESET_ALL}")

# Fungsi untuk memproses klaim faucet
def process_claim(_):
    address, private_key = generate_wallet()
    print(f"{Fore.BLUE}Wallet baru dibuat - Address: {address}{Style.RESET_ALL}")
    
    if claim_faucet(address, private_key):
        save_wallet(address, private_key)
        return True
    else:
        print(f"{Fore.RED}Klaim gagal, wallet tidak disimpan{Style.RESET_ALL}")
        return False

# Fungsi untuk memproses transfer
def process_transfer(args):
    address, private_key, recipient, transfer_option = args
    print(f"{Fore.CYAN}Memproses transfer dari address: {address}{Style.RESET_ALL}")
    
    balance_wei, balance_phrs = get_balance(address)
    print(f"{Fore.BLUE}Saldo saat ini: {balance_phrs:.4f} PHRS{Style.RESET_ALL}")
    
    if balance_wei == 0:
        print(f"{Fore.RED}Saldo kosong, lewati address ini{Style.RESET_ALL}")
        return False
    
    gas_limit = 21000
    gas_price = w3.eth.gas_price
    gas_fee = gas_limit * gas_price
    
    if balance_wei <= gas_fee:
        print(f"{Fore.RED}Saldo tidak cukup untuk membayar gas, lewati address ini{Style.RESET_ALL}")
        return False
    
    if transfer_option == "1":
        # Transfer semua PHRS (dikurangi gas)
        amount_wei = balance_wei - gas_fee
    else:
        # Transfer random 0.05 - 0.09 PHRS
        amount_phrs = random.uniform(0.05, 0.09)
        amount_wei = w3.to_wei(amount_phrs, "ether")
        if amount_wei + gas_fee > balance_wei:
            print(f"{Fore.RED}Saldo tidak cukup untuk transfer random, coba transfer semua{Style.RESET_ALL}")
            amount_wei = balance_wei - gas_fee
    
    if amount_wei <= 0:
        print(f"{Fore.RED}Jumlah transfer tidak valid, lewati address ini{Style.RESET_ALL}")
        return False
    
    return transfer_phrs(private_key, recipient, amount_wei)

def main():
    print(BANNER)
    
    if not check_rpc_connection():
        print(f"{Fore.RED}Tidak dapat melanjutkan karena masalah koneksi RPC{Style.RESET_ALL}")
        return
    
    while True:
        option = get_main_option()
        max_workers = get_worker_count()
        
        if option == "1":
            # Claim Faucet
            claim_count = get_claim_count()
            print(f"{Fore.CYAN}Memulai {claim_count} klaim faucet dengan {max_workers} workers{Style.RESET_ALL}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_claim, i) for i in range(claim_count)]
                for i, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    print(f"{Fore.CYAN}Klaim ke-{i} dari {claim_count} selesai: {'Berhasil' if result else 'Gagal'}{Style.RESET_ALL}")
                    if i < claim_count:
                        print(f"{Fore.YELLOW}Menunggu 1 detik sebelum hasil berikutnya...{Style.RESET_ALL}")
                        time.sleep(1)
        
        elif option == "2":
            # Transfer Faucet
            private_keys = read_private_keys()
            if not private_keys:
                print(f"{Fore.RED}Tidak ada private keys untuk transfer, jalankan claim faucet terlebih dahulu{Style.RESET_ALL}")
                continue
            
            recipient = get_recipient_address()
            transfer_option = get_transfer_option()
            print(f"{Fore.CYAN}Memulai transfer dari {len(private_keys)} address dengan {max_workers} workers{Style.RESET_ALL}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_transfer, (addr, pk, recipient, transfer_option)) 
                          for addr, pk in private_keys]
                for i, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    print(f"{Fore.CYAN}Transfer ke-{i} dari {len(private_keys)} selesai: {'Berhasil' if result else 'Gagal'}{Style.RESET_ALL}")
                    if i < len(private_keys):
                        print(f"{Fore.YELLOW}Menunggu 1 detik sebelum hasil berikutnya...{Style.RESET_ALL}")
                        time.sleep(1)

if __name__ == "__main__":
    main()
                    
