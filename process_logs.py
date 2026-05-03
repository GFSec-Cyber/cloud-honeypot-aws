import json
import re
import subprocess
from datetime import datetime
from collections import defaultdict
import requests

def get_country(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = response.json()
        return data.get("country", "Unknown"), data.get("countryCode", "??"), data.get("lat", 0), data.get("lon", 0)
    except:
        return "Unknown", "??", 0, 0

def process_logs():
    result = subprocess.run(
        ["docker", "logs", "cowrie"],
        capture_output=True,
        text=True
    )
    logs = result.stdout + result.stderr
    
    attacks = defaultdict(lambda: {
        "ip": "",
        "country": "",
        "country_code": "",
        "lat": 0,
        "lon": 0,
        "connection_count": 0,
        "login_attempts": [],
        "successful_logins": [],
        "commands": []
    })
    
    for line in logs.split("\n"):
        # Extract new connections
        conn_match = re.search(r"New connection: (\d+\.\d+\.\d+\.\d+)", line)
        if conn_match:
            ip = conn_match.group(1)
            attacks[ip]["ip"] = ip
            attacks[ip]["connection_count"] += 1
        
        # Extract login attempts
        login_match = re.search(r"\[(\d+\.\d+\.\d+\.\d+)\] login attempt \[b'(.+)'/b'(.+)'\] (failed|succeeded)", line)
        if login_match:
            ip = login_match.group(1)
            username = login_match.group(2)
            password = login_match.group(3)
            status = login_match.group(4)
            attacks[ip]["ip"] = ip
            attempt = {"username": username, "password": password, "status": status}
            attacks[ip]["login_attempts"].append(attempt)
            if status == "succeeded":
                attacks[ip]["successful_logins"].append(attempt)
        
        # Extract commands
        cmd_match = re.search(r"\[(\d+\.\d+\.\d+\.\d+)\] Command found: (.+)", line)
        if cmd_match:
            ip = cmd_match.group(1)
            command = cmd_match.group(2).strip()
            attacks[ip]["ip"] = ip
            attacks[ip]["commands"].append(command)
    
    # Get country info for each IP
    print("Looking up country info for each IP...")
    for ip in attacks:
        if ip and not ip.startswith("172."):
            country, code, lat, lon = get_country(ip)
            attacks[ip]["country"] = country
            attacks[ip]["country_code"] = code
            attacks[ip]["lat"] = lat
            attacks[ip]["lon"] = lon
            print(f"  {ip} -> {country}")
    
    # Convert to list and save
    output = list(attacks.values())
    output = [a for a in output if a["ip"] and not a["ip"].startswith("172.")]
    
    with open("/home/ubuntu/attack_data.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nDone! Processed {len(output)} unique attackers.")
    print("Data saved to attack_data.json")

if __name__ == "__main__":
    process_logs()
