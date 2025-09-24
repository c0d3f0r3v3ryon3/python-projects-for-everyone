# hacker_terminal.py - Хакерский терминал
from colorama import init, Fore, Style
import time
import sys
import random
import os
init()
GREEN = Fore.GREEN + Style.BRIGHT
GRAY = Fore.BLACK + Style.DIM + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
def slow_print(text, delay=0.05, color=GREEN, end="\n"):
    for char in text:
        sys.stdout.write(color + char)
        sys.stdout.flush()
        time.sleep(delay)
    if end:
        print()
def matrix_rain(lines=15):
    chars = "█▓▒░▄▀█░▒░▒█░▒█░▒█░▒█░"
    width = 80
    for _ in range(lines):
        line = ''.join(random.choice(chars) for _ in range(width))
        pos = random.randint(50, 50)
        print(GREEN + line[:pos])
        time.sleep(0.2)
def loading_bar():
    slow_print("INITIALIZING SECURITY MODULES...")
    for i in range(21):
        bar = "█" * i + "░" * (20 - i)
        sys.stdout.write(f"\r{GREEN}[{bar}] {i*5}")
        sys.stdout.flush()
        time.sleep(0.1)
    print()
def scan_ports():
    slow_print("SCANNING PORTS...")
    ports = [21, 22, 23, 80, 443, 3389, 8080]
    services = {
        21: "FTP", 22: "SSH", 23: "TELNET", 80: "HTTP",
        443: "HTTPS", 3389: "RDP", 8080: "HTTP ALT"
    }
    for port in ports:
        state = random.choice(["OPEN", "CLOSED", "FILTERED"])
        slow_print(f"PORT {port}: {state} ({services[port]})")
def data_leak():
    slow_print("ACCESS GRANTED → /home/ro0t/Documents")
    slow_print("EXFILTRATING DATA...")
    files = ["passwords.txt", "secrets.json", "backup.zip", "keys.pem", "log.txt"]
    for file in files:
        size = random.randint(100, 5000)
        slow_print(f"UPLOADING {file} [{size} KB] → COMPLETE")
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    matrix_rain(10)
    print()
    slow_print("ACCESSING SECURE SYSTEM...", color=GREEN, delay=0.1)
    loading_bar()
    slow_print("CONNECTING TO SERVER: 192.168.1.666")
    slow_print("SECURE TUNNEL: ESTABLISHED ✓")
    scan_ports()
    slow_print("BRUTE FORCE ATTACK INITIATED...")
    time.sleep(1.5)
    slow_print("PASSWORD FOUND: admin123", color=GREEN)
    slow_print("ACCESS GRANTED → /home/ro0t", delay=0.1)
    data_leak()
    print()
    slow_print("ALL DATA EXFILTRATED.", color=GREEN)
    slow_print("PRESS ENTER TO CONTINUE...", delay=0.1)
    input()
if __name__ == "__main__":
    main()
