from flask import Flask, jsonify, render_template_string
import subprocess
import re
import requests
from collections import defaultdict

app = Flask(__name__)

def get_country(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = response.json()
        return data.get("country", "Unknown"), data.get("lat", 0), data.get("lon", 0)
    except:
        return "Unknown", 0, 0

def get_attack_data():
    result = subprocess.run(["docker", "logs", "cowrie"], capture_output=True, text=True)
    logs = result.stdout + result.stderr
    attacks = defaultdict(lambda: {
        "ip": "", "country": "", "lat": 0, "lon": 0,
        "connections": 0, "login_attempts": 0,
        "successful_logins": [], "commands": []
    })
    for line in logs.split("\n"):
        conn = re.search(r"New connection: (\d+\.\d+\.\d+\.\d+)", line)
        if conn:
            ip = conn.group(1)
            if not ip.startswith("172."):
                attacks[ip]["ip"] = ip
                attacks[ip]["connections"] += 1
        login = re.search(r"\[HoneyPotSSHTransport,\d+,(\d+\.\d+\.\d+\.\d+)\] login attempt \[b'(.+)'/b'(.+)'\] (failed|succeeded)", line)
        if login:
            ip = login.group(1)
            attacks[ip]["ip"] = ip
            attacks[ip]["login_attempts"] += 1
            if login.group(4) == "succeeded":
                attacks[ip]["successful_logins"].append({
                    "username": login.group(2),
                    "password": login.group(3)
                })
        cmd = re.search(r"\[SSHChannel.+,(\d+\.\d+\.\d+\.\d+)\] Command found: (.+)", line)
        if cmd:
            ip = cmd.group(1)
            attacks[ip]["ip"] = ip
            attacks[ip]["commands"].append(cmd.group(2).strip())
    for ip in attacks:
        country, lat, lon = get_country(ip)
        attacks[ip]["country"] = country
        attacks[ip]["lat"] = lat
        attacks[ip]["lon"] = lon
    return [v for v in attacks.values() if v["ip"]]

HTML = '''<!DOCTYPE html>
<html>
<head>
<title>Honeypot SOC Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#080c14; color:#c9d1d9; min-height:100vh; }
header { background:#0d1117; border-bottom:1px solid #21262d; padding:1rem 2rem; display:flex; align-items:center; justify-content:space-between; }
header h1 { font-size:1rem; font-weight:600; color:#fff; letter-spacing:0.02em; }
.live { display:flex; align-items:center; gap:6px; font-size:12px; color:#3fb950; }
.dot { width:8px; height:8px; border-radius:50%; background:#3fb950; animation:pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
main { padding:1.5rem 2rem; max-width:1400px; margin:0 auto; }
.stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1rem; margin-bottom:1.5rem; }
.stat { background:#0d1117; border:1px solid #21262d; border-radius:8px; padding:1.25rem; }
.stat-label { font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px; }
.stat-value { font-size:2rem; font-weight:600; color:#fff; }
.stat-value.danger { color:#f85149; }
.stat-value.warning { color:#e3b341; }
.stat-value.success { color:#3fb950; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; }
.grid-3 { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:1rem; margin-bottom:1rem; }
.card { background:#0d1117; border:1px solid #21262d; border-radius:8px; padding:1.25rem; }
.card-title { font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:1rem; font-weight:600; }
.ip-row { display:flex; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid #161b22; font-size:13px; }
.ip-row:last-child { border-bottom:none; }
.ip { font-family:"SF Mono",Monaco,monospace; color:#58a6ff; min-width:135px; font-size:12px; }
.country { color:#8b949e; flex:1; font-size:12px; }
.bar-wrap { width:80px; background:#161b22; border-radius:2px; height:4px; }
.bar-fill { height:4px; background:#1f6feb; border-radius:2px; }
.count { font-weight:600; color:#e6edf3; font-size:13px; min-width:28px; text-align:right; }
.login-row { display:flex; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid #161b22; font-size:12px; }
.login-row:last-child { border-bottom:none; }
.login-ip { font-family:"SF Mono",Monaco,monospace; color:#58a6ff; min-width:120px; font-size:11px; }
.login-user { font-family:"SF Mono",Monaco,monospace; color:#e6edf3; min-width:80px; }
.login-pass { font-family:"SF Mono",Monaco,monospace; color:#8b949e; flex:1; }
.badge { font-size:10px; padding:2px 8px; border-radius:12px; font-weight:600; }
.badge-success { background:rgba(63,185,80,0.15); color:#3fb950; border:1px solid rgba(63,185,80,0.3); }
.badge-fail { background:rgba(248,81,73,0.1); color:#f85149; border:1px solid rgba(248,81,73,0.2); }
.cmd-row { display:flex; gap:10px; padding:6px 0; border-bottom:1px solid #161b22; font-size:12px; font-family:"SF Mono",Monaco,monospace; }
.cmd-row:last-child { border-bottom:none; }
.cmd-ip { color:#58a6ff; min-width:120px; font-size:11px; white-space:nowrap; }
.cmd-text { color:#8b949e; word-break:break-all; }
#map { width:100%; height:220px; }
#map path { stroke:#21262d; stroke-width:0.5; }
footer { text-align:center; padding:1rem; font-size:11px; color:#484f58; border-top:1px solid #21262d; margin-top:1rem; }
</style>
</head>
<body>
<header>
  <h1>Honeypot SOC Dashboard</h1>
  <div class="live"><div class="dot"></div><span id="live-time">Live</span></div>
</header>
<main>
  <div class="stat-grid" id="stats"></div>
  <div class="grid-2" style="margin-bottom:1rem;">
    <div class="card"><div class="card-title">World attack map</div><svg id="map"></svg></div>
    <div class="card"><div class="card-title">Attack origins</div><div style="position:relative;height:200px;"><canvas id="countryChart" role="img" aria-label="Attacks by country">Attacks by country.</canvas></div></div>
  </div>
  <div class="grid-2" style="margin-bottom:1rem;">
    <div class="card"><div class="card-title">Top attackers</div><div id="attackers"></div></div>
    <div class="card"><div class="card-title">Successful logins</div><div id="logins"></div></div>
  </div>
  <div class="card"><div class="card-title">Commands executed by attackers</div><div id="commands"></div></div>
</main>
<footer id="footer">Loading...</footer>

<script>
let countryChartInstance = null;

async function loadData() {
  const res = await fetch('/api/attacks');
  const data = await res.json();

  const totalConn = data.reduce((s,a)=>s+a.connections,0);
  const totalAttempts = data.reduce((s,a)=>s+a.login_attempts,0);
  const totalSuccess = data.reduce((s,a)=>s+a.successful_logins.length,0);
  const totalCmds = data.reduce((s,a)=>s+a.commands.length,0);
  const countries = new Set(data.map(a=>a.country)).size;

  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="stat-label">Total connections</div><div class="stat-value">${totalConn}</div></div>
    <div class="stat"><div class="stat-label">Unique attackers</div><div class="stat-value warning">${data.length}</div></div>
    <div class="stat"><div class="stat-label">Login attempts</div><div class="stat-value warning">${totalAttempts}</div></div>
    <div class="stat"><div class="stat-label">Successful logins</div><div class="stat-value danger">${totalSuccess}</div></div>
    <div class="stat"><div class="stat-label">Commands captured</div><div class="stat-value">${totalCmds}</div></div>
    <div class="stat"><div class="stat-label">Countries</div><div class="stat-value">${countries}</div></div>
  `;

  const sorted = [...data].sort((a,b)=>b.connections-a.connections).slice(0,10);
  const max = sorted[0]?.connections||1;
  document.getElementById('attackers').innerHTML = sorted.map(a=>`
    <div class="ip-row">
      <span class="ip">${a.ip}</span>
      <span class="country">${a.country}</span>
      <div class="bar-wrap"><div class="bar-fill" style="width:${Math.round((a.connections/max)*100)}%"></div></div>
      <span class="count">${a.connections}</span>
    </div>`).join('');

  const allLogins = data.flatMap(a=>a.successful_logins.map(l=>({...l,ip:a.ip})));
  document.getElementById('logins').innerHTML = allLogins.length ? allLogins.map(l=>`
    <div class="login-row">
      <span class="login-ip">${l.ip}</span>
      <span class="login-user">${l.username}</span>
      <span class="login-pass">${l.password}</span>
      <span class="badge badge-success">in</span>
    </div>`).join('') : '<p style="color:#484f58;font-size:13px;">No successful logins yet</p>';

  const allCmds = data.flatMap(a=>a.commands.map(c=>({ip:a.ip,cmd:c})));
  document.getElementById('commands').innerHTML = allCmds.length ? allCmds.map(c=>`
    <div class="cmd-row">
      <span class="cmd-ip">${c.ip}</span>
      <span class="cmd-text">${c.cmd}</span>
    </div>`).join('') : '<p style="color:#484f58;font-size:13px;">No commands yet</p>';

  const countryCounts = {};
  data.forEach(a=>{ countryCounts[a.country]=(countryCounts[a.country]||0)+a.connections; });
  const sortedC = Object.entries(countryCounts).sort((a,b)=>b[1]-a[1]);

  if(countryChartInstance) countryChartInstance.destroy();
  countryChartInstance = new Chart(document.getElementById('countryChart'),{
    type:'bar',
    data:{
      labels:sortedC.map(c=>c[0]),
      datasets:[{data:sortedC.map(c=>c[1]),backgroundColor:'#1f6feb',borderRadius:4,borderWidth:0}]
    },
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        y:{beginAtZero:true,ticks:{color:'#8b949e',font:{size:11}},grid:{color:'#161b22'}},
        x:{ticks:{color:'#8b949e',font:{size:10},maxRotation:45},grid:{display:false}}
      }
    }
  });

  drawMap(data);
  document.getElementById('footer').textContent = 'Last updated: ' + new Date().toLocaleTimeString() + ' — Auto-refreshes every 60s';
  document.getElementById('live-time').textContent = new Date().toLocaleTimeString();
}

function drawMap(data) {
  const svg = d3.select('#map');
  svg.selectAll('*').remove();
  const w = document.getElementById('map').parentElement.clientWidth - 40;
  const h = 220;
  svg.attr('viewBox', `0 0 ${w} ${h}`).attr('width','100%').attr('height',h);
  const projection = d3.geoNaturalEarth1().scale(w/6.5).translate([w/2, h/2]);
  const path = d3.geoPath(projection);
  d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json').then(world=>{
    svg.selectAll('path').data(topojson.feature(world,world.objects.countries).features)
      .join('path').attr('d',path).attr('fill','#161b22').attr('stroke','#21262d').attr('stroke-width',0.5);
    data.forEach(a=>{
      if(a.lat&&a.lon){
        const coords = projection([a.lon,a.lat]);
        if(coords){
          const r = Math.min(3+a.connections*0.3,12);
          svg.append('circle')
            .attr('cx',coords[0]).attr('cy',coords[1])
            .attr('r',r).attr('fill','#f85149').attr('opacity',0.75)
            .append('title').text(`${a.ip} (${a.country}) — ${a.connections} connections`);
        }
      }
    });
  });
}

loadData();
setInterval(loadData, 60000);
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/attacks')
def api_attacks():
    return jsonify(get_attack_data())

if __name__ == '__main__':
    import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.run(host='0.0.0.0', port=5000, debug=False)
