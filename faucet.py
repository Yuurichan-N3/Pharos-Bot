import requests
import json
import time
import random
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from colorama import init, Fore, Style

init()

WEB3_PROVIDER = "https://testnet.dplabs-internal.com"
FAUCET_URL = "https://api.pharosnetwork.xyz/faucet/daily"
LOGIN_URL = "https://api.pharosnetwork.xyz/user/login"
INVITE_CODE = "gfLSEaGI1Tw4wdEN"

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

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}╔════════════════════════════════════════════════╗
║     🌟 PHAROS BOT - Auto Claim & Transfer      ║
║  Automate Pharos Network faucet and transfers  ║
║    Developed by: https://t.me/sentineldiscus   ║
╚════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

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

def generate_wallet():
    account = Account.create()
    address = account.address
    private_key = account._private_key.hex()
    return address, private_key

def create_signature(private_key, message="pharos"):
    try:
        account = w3.eth.account.from_key(private_key)
        message_hash = encode_defunct(text=message)
        signed_message = w3.eth.account.sign_message(message_hash, private_key=private_key)
        return signed_message.signature.hex(), account.address
    except Exception as e:
        print(f"{Fore.RED}Gagal membuat signature: {str(e)}{Style.RESET_ALL}")
        return None, None

def login(address, signature, retries=3):
    login_params = {
        "address": address,
        "signature": signature,
        "invite_code": INVITE_CODE
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(LOGIN_URL, headers=HEADERS, params=login_params)
            if response.status_code == 200 and response.json().get("code") == 0:
                print(f"{Fore.GREEN}Login berhasil untuk {address}{Style.RESET_ALL}")
                return response.json().get("data").get("jwt")
            print(f"{Fore.RED}Login gagal (Percobaan {attempt+1}/{retries}): {response.json()}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Gagal login (Percobaan {attempt+1}/{retries}): {str(e)}{Style.RESET_ALL}")
        
        if attempt < retries - 1:
            print(f"{Fore.YELLOW}Menunggu 2 detik sebelum retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Gagal login setelah {retries} percobaan{Style.RESET_ALL}")
    return None

def claim_faucet(address, private_key):
    signature, recovered_address = create_signature(private_key)
    if not signature or recovered_address.lower() != address.lower():
        print(f"{Fore.RED}Gagal membuat signature atau address tidak cocok{Style.RESET_ALL}")
        return False
    
    jwt = login(address, signature)
    if not jwt:
        print(f"{Fore.RED}Gagal login{Style.RESET_ALL}")
        return False
    
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt}"
    
    for attempt in range(3):
        try:
            response = requests.post(f"{FAUCET_URL}?address={address}", headers=headers)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Berhasil klaim faucet untuk {address}{Style.RESET_ALL}")
                return True
            print(f"{Fore.RED}Gagal klaim faucet (Percobaan {attempt+1}/3): {response.json()}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Gagal klaim faucet (Percobaan {attempt+1}/3): {str(e)}{Style.RESET_ALL}")
        
        if attempt < 2:
            print(f"{Fore.YELLOW}Menunggu 2 detik sebelum retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Gagal klaim faucet setelah 3 percobaan{Style.RESET_ALL}")
    return False

def get_balance(address):
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_phrs = w3.from_wei(balance_wei, "ether")
        return balance_wei, balance_phrs
    except Exception as e:
        print(f"{Fore.RED}Gagal mendapatkan saldo untuk {address}: {str(e)}{Style.RESET_ALL}")
        return 0, 0

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

def is_valid_address(address):
    return w3.is_address(address)

def get_recipient_address():
    while True:
        address = input(f"{Fore.YELLOW}Masukkan alamat penerima (Ethereum address): {Style.RESET_ALL}").strip()
        if is_valid_address(address):
            return w3.to_checksum_address(address)
        print(f"{Fore.RED}Alamat tidak valid, pastikan alamat Ethereum benar{Style.RESET_ALL}")

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

def process_batch(recipient, batch_size=10):
    wallets = []
    
    print(f"{Fore.CYAN}Membuat {batch_size} wallet baru...{Style.RESET_ALL}")
    for _ in range(batch_size):
        address, private_key = generate_wallet()
        wallets.append((address, private_key))
        print(f"{Fore.BLUE}Wallet baru dibuat - Address: {address}{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}Melakukan login untuk {batch_size} wallet...{Style.RESET_ALL}")
    for i, (address, private_key) in enumerate(wallets[:]):
        signature, recovered_address = create_signature(private_key)
        if signature and recovered_address.lower() == address.lower():
            jwt = login(address, signature)
            if jwt:
                wallets[i] = (address, private_key, jwt)
            else:
                print(f"{Fore.RED}Gagal login untuk {address}, melewati wallet ini{Style.RESET_ALL}")
                wallets[i] = None
        else:
            print(f"{Fore.RED}Gagal membuat signature untuk {address}, melewati wallet ini{Style.RESET_ALL}")
            wallets[i] = None
    
    print(f"{Fore.CYAN}Mengklaim faucet untuk wallet yang berhasil login...{Style.RESET_ALL}")
    for i, wallet in enumerate(wallets[:]):
        if wallet is None:
            continue
        address, private_key, jwt = wallet
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {jwt}"
        try:
            response = requests.post(f"{FAUCET_URL}?address={address}", headers=headers)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Berhasil klaim faucet untuk {address}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Gagal klaim faucet untuk {address}: {response.json()}{Style.RESET_ALL}")
                wallets[i] = None
        except Exception as e:
            print(f"{Fore.RED}Gagal klaim faucet untuk {address}: {str(e)}{Style.RESET_ALL}")
            wallets[i] = None
    
    print(f"{Fore.CYAN}Melakukan transfer dari wallet yang berhasil claim...{Style.RESET_ALL}")
    for wallet in wallets:
        if wallet is None:
            continue
        address, private_key, _ = wallet
        balance_wei, balance_phrs = get_balance(address)
        print(f"{Fore.BLUE}Saldo {address}: {balance_phrs:.4f} PHRS{Style.RESET_ALL}")
        
        if balance_wei == 0:
            print(f"{Fore.RED}Saldo kosong untuk {address}, melewati wallet ini{Style.RESET_ALL}")
            continue
        
        gas_limit = 21000
        gas_price = w3.eth.gas_price
        gas_fee = gas_limit * gas_price
        
        if balance_wei <= gas_fee:
            print(f"{Fore.RED}Saldo tidak cukup untuk gas di {address}, melewati wallet ini{Style.RESET_ALL}")
            continue
        
        amount_wei = balance_wei - gas_fee
        if amount_wei <= 0:
            print(f"{Fore.RED}Jumlah transfer tidak valid untuk {address}, melewati wallet ini{Style.RESET_ALL}")
            continue
        
        if transfer_phrs(private_key, recipient, amount_wei):
            print(f"{Fore.GREEN}Berhasil transfer dari {address} ke {recipient}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Gagal transfer dari {address}{Style.RESET_ALL}")

def main():
    print(BANNER)
    
    if not check_rpc_connection():
        print(f"{Fore.RED}Tidak dapat melanjutkan karena masalah koneksi RPC{Style.RESET_ALL}")
        return
    
    recipient = get_recipient_address()
    total_claims = get_claim_count()
    
    print(f"{Fore.CYAN}Memulai proses untuk {total_claims} klaim dan transfer ke {recipient}{Style.RESET_ALL}")
    
    processed = 0
    while processed < total_claims:
        batch_size = min(10, total_claims - processed)
        print(f"{Fore.CYAN}Memproses batch {processed//10 + 1} ({batch_size} wallet)...{Style.RESET_ALL}")
        process_batch(recipient, batch_size)
        processed += batch_size
        if processed < total_claims:
            print(f"{Fore.YELLOW}Menunggu 5 detik sebelum batch berikutnya...{Style.RESET_ALL}")
            time.sleep(5)
    
    print(f"{Fore.GREEN}Selesai memproses {total_claims} klaim dan transfer!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
        
