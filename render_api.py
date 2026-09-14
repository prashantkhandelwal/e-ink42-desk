import socket

from config_loader import API_MAX_REQUEST_BYTES, API_PORT, CONFIG, save_config

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
    print("Settings: http://{}:{}/settings".format(wlan.ifconfig()[0], API_PORT))
    return server


def send_all(client, data):
    offset = 0
    while offset < len(data):
        sent = client.send(data[offset:offset + 1024])
        if not sent:
            raise OSError("Socket closed while sending response")
        offset += sent


def send_http_response(client, status, body, content_type="application/json"):
    encoded_body = body.encode()
    headers = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: {}; charset=utf-8\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n"
    ).format(status, content_type, len(encoded_body))
    send_all(client, headers.encode())
    send_all(client, encoded_body)


def send_http_redirect(client, location):
    response = (
        "HTTP/1.1 303 See Other\r\n"
        "Location: {}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n\r\n"
    ).format(location)
    send_all(client, response.encode())


def escape_html(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def settings_page(saved=False):
    notice = '<p class="notice">Settings saved and display refresh queued.</p>' if saved else ""
    feed_buttons = "".join(
        '<button class="feed-button" type="submit" name="feed_index" value="{}">{}</button>'.format(
            index, escape_html(feed["name"])
        )
        for index, feed in enumerate(CONFIG.get("feeds", []))
    )
    with open("settings.html", "r") as html_file:
        page = html_file.read()
    return (
        page.replace("{{notice}}", notice)
        .replace("{{stock_symbol}}", escape_html(CONFIG.get("stock_symbol", "MSFT")))
        .replace("{{location_name}}", escape_html(CONFIG.get("location_name", "")))
        .replace("{{feed_buttons}}", feed_buttons)
    )


def url_decode(value):
    result = bytearray()
    index = 0
    while index < len(value):
        if value[index] == "+":
            result.append(32)
        elif value[index] == "%" and index + 2 < len(value):
            result.append(int(value[index + 1:index + 3], 16))
            index += 2
        else:
            result.extend(value[index].encode("utf-8"))
        index += 1
    return result.decode("utf-8")


def parse_settings(body):
    fields = {}
    for pair in body.decode().split("&"):
        name, separator, value = pair.partition("=")
        if separator:
            fields[url_decode(name)] = url_decode(value)

    symbol = fields.get("stock_symbol", "").strip().upper()
    if not symbol or len(symbol) > 10 or not all(
        character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        for character in symbol
    ):
        raise ValueError("Invalid stock symbol")

    location_name = fields.get("location_name", "").strip()
    if len(location_name) > 48 or any(
        ord(character) < 32 or 127 <= ord(character) <= 159
        for character in location_name
    ):
        raise ValueError("Invalid location name")

    return {
        "stock_symbol": symbol,
        "location_name": location_name,
    }


def parse_feed_index(body):
    fields = {}
    for pair in body.decode().split("&"):
        name, separator, value = pair.partition("=")
        if separator:
            fields[url_decode(name)] = url_decode(value)

    try:
        feed_index = int(fields.get("feed_index", ""))
    except ValueError:
        raise ValueError("Invalid feed selection")
    if feed_index < 0 or feed_index >= len(CONFIG.get("feeds", [])):
        raise ValueError("Invalid feed selection")
    return feed_index


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
                    if separator and name.strip().lower() == "content-length":
                        content_length = int(value.strip())
        if header_end >= 0 and len(request) >= header_end + 4 + content_length:
            break

    if header_end < 0 or len(request) >= API_MAX_REQUEST_BYTES:
        raise ValueError("Invalid or oversized request")
    if len(request) < header_end + 4 + content_length:
        raise ValueError("Incomplete request body")
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
        client.settimeout(5)
        method, path, body = read_http_request(client)
        path_with_query = path
        path = path.split("?", 1)[0]
        if method == "GET" and path == "/health":
            send_http_response(client, "200 OK", '{"status":"ok"}')
            return None
        if method == "GET" and path in ("/", "/settings"):
            saved = "saved=1" in path_with_query
            send_http_response(client, "200 OK", settings_page(saved), "text/html")
            return None
        if method == "POST" and path == "/settings":
            settings = parse_settings(body)
            save_config(settings)
            send_http_redirect(client, "/settings?saved=1")
            return {"type": "settings", "settings": settings}
        if method == "POST" and path == "/dashboard":
            send_http_redirect(client, "/settings")
            return {"type": "dashboard"}
        if method == "POST" and path == "/feed":
            feed_index = parse_feed_index(body)
            send_http_redirect(client, "/settings")
            return {"type": "feed", "feed_index": feed_index}
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
        return {"type": "render", "payload": payload}
    except Exception as error:
        print("API request failed:", error)
        try:
            send_http_response(
                client,
                "400 Bad Request",
                json.dumps({"error": str(error)}),
            )
        except Exception:
            pass
        return None
    finally:
        client.close()