import network
import socket
import machine
import time
import os
import ujson

# ---- CONFIGURATION ----
LOG_SERVER_IP = '192.168.x.x'  # <-- Your PC IP for UDP logs
LOG_SERVER_PORT = 12345
UPLOAD_FILENAME = 'main.py'
WIFI_FILE = 'wifi.json'
RELAY_PIN = 13

# ---- LOGGING ----
try:
    log_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    network_ready = True
except:
    log_socket = None
    network_ready = False

def log(message):
    try:
        if network_ready and log_socket:
            print(f"[sending log] {message}")
            log_socket.sendto((message + '\n').encode('utf-8'), (LOG_SERVER_IP, LOG_SERVER_PORT))
        else:
            print(message)
    except Exception as e:
        print("[LOG ERROR]", e)
        print(message)

# ---- RELAY SETUP ----
relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
relay.value(0)

# ---- Wi-Fi Functions ----
def save_wifi_credentials(ssid, password):
    data = {"ssid": ssid, "password": password}
    with open(WIFI_FILE, 'w') as f:
        ujson.dump(data, f)
    log(f"Saved WiFi credentials for SSID: {ssid}")

def load_wifi_credentials():
    try:
        with open(WIFI_FILE, 'r') as f:
            data = ujson.load(f)
            return data['ssid'], data['password']
    except Exception as e:
        log(f"Failed to load WiFi credentials: {e}")
        return None, None

def connect_wifi():
    ssid, password = load_wifi_credentials()
    if ssid is None or password is None:
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    timeout = 15
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        log(f'Connected to WiFi: {wlan.ifconfig()}')

        ap = network.WLAN(network.AP_IF)
        if ap.active():
            ap.active(False)
            log("Disabled Access Point after successful WiFi connection.")

        return True
    else:
        log('Failed to connect to WiFi.')
        return False

def start_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP-Setup", password="12345678")
    log(f"Access Point started: SSID ESP-Setup, IP: {ap.ifconfig()[0]}")
    return ap

# ---- HTTP SERVER ----
def start_http_server(port=8080):
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    log(f'Server listening on {addr}')

    while True:
        cl, addr = s.accept()
        log(f'Client connected: {addr}')
        try:
            cl_file = cl.makefile('rwb', 0)
            request_line = cl_file.readline()
            log(f"Request: {request_line}")

            if not request_line:
                cl.close()
                continue

            method, path, _ = request_line.decode().split(' ')

            # Parse headers
            content_length = 0
            while True:
                header = cl_file.readline()
                if header == b'\r\n' or header == b'':
                    break
                if header.lower().startswith(b'content-length:'):
                    content_length = int(header.split(b':')[1].strip())

            log(f"Content-Length: {content_length}")

            if method == 'POST':
                if path == '/upload':
                    handle_upload(cl_file, cl, content_length)
                elif path == '/relay':
                    handle_relay(cl_file, cl, content_length)
                elif path == '/setup_wifi':
                    handle_setup_wifi(cl_file, cl, content_length)
                else:
                    send_response(cl, 404, "Invalid Path")
            else:
                send_response(cl, 405, "Only POST supported")

        except Exception as e:
            log(f'Exception: {e}')
            safe_close(cl)

def handle_upload(cl_file, cl, content_length):
    log("Handling /upload...")
    body = cl_file.read(content_length)
    with open(UPLOAD_FILENAME, 'w') as f:
        f.write(body.decode('utf-8'))
    send_response(cl, 200, "Upload successful. Rebooting...")
    log('main.py updated. Rebooting...')
    machine.reset()

def handle_relay(cl_file, cl, content_length):
    log("Handling /relay...")
    body = cl_file.read(content_length)
    command = body.decode('utf-8').strip().lower()
    log(f"Relay command: {command}")

    if command == 'on':
        relay.value(1)
        log("Relay ON")
        send_response(cl, 200, "Relay turned ON.")
    elif command == 'off':
        relay.value(0)
        log("Relay OFF")
        send_response(cl, 200, "Relay turned OFF.")
    else:
        send_response(cl, 400, "Invalid relay command.")

def handle_setup_wifi(cl_file, cl, content_length):
    log("Handling /setup_wifi...")
    body = cl_file.read(content_length)
    try:
        data = ujson.loads(body)
        ssid = data.get('ssid')
        password = data.get('password')
        if ssid and password:
            save_wifi_credentials(ssid, password)
            send_response(cl, 200, "WiFi credentials saved. Rebooting...")
            log('WiFi credentials saved. Rebooting...')
            time.sleep(2)
            machine.reset()
        else:
            send_response(cl, 400, "Invalid WiFi setup data.")
    except Exception as e:
        log(f"WiFi setup error: {e}")
        send_response(cl, 400, "Invalid JSON format.")

# ---- LOW-LEVEL HELPERS ----
def send_response(cl, status_code, message):
    response_body = message
    response_headers = (
        f'HTTP/1.1 {status_code} OK\r\n'
        'Content-Type: text/plain\r\n'
        f'Content-Length: {len(response_body)}\r\n'
        'Connection: close\r\n'
        '\r\n'
    )
    full_response = response_headers + response_body

    try:
        cl.send(full_response.encode())
        cl.shutdown(socket.SHUT_WR)
    except Exception as e:
        log(f"Error sending response: {e}")
    finally:
        safe_close(cl)

def safe_close(cl):
    try:
        cl.close()
    except:
        pass

# ---- MAIN ----

log("Booting device...")
time.sleep(1)

if not connect_wifi():
    log("Failed to connect WiFi. Starting AP mode...")
    start_access_point()

start_http_server(port=8080)
