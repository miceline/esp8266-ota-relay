import network
import socket
import os
import machine

# Configuration
PORT = 8080

# Start WiFi Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP-Recovery", password="12345678")
print("Access Point started:", ap.ifconfig())

# Parse query string
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

# Handle upload
def handle_upload(cl_file, cl, content_length, filename):
    print(f"Receiving upload for {filename}...")

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

        print(f"Upload of {filename} complete. ✅")
        send_response(cl, 200, "Upload successful. Please upload all files manually, then reboot manually.")

    except Exception as e:
        print(f"Upload failed: {e}")
        send_response(cl, 500, "Upload failed.")

# Send basic HTTP response
def send_response(cl, status_code, message):
    response = f"HTTP/1.1 {status_code} OK\r\nContent-Type: text/plain\r\nContent-Length: {len(message)}\r\nConnection: close\r\n\r\n{message}"
    cl.send(response.encode())
    cl.close()

# Start simple HTTP server
addr = socket.getaddrinfo('0.0.0.0', PORT)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print(f"Listening for uploads on port {PORT}...")

while True:
    cl, addr = s.accept()
    print(f"Client connected: {addr}")

    cl_file = cl.makefile('rwb', 0)
    request_line = cl_file.readline()

    if not request_line:
        cl.close()
        continue

    method, full_path, _ = request_line.decode().split(' ')
    path, params = parse_query(full_path)

    content_length = 0
    while True:
        header = cl_file.readline()
        if header == b'\r\n' or header == b'':
            break
        if header.lower().startswith(b'content-length:'):
            content_length = int(header.split(b':')[1].strip())

    if method == 'POST' and path == '/upload':
        filename = params.get('filename', 'uploaded.py')
        handle_upload(cl_file, cl, content_length, filename)
    else:
        send_response(cl, 404, "Invalid path")
