import ujson
import os
import machine
import hardware
import logging_util
import time

def parse_query(path):
    if '?' not in path:
        return path, {}
    p, q = path.split('?', 1)
    params = {}
    for pair in q.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            params[k] = v
    return p, params

def handle_client(cl):
    cl_file = cl.makefile('rwb', 0)
    request_line = cl_file.readline()

    if not request_line:
        cl.close()
        return

    method, full_path, _ = request_line.decode().split(' ')
    path, params = parse_query(full_path)

    content_length = 0
    while True:
        header = cl_file.readline()
        if header == b'\r\n' or header == b'':
            break
        if header.lower().startswith(b'content-length:'):
            content_length = int(header.split(b':')[1].strip())

    if method == 'POST':
        if path == '/upload':
            filename = params.get('filename', 'main.py')
            upload_file(cl_file, cl, content_length, filename)
        elif path == '/relay':
            relay_control(cl_file, cl, content_length)
        elif path == '/setup_wifi':
            wifi_setup(cl_file, cl, content_length)
        elif path == '/setup_udp':
            udp_setup(cl_file, cl, content_length)
        else:
            send_response(cl, 404, "Invalid Path")
    elif method == 'GET':
        if path == '/read_pressure':
            read_pressure(cl)
        elif path == '/status':
            serve_status(cl)
        elif path == '/reboot':
            send_response(cl, 200, "Rebooting...")
            logging_util.log("Rebooting...")
            time.sleep(2)
            machine.reset()
        else:
            send_response(cl, 404, "Invalid Path")
    else:
        send_response(cl, 405, "Only POST/GET supported")

    cl.close()

def serve_status(cl):
    status = hardware.get_status()
    body = ujson.dumps(status)
    send_response(cl, 200, body)

def upload_file(cl_file, cl, content_length, filename):
    logging_util.log(f"Uploading {filename}...")
    try:
        with open(filename, 'w') as f:
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
        send_response(cl, 200, "Upload successful.")
        logging_util.log(f"{filename} uploaded.")
    except Exception as e:
        logging_util.log(f"Upload error: {e}")
        send_response(cl, 500, "Upload failed.")

def relay_control(cl_file, cl, content_length):
    body = cl_file.read(content_length)
    command = body.decode('utf-8').strip().lower()
    if command == 'on':
        hardware.relay_on()
        send_response(cl, 200, "Relay turned ON.")
    elif command == 'off':
        hardware.relay_off()
        send_response(cl, 200, "Relay turned OFF.")
    else:
        send_response(cl, 400, "Invalid relay command.")

def wifi_setup(cl_file, cl, content_length):
    body = cl_file.read(content_length)
    try:
        data = ujson.loads(body)
        ssid = data.get('ssid')
        password = data.get('password')
        if ssid and password:
            hardware.save_wifi_credentials(ssid, password)
            send_response(cl, 200, "WiFi saved. Rebooting...")
            machine.reset()
        else:
            send_response(cl, 400, "Invalid WiFi data.")
    except:
        send_response(cl, 400, "Invalid WiFi JSON.")

def udp_setup(cl_file, cl, content_length):
    body = cl_file.read(content_length)
    try:
        data = ujson.loads(body)
        ip = data.get('ip')
        port = data.get('port')
        if ip and port:
            hardware.save_udp_config(ip, port)
            send_response(cl, 200, "UDP settings saved. Rebooting...")
            machine.reset()
        else:
            send_response(cl, 400, "Invalid UDP data.")
    except:
        send_response(cl, 400, "Invalid UDP JSON.")

def read_pressure(cl):
    pressure = hardware.read_pressure()
    response = '{"pressure": %.2f}' % pressure
    send_response(cl, 200, response)

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
    except:
        pass
