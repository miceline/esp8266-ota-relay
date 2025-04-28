import network
import machine
import time
import ujson
import ntptime
from machine import ADC

TIMEZONE_OFFSET_HOURS = -4 # Aruba
relay = machine.Pin(16, machine.Pin.OUT)
relay.value(0)
adc = ADC(0)

relay_timeout_minutes = 5
relay_timer_end = None 

boot_time = time.time()

def relay_on():
    global relay_timer_end
    relay.value(1)
    relay_timer_end = time.time() + relay_timeout_minutes * 60

def relay_off():
    global relay_timer_end
    relay.value(0)
    relay_timer_end = None

def relay_status():
    return "on" if relay.value() else "off"

def check_relay_timer():
    global relay_timer_end
    if relay_timer_end and time.time() >= relay_timer_end:
        print("Relay auto-off timeout reached.")
        relay_off()

def set_relay_timeout(minutes):
    global relay_timeout_minutes
    relay_timeout_minutes = minutes

def read_pressure():
    raw_value = adc.read()
    voltage = (raw_value / 1024.0) * 1.0
    pressure = (voltage / 1.0) * 100  # Adjust if needed
    return pressure

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    timeout = 15
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
    return wlan.isconnected()

def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP-Setup", password="12345678")

def save_wifi_credentials(ssid, password):
    with open('wifi.json', 'w') as f:
        ujson.dump({"ssid": ssid, "password": password}, f)

def save_udp_config(ip, port):
    with open('udp.json', 'w') as f:
        ujson.dump({"ip": ip, "port": int(port)}, f)

def sync_time():
    try:
        ntptime.settime()
        tm = time.localtime(time.time() + TIMEZONE_OFFSET_HOURS * 3600)
        return tm
    except Exception as e:
        return e
    
def get_status():
    wlan = network.WLAN(network.STA_IF)
    ip = wlan.ifconfig()[0] if wlan.isconnected() else None

    now = time.time() + TIMEZONE_OFFSET_HOURS * 3600
    tm = time.localtime(now)

    date_str = "%04d-%02d-%02d %02d:%02d:%02d" % (tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])

    uptime = time.time() - boot_time

    if relay_timer_end:
        seconds_left = int(relay_timer_end - time.time())
        if seconds_left < 0:
            seconds_left = 0
    else:
        seconds_left = 0

    return {
        "ip": ip,
        "time": date_str,
        "uptime_seconds": int(uptime),
        "wifi_connected": wlan.isconnected(),
        "relay_status": relay_status(),
        "relay_auto_off_seconds_left": seconds_left,
    }
