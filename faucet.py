import requests
import json
import time
import random
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from colorama import init, Fore, Style
from apikey import TWOCAPTCHA_API_KEY

init()

WEB3_PROVIDER = "https://testnet.dplabs-internal.com"
FAUCET_URL = "https://api.pharosnetwork.xyz/faucet/daily"
LOGIN_URL = "https://api.pharosnetwork.xyz/user/login"
CAPTCHA_URL = "https://www.google.com/recaptcha/api2/reload"
VERIFY_URL = "https://www.google.com/recaptcha/api2/userverify"
SITE_KEY = "6Lfx1iwrAAAAAJp_suDVjStYCUs0keW8tQ722uZR"
INVITE_CODE = "gfLSEaGI1Tw4wdEN"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Langue": "ja-ID,ja;q=0.9,id-ID;q=0.8,id;q=0.7,en-ID;q=0.6,en-US;q=0.5,en;q=0.4",
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

def load_proxies():
    try:
        if not os.path.exists("proxy.txt"):
            print(f"{Fore.YELLOW}File proxy.txt not found, running without proxy{Style.RESET_ALL}")
            return []
        with open("proxy.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies:
            print(f"{Fore.YELLOW}File proxy.txt is empty, running without proxy{Style.RESET_ALL}")
        return proxies
    except Exception as e:
        print(f"{Fore.RED}Failed to read proxy.txt: {str(e)}{Style.RESET_ALL}")
        return []

class ProxyManager:
    def __init__(self):
        self.proxies = load_proxies()
        self.current_index = 0
    
    def get_proxy_for_address(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        proxy_dict = {"http": proxy, "https": proxy}
        print(f"{Fore.BLUE}Using proxy: {proxy}{Style.RESET_ALL}")
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy_dict

proxy_manager = ProxyManager()

def check_rpc_connection():
    try:
        if w3.is_connected():
            print(f"{Fore.GREEN}Connected to RPC: {WEB3_PROVIDER}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Failed to connect to RPC: {WEB3_PROVIDER}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error checking RPC: {str(e)}{Style.RESET_ALL}")
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
        print(f"{Fore.RED}Failed to create signature: {str(e)}{Style.RESET_ALL}")
        return None, None

def save_wallet(address, private_key):
    wallet_data = {}
    if os.path.exists("faucet.json"):
        with open("faucet.json", "r") as f:
            wallet_data = json.load(f)
    
    wallet_data[address] = {"private_key": private_key}
    
    with open("faucet.json", "w") as f:
        json.dump(wallet_data, f, indent=4)

def solve_captcha(proxy):
    captcha_data = {
        "key": TWOCAPTCHA_API_KEY,
        "method": "userrecaptcha",
        "googlekey": SITE_KEY,
        "pageurl": "https://testnet.pharosnetwork.xyz",
        "json": 1
    }
    
    try:
        response = requests.post("http://2captcha.com/in.php", data=captcha_data, proxies=proxy)
        if response.json().get("status") != 1:
            print(f"{Fore.RED}Failed to request CAPTCHA: {response.json()}{Style.RESET_ALL}")
            return None
        
        captcha_id = response.json().get("request")
        
        for _ in range(30):
            result = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1", proxies=proxy)
            result_json = result.json()
            if result_json.get("status") == 1:
                print(f"{Fore.GREEN}CAPTCHA successfully solved{Style.RESET_ALL}")
                return result_json.get("request")
            time.sleep(5)
        
        print(f"{Fore.RED}Failed to get CAPTCHA solution within time limit{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Failed to solve CAPTCHA with proxy: {str(e)}{Style.RESET_ALL}")
        return None

def login(address, signature, proxy, retries=3):
    login_params = {
        "address": address,
        "signature": signature,
        "invite_code": INVITE_CODE
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(LOGIN_URL, headers=HEADERS, params=login_params, proxies=proxy)
            barras = response.json()
            if response.status_code == 200 and barras.get("code") == 0:
                print(f"{Fore.GREEN}Login successful for {address}{Style.RESET_ALL}")
                return barras.get("data").get("jwt")
            print(f"{Fore.RED}Login failed (Attempt {attempt+1}/{retries}): {barras}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Failed to login with proxy (Attempt {attempt+1}/{retries}): {str(e)}{Style.RESET_ALL}")
        
        if attempt < retries - 1:
            print(f"{Fore.YELLOW}Waiting 2 seconds before retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Failed to login after {retries} attempts{Style.RESET_ALL}")
    return None

def claim_faucet(address, private_key):
    signature, recovered_address = create_signature(private_key)
    if not signature or recovered_address.lower() != address.lower():
        print(f"{Fore.RED}Failed to create signature or address mismatch: Expected {address}, Got {recovered_address}{Style.RESET_ALL}")
        return False
    
    proxy = proxy_manager.get_proxy_for_address()
    
    captcha_solution = solve_captcha(proxy)
    if not captcha_solution:
        print(f"{Fore.RED}Failed to solve CAPTCHA{Style.RESET_ALL}")
        return False
    
    jwt = login(address, signature, proxy)
    if not jwt:
        print(f"{Fore.RED}Failed to login{Style.RESET_ALL}")
        return False
    
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt}"
    
    for attempt in range(3):
        try:
            response = requests.post(f"{FAUCET_URL}?address={address}", headers=headers, proxies=proxy)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Successfully claimed faucet for {address}{Style.RESET_ALL}")
                return True
            print(f"{Fore.RED}Failed to claim faucet (Attempt {attempt+1}/3): {response.json()}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Failed to claim faucet with proxy (Attempt {attempt+1}/3): {str(e)}{Style.RESET_ALL}")
        
        if attempt < 2:
            print(f"{Fore.YELLOW}Waiting 2 seconds before retry...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"{Fore.RED}Failed to claim faucet after 3 attempts{Style.RESET_ALL}")
    return False

def read_private_keys():
    try:
        if not os.path.exists("faucet.json"):
            print(f"{Fore.RED}File faucet.json not found{Style.RESET_ALL}")
            return []
        
        with open("faucet.json", "r") as f:
            wallet_data = json.load(f)
        
        private_keys = [(addr, data["private_key"]) for addr, data in wallet_data.items()]
        if not private_keys:
            print(f"{Fore.RED}No private keys in faucet.json{Style.RESET_ALL}")
        return private_keys
    except Exception as e:
        print(f"{Fore.RED}Failed to read faucet.json: {str(e)}{Style.RESET_ALL}")
        return []

def get_balance(address):
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_phrs = w3.from_wei(balance_wei, "ether")
        return balance_wei, balance_phrs
    except Exception as e:
        print(f"{Fore.RED}Failed to get balance for {address}: {str(e)}{Style.RESET_ALL}")
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
            print(f"{Fore.RED}Transfer failed for {from_address}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Failed to transfer from {from_address}: {str(e)}{Style.RESET_ALL}")
        return False

def is_valid_address(address):
    return w3.is_address(address)

def get_recipient_address():
    while True:
        address = input(f"{Fore.YELLOW}Enter recipient address (Ethereum address): {Style.RESET_ALL}").strip()
        if is_valid_address(address):
            return w3.to_checksum_address(address)
        print(f"{Fore.RED}Invalid address, ensure it's a valid Ethereum address{Style.RESET_ALL}")

def get_main_option():
    while True:
        print(f"{Fore.YELLOW}Select option:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. Claim Faucet{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. Transfer Faucet{Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}Enter choice (1/2): {Style.RESET_ALL}")
        if choice in ["1", "2"]:
            return choice
        print(f"{Fore.RED}Invalid choice, enter 1 or 2{Style.RESET_ALL}")

def get_claim_count():
    while True:
        try:
            count = int(input(f"{Fore.YELLOW}Enter desired number of faucet claims: {Style.RESET_ALL}"))
            if count <= 0:
                print(f"{Fore.RED}Number of claims must be greater than 0{Style.RESET_ALL}")
                continue
            print(f"{Fore.GREEN}Will perform {count} faucet claims{Style.RESET_ALL}")
            return count
        except ValueError:
            print(f"{Fore.RED}Enter a valid number{Style.RESET_ALL}")

def get_transfer_option():
    while True:
        print(f"{Fore.YELLOW}Select transfer option:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. Transfer all PHRS{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. Transfer random (0.05 - 0.09 PHRS){Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}Enter choice (1/2): {Style.RESET_ALL}")
        if choice in ["1", "2"]:
            return choice
        print(f"{Fore.RED}Invalid choice, enter 1 or 2{Style.RESET_ALL}")

def main():
    print(BANNER)
    
    if not check_rpc_connection():
        print(f"{Fore.RED}Cannot proceed due to RPC connection issues{Style.RESET_ALL}")
        return
    
    while True:
        option = get_main_option()
        
        if option == "1":
            claim_count = get_claim_count()
            for i in range(claim_count):
                print(f"{Fore.CYAN}Processing claim {i+1} of {claim_count}{Style.RESET_ALL}")
                address, private_key = generate_wallet()
                print(f"{Fore.BLUE}New wallet created - Address: {address}{Style.RESET_ALL}")
                
                if claim_faucet(address, private_key):
                    save_wallet(address, private_key)
                else:
                    print(f"{Fore.RED}Claim failed, wallet not saved{Style.RESET_ALL}")
                
                if i < claim_count - 1:
                    print(f"{Fore.YELLOW}Waiting 5 seconds before next claim...{Style.RESET_ALL}")
                    time.sleep(5)
        
        elif option == "2":
            private_keys = read_private_keys()
            if not private_keys:
                print(f"{Fore.RED}No private keys for transfer, run faucet claim first{Style.RESET_ALL}")
                continue
            
            recipient = get_recipient_address()
            transfer_option = get_transfer_option()
            
            for i, (address, private_key) in enumerate(private_keys, 1):
                print(f"{Fore.CYAN}Processing transfer from address {i} of {len(private_keys)}: {address}{Style.RESET_ALL}")
                
                balance_wei, balance_phrs = get_balance(address)
                print(f"{Fore.BLUE}Current balance: {balance_phrs:.4f} PHRS{Style.RESET_ALL}")
                
                if balance_wei == 0:
                    print(f"{Fore.RED}Balance empty, skipping this address{Style.RESET_ALL}")
                    continue
                
                gas_limit = 21000
                gas_price = w3.eth.gas_price
                gas_fee = gas_limit * gas_price
                
                if balance_wei <= gas_fee:
                    print(f"{Fore.RED}Insufficient balance for gas, skipping this address{Style.RESET_ALL}")
                    continue
                
                if transfer_option == "1":
                    amount_wei = balance_wei - gas_fee
                else:
                    amount_phrs = random.uniform(0.05, 0.09)
                    amount_wei = w3.to_wei(amount_phrs, "ether")
                    if amount_wei + gas_fee > balance_wei:
                        print(f"{Fore.RED}Insufficient balance for random transfer, trying full transfer{Style.RESET_ALL}")
                        amount_wei = balance_wei - gas_fee
                
                if amount_wei <= 0:
                    print(f"{Fore.RED}Invalid transfer amount, skipping this address{Style.RESET_ALL}")
                    continue
                
                transfer_phrs(private_key, recipient, amount_wei)
                
                if i < len(private_keys):
                    print(f"{Fore.YELLOW}Waiting 5 seconds before next transfer...{Style.RESET_ALL}")
                    time.sleep(5)

if __name__ == "__main__":
    main()
      
