import network
import socket
import machine
import time
import os
import ujson
import sys
import select
from machine import ADC

# ---- CONFIGURATION ----
UPLOAD_FILENAME = 'main.py'
WIFI_FILE = 'wifi.json'
UDP_FILE = 'udp.json'
RELAY_PIN = 13

ADC_PIN = 0
PRESSURE_MIN = 0
PRESSURE_MAX = 100

# ---- GLOBALS ----
log_socket = None
network_ready = False
udp_ip = None
udp_port = None
adc = ADC(ADC_PIN)

# ---- LOGGING ----
def load_udp_config():
    global udp_ip, udp_port
    try:
        with open(UDP_FILE, 'r') as f:
            data = ujson.load(f)
            udp_ip = data['ip']
            udp_port = int(data['port'])
            log(f"Loaded UDP config: {udp_ip}:{udp_port}")
    except Exception as e:
        print(f"Failed to load UDP config: {e}")
        udp_ip = None
        udp_port = None

def setup_log_socket():
    global log_socket, network_ready
    try:
        log_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        network_ready = True
    except:
        log_socket = None
        network_ready = False

def log(message):
    try:
        if network_ready and log_socket and udp_ip and udp_port:
            print(f"[sending log] {message}")
            log_socket.sendto((message + '\n').encode('utf-8'), (udp_ip, udp_port))
        else:
            print(message)
    except Exception as e:
        print("[LOG ERROR]", e)
        print(message)

# ---- RELAY SETUP ----
relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
relay.value(0)

# ---- WIFI FUNCTIONS ----
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

# ---- ADC PRESSURE SENSOR ----
def read_pressure_sensor():
    raw_value = adc.read()
    voltage = (raw_value / 1024.0) * 1.0
    pressure = (voltage / 1.0) * (PRESSURE_MAX - PRESSURE_MIN) + PRESSURE_MIN
    return pressure

# ---- HTTP HANDLERS ----
def handle_client(cl, addr):
    log(f'Client connected: {addr}')
    try:
        cl_file = cl.makefile('rwb', 0)
        request_line = cl_file.readline()
        log(f"Request: {request_line}")

        if not request_line:
            cl.close()
            return

        method, path, _ = request_line.decode().split(' ')

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
            elif path == '/setup_udp':
                handle_setup_udp(cl_file, cl, content_length)
            else:
                send_response(cl, 404, "Invalid Path")
        elif method == 'GET':
            if path == '/read_pressure':
                handle_read_pressure(cl)
            elif path == '/reboot':
                handle_reboot(cl)
            elif path == '/':
                send_response(cl, 200, "Welcome to the ESP8266 Web Server!")
            else:
                send_response(cl, 404, "Invalid Path")
        else:
            send_response(cl, 405, "Only POST/GET supported")
    except Exception as e:
        log(f'Exception handling client: {e}')
    finally:
        safe_close(cl)

def handle_upload(cl_file, cl, content_length):
    log("Handling /upload...")
    try:
        with open(UPLOAD_FILENAME, 'w') as f:
            remaining = content_length
            while remaining > 0:
                chunk_size = 512
                if remaining < chunk_size:
                    chunk_size = remaining
                chunk = cl_file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk.decode('utf-8'))
                remaining -= len(chunk)

        send_response(cl, 200, "Upload successful. Rebooting...")
        log('main.py updated successfully. Rebooting...')
        time.sleep(1)
        machine.reset()

    except Exception as e:
        log(f"Upload error: {e}")
        send_response(cl, 500, "Upload failed.")

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

def handle_setup_udp(cl_file, cl, content_length):
    log("Handling /setup_udp...")
    body = cl_file.read(content_length)
    try:
        data = ujson.loads(body)
        ip = data.get('ip')
        port = data.get('port')
        if ip and port:
            with open(UDP_FILE, 'w') as f:
                ujson.dump({"ip": ip, "port": int(port)}, f)
            send_response(cl, 200, "UDP config saved. Rebooting...")
            log('UDP config saved. Rebooting...')
            time.sleep(2)
            machine.reset()
        else:
            send_response(cl, 400, "Invalid UDP setup data.")
    except Exception as e:
        log(f"UDP setup error: {e}")
        send_response(cl, 400, "Invalid JSON format.")

def handle_read_pressure(cl):
    log("Handling /read_pressure...")
    pressure = read_pressure_sensor()
    response = '{"pressure": %.2f}' % pressure
    send_response(cl, 200, response)

def handle_reboot(cl):
    send_response(cl, 200, "Rebooting...")
    log('Rebooting...')
    time.sleep(2)
    machine.reset()

def send_response(cl, status_code, message):
    response_body = message
    response_headers = (
        f'HTTP/1.1 {status_code} OK\r\n'
        'Content-Type: application/json\r\n'
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

# ---- SERIAL COMMANDS ----
def handle_serial_command(cmd):
    if cmd == "clear wifi":
        try:
            os.remove(WIFI_FILE)
            log("WiFi settings cleared. Rebooting...")
            time.sleep(2)
            machine.reset()
        except:
            log("Failed to clear WiFi settings.")
    elif cmd == "clear udp_log":
        try:
            os.remove(UDP_FILE)
            log("UDP log settings cleared. Rebooting...")
            time.sleep(2)
            machine.reset()
        except:
            log("Failed to clear UDP settings.")
    elif cmd == "help":
        log("Available commands:")
        log("  clear wifi     - Erase saved WiFi credentials")
        log("  clear udp_log  - Erase saved UDP logging settings")
        log("  help           - Show this help menu")
    else:
        log("Unknown command. Type 'help'.")

# ---- MAIN MULTIPLEXED LOOP ----
def main_loop(port=8080):
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    server_socket = socket.socket()
    server_socket.bind(addr)
    server_socket.listen(1)
    log(f'Server listening on {addr}')

    log("Serial command listener started. Type 'help' for options.")

    while True:
        # Check HTTP
        try:
            server_socket.settimeout(0.1)
            cl, addr = server_socket.accept()
            handle_client(cl, addr)
        except OSError:
            pass

        # Check Serial
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            cmd = sys.stdin.readline().strip().lower()
            handle_serial_command(cmd)

# ---- MAIN ----
log("Booting device...")
time.sleep(1)

load_udp_config()
setup_log_socket()

if not connect_wifi():
    log("Failed to connect WiFi. Starting AP mode...")
    start_access_point()

main_loop(port=8080)
