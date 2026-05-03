Cloud Honeypot — Real-World SSH Attack Detection on AWS

Deployed a live honeypot on AWS, captured real-world attacks from 7 countries, and built a SOC-style dashboard to visualize everything. Within 24 hours, 102 connections hit the trap — including a cryptomining bot that revealed its entire playbook.


What This Is
This is a cloud-based honeypot project built from scratch on AWS. A honeypot is a deliberately exposed system designed to attract and log real attackers. Instead of defending a real server, you build a fake one, let the internet find it, and watch what happens.
Spoiler: the internet finds it fast.
This project covers the full pipeline — from spinning up a cloud VM, to deploying honeypot software, to shipping logs into AWS CloudWatch, to building a live dashboard that visualizes attacks in real time. Every piece of data in this repo came from real attackers hitting a real server.

Results (First 24 Hours)
MetricCountTotal connection attempts102Unique attacking IPs24Countries represented7Login attempts captured50Successful honeypot logins5Attacker commands recorded14
Top attacking IP: 60.161.136.203 (China) — 54 connection attempts in a single session, running a sophisticated enterprise credential wordlist targeting services like ldap, weblogic, vagrant, and odoo.
Most interesting attacker: 114.219.11.228 (China) — a cryptomining bot that logged in and immediately ran cat /proc/cpuinfo to check CPU power, then searched for competing miners already running on the system. It was hunting for servers to hijack for crypto mining. It found a honeypot instead.

Attack Origins
CountryConnectionsChina71United States6India1Canada1Singapore1Taiwan1South Korea1

Credentials Captured
These are real passwords that real attackers tried. The "successful" logins are intentional — Cowrie presents a fake shell to attackers who "get in", recording everything they do while they believe they're inside a real system.
IPUsernamePasswordResult39.104.78.118rootAdmin1234Honeypot shell114.219.11.228rootadminHoneypot shell58.23.69.251rootcentosHoneypot shell120.195.56.56root---fuck_you----Honeypot shell101.96.216.167root---fuck_you----Honeypot shell
A note on "successful logins": these are not security failures. Cowrie is designed to accept certain credentials and simulate a real shell. Attackers believe they are inside a live system. They are not. Everything they do is logged and they never touch anything real.

Commands Run by Attackers
After "logging in", attackers ran the following commands inside Cowrie's fake shell:
uname -a                          # OS and architecture recon
ifconfig                          # Network interface check
cat /proc/cpuinfo                 # CPU power check (cryptominer hunting for resources)
ps / ps -ef | grep [Mm]iner       # Checking for competing miners already running
ls -la ~/.local/share/TelegramDesktop/tdata ...  # Hunting for Telegram data and SIM card managers
locate D877F783D5D3EF8C           # Known cryptominer malware hash — checking if already installed
echo Hi                           # Testing command execution
uname -s -m                       # Architecture check
The cryptominer's playbook is particularly telling. It followed a clear sequence: check CPU power → check for competing miners → look for communication channels to hijack → verify its own malware isn't already installed. This is automated, professional, and running at scale across the internet 24/7.

Architecture
Internet Attackers
        │
        ▼
AWS Security Group (ports 22, 80, 2222, 4444 open)
        │
        ▼
EC2 Instance (Ubuntu 26.04, t2.micro)
        │
    ┌───┴───┐
    │       │
iptables    SSH (port 4444 — admin only)
redirect
port 22 → 2222
    │
    ▼
Cowrie Honeypot (Docker)
    │
    ▼
Docker Logs → CloudWatch Agent → AWS CloudWatch
                                        │
                                        ▼
                              Metric Filter (login attempts)
                                        │
                                        ▼
                              SNS Alert → Email notification
                                        
Python Log Processor → Flask Dashboard (port 5000)

Tech Stack
ToolPurposeAWS EC2Cloud virtual machine hosting the honeypotAWS CloudWatchLog aggregation and monitoringAWS SNSReal-time email alerting on successful loginsAWS IAMSecure role-based access for CloudWatch agentDockerRunning Cowrie in an isolated containerCowrieSSH honeypot — captures credentials and commandsiptablesRedirecting port 22 traffic to Cowrie on port 2222Python + FlaskLog processing and live dashboard backendD3.jsWorld attack map visualizationChart.jsAttack origin bar chart

How It Works
1. The Trap
An EC2 instance is deployed with port 22 (SSH) intentionally open to the internet. An iptables rule silently redirects all traffic on port 22 to port 2222, where Cowrie is listening inside a Docker container. Attackers think they're hitting a real SSH server. They're not.
2. The Capture
Cowrie mimics a real Ubuntu server. It accepts connections, handles authentication, and presents a fake shell to anyone who "gets in." Every login attempt, every command typed, every file they try to download — all of it gets logged with timestamps and source IPs.
3. The Pipeline
A CloudWatch agent ships Cowrie's Docker logs to AWS CloudWatch in real time. A metric filter watches for successful login events and triggers an SNS notification, which sends an email alert within minutes.
4. The Dashboard
A Python script processes the raw Cowrie logs — extracting IPs, geolocating them via ip-api.com, parsing credentials and commands — and serves a live Flask dashboard. The dashboard auto-refreshes every 60 seconds and shows a D3.js world map with attack dots, country breakdown charts, attacker tables, and captured credentials.

Key Lessons Learned
Attackers are fast. The first connection hit within 6 minutes of the VM going live. Automated scanners are constantly sweeping every IP address on the internet.
Credential lists are sophisticated. The top attacker wasn't trying password123. It was targeting enterprise service accounts — ldap, weblogic, odoo, vagrant — with a curated list of known default credentials including Huawei12#$, a real Huawei equipment default.
Cryptominers are everywhere. Multiple attackers showed clear crypto mining intent — checking CPU resources, looking for competing miners, searching for known malware hashes. Your cloud server is a target not just for data theft but as a compute resource to steal.
Cloud security misconfigurations are dangerous. This project deliberately used a misconfigured server. In the real world, that misconfiguration is an accident. The speed and volume of attacks demonstrated here is why cloud security hygiene matters.
Detection engineering starts with data. Building the CloudWatch pipeline reinforced how real SOC alerting works — logs come in, filters extract signal from noise, alerts fire when something matters. The same pattern scales to enterprise environments.

Project Structure
cloud-honeypot/
├── README.md
├── dashboard.py          # Flask dashboard server
├── process_logs.py       # Log processing and IP geolocation script
└── screenshots/
    ├── dashboard-full.png
    ├── world-map.png
    ├── successful-logins.png
    ├── commands-captured.png
    └── top-attackers.png

Setup Guide
Prerequisites

AWS account
Basic Linux/SSH knowledge

1. Launch EC2 Instance

Ubuntu 26.04, t2.micro (free tier eligible)
Security group: open ports 22, 80, 2222, 2223, 4444, 5000
Generate and download a key pair

2. Connect and Update
bashssh -i your-key.pem ubuntu@your-ip
sudo apt update && sudo apt upgrade -y
3. Install Docker and Deploy Cowrie
bashsudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker
docker run -d --name cowrie --network host cowrie/cowrie:latest
docker update --restart always cowrie
4. Redirect Port 22 to Cowrie
bash# First move your admin SSH to port 4444
sudo nano /etc/ssh/sshd_config  # Change Port to 4444
sudo systemctl restart ssh

# Then redirect attackers to Cowrie
sudo apt install iptables-persistent -y
sudo iptables -t nat -I PREROUTING 1 -p tcp --dport 22 -j REDIRECT --to-port 2222
sudo netfilter-persistent save
5. Set Up CloudWatch
bash# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Create log group and stream via AWS CLI
aws logs create-log-group --log-group-name honeypot-logs --region us-east-1
aws logs create-log-stream --log-group-name honeypot-logs --log-stream-name cowrie-stream --region us-east-1

# Attach IAM role with CloudWatchAgentServerPolicy to your EC2 instance
# Then start the agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-config.json
6. Run the Dashboard
bashpip install flask requests --break-system-packages
python3 dashboard.py &
# Access at http://your-ip:5000

Important Notes
This project is for educational purposes. The honeypot is intentionally exposed — do not store sensitive data on the instance. Always terminate the instance when the project is complete to avoid ongoing charges. AWS free tier covers most of the cost; estimated spend for a 48-hour run is under $3.

About
Built by an aspiring SOC analyst exploring cloud security, threat detection, and real-world attack behavior. This project was as much about learning as it was about building — and the internet delivered better data than any lab simulation could.
If you have questions or want to talk security, find me on LinkedIn.
