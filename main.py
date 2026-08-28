flask
paho-mqtt
import os
import random
import threading
from flask import Flask, render_template_string, request, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)

# Data tracking structure cache holds information across router reboots
telemetry = {
    "hitachi_pct": "--", "hitachi_ltr": "--",
    "kaveri_pct": "--", "kaveri_ltr": "--",
    "sump_pct": "--", "sump_ltr": "--"
}

def on_connect(client, userdata, flags, rc):
    print(f"Cloud Server Connected to Shiftr Broker Grid with Return Code: {rc}")
    client.subscribe("home/water/status/#")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Network Data Received -> Topic: {topic} | Payload: {payload}")
    
    if "hitachi_pct" in topic: telemetry["hitachi_pct"] = payload
    elif "hitachi_litres" in topic: telemetry["hitachi_ltr"] = payload
    elif "kaveri_pct" in topic: telemetry["kaveri_pct"] = payload
    elif "kaveri_litres" in topic: telemetry["kaveri_ltr"] = payload
    elif "sump_pct" in topic: telemetry["sump_pct"] = payload
    elif "sump_litres" in topic: telemetry["sump_ltr"] = payload

# Initialize background client connectivity loops with randomized seeds
client_id = f"Render_Cloud_Varun_{random.randint(1000, 9999)}"
mqtt_client = mqtt.Client(client_id=client_id)
mqtt_client.username_pw_set("water-station", "Kxf68JkbfTYY7Ot9")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    while True:
        try:
            print("Opening outbound web pipe connection link to shiftr.io...")
            mqtt_client.connect("water-station.cloud.shiftr.io", 1883, 60)
            mqtt_client.loop_forever()
        except Exception as e:
            print(f"Broker connection blip, retrying background thread execution: {e}")
            import time
            time.sleep(5)

threading.Thread(target=start_mqtt, daemon=True).start()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Global Water Command Center</title>
    <style>
        body { font-family: sans-serif; background: #0b111e; color: #fff; text-align: center; padding: 15px; margin: 0; }
        .bar { padding: 12px; font-size: 13px; font-weight: bold; letter-spacing: 1px; border-radius: 6px; margin-bottom: 15px; background: #10b981; box-shadow: 0 3px 12px rgba(16,185,129,0.3); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; max-width: 1000px; margin: 0 auto; }
        .card { background: #172237; border: 1px solid #26354a; border-radius: 12px; padding: 20px; }
        .title { color: #8a99ad; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
        .val { font-size: 36px; font-weight: bold; color: #3b82f6; }
        .litres { font-size: 14px; color: #64748b; margin-top: 4px; }
        button { width: 100%; padding: 14px; margin-top: 15px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:active { background: #1d4ed8; transform: scale(0.98); }
    </style>
    <script>
        // Automatic background fetch loop queries internal cloud variables every 2 seconds without full refreshes
        setInterval(async () => {
            try {
                let res = await fetch('/data');
                let data = await res.json();
                document.getElementById('h_pct').innerText = data.hitachi_pct + "%";
                document.getElementById('h_ltr').innerText = data.hitachi_ltr + " L";
                document.getElementById('k_pct').innerText = data.kaveri_pct + "%";
                document.getElementById('k_ltr').innerText = data.kaveri_ltr + " L";
                document.getElementById('s_pct').innerText = data.sump_pct + "%";
                document.getElementById('s_ltr').innerText = data.sump_ltr + " L";
            } catch(e) { console.log("Data sync issue:", e); }
        }, 2000);
        
        async function triggerRelay(tank) {
            await fetch('/trigger?tank=' + tank);
        }
    </script>
</head>
<body>
    <div class="bar">🌐 GLOBAL CLOUD CORE CONNECTION LIVE</div>
    <h2>GLOBAL WATER COMMAND PANEL</h2>
    <p style="color: #64748b; font-size: 13px; margin-top: -8px; margin-bottom: 25px;">SECURE MONITORING OVER THE INTERNET FOR THE WHOLE FAMILY</p>
    
    <div class="grid">
        <div class="card"><div class="title">Hitachi Overhead</div><div class="val" id="h_pct">--%</div><div class="litres" id="h_ltr">-- L</div><button onclick="triggerRelay('hitachi')">PULSE MOTOR</button></div>
        <div class="card"><div class="title">Kaveri Overhead</div><div class="val" id="k_pct" style="color:#a855f7;">--%</div><div class="litres" id="k_ltr">-- L</div><button onclick="triggerRelay('kaveri')" style="background:#a855f7;">PULSE MOTOR</button></div>
        <div class="card"><div class="title">Underground Sump</div><div class="val" id="s_pct" style="color:#10b981;">--%</div><div class="litres" id="s_ltr">-- L</div><div style="font-size: 11px; color: #475569; margin-top: 25px;">Continuous Feed Active</div></div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/data')
def get_data():
    return jsonify(telemetry)

@app.route('/trigger')
def trigger():
    target = request.args.get('tank')
    if target == 'hitachi':
        mqtt_client.publish("home/water/control/hitachi", "START")
    elif target == 'kaveri':
        mqtt_client.publish("home/water/control/kaveri", "START")
    return "OK"

if __name__ == '__main__':
    # Binds to the secure dynamic web port assigned by the cloud platform
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
