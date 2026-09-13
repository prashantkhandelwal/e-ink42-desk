import socket

from config_loader import API_MAX_REQUEST_BYTES, API_PORT

try:
    import ujson as json
except ImportError:
    import json


def create_api_server(wlan):
    address = socket.getaddrinfo("0.0.0.0", API_PORT)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(address)
    server.listen(1)
    server.setblocking(False)
    print("Render API: http://{}:{}/render".format(wlan.ifconfig()[0], API_PORT))
    return server


def send_http_response(client, status, body):
    response = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n{}"
    ).format(status, len(body), body)
    client.send(response.encode())


def read_http_request(client):
    request = b""
    content_length = 0
    header_end = -1

    while len(request) < API_MAX_REQUEST_BYTES:
        chunk = client.recv(min(1024, API_MAX_REQUEST_BYTES - len(request)))
        if not chunk:
            break
        request += chunk
        if header_end < 0:
            header_end = request.find(b"\r\n\r\n")
            if header_end >= 0:
                for header in request[:header_end].decode().split("\r\n")[1:]:
                    name, separator, value = header.partition(":")
                    if separator and name.lower() == "content-length":
                        content_length = int(value.strip())
        if header_end >= 0 and len(request) >= header_end + 4 + content_length:
            break

    if header_end < 0 or len(request) >= API_MAX_REQUEST_BYTES:
        raise ValueError("Invalid or oversized request")
    header = request[:header_end].decode()
    method, path, _ = header.split("\r\n", 1)[0].split(" ", 2)
    body = request[header_end + 4:header_end + 4 + content_length]
    return method, path, body


def poll_render_api(server):
    if server is None:
        return None

    try:
        client, _ = server.accept()
    except OSError:
        return None

    try:
        client.settimeout(1)
        method, path, body = read_http_request(client)
        if method == "GET" and path == "/health":
            send_http_response(client, "200 OK", '{"status":"ok"}')
            return None
        if method != "POST" or path != "/render":
            send_http_response(client, "404 Not Found", '{"error":"not found"}')
            return None

        payload = json.loads(body.decode())
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        lines = payload.get("lines")
        data = payload.get("data")
        if not isinstance(lines, list) and not isinstance(data, dict):
            raise ValueError("Expected a lines array or data object")
        send_http_response(client, "202 Accepted", '{"status":"rendering"}')
        return payload
    except Exception as error:
        print("API request failed:", error)
        try:
            send_http_response(client, "400 Bad Request", '{"error":"bad request"}')
        except Exception:
            pass
        return None
    finally:
        client.close()