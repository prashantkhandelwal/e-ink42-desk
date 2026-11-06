import errno
import socket
import time

from config_loader import API_MAX_REQUEST_BYTES, API_PORT, CONFIG, save_config

try:
    import ujson as json
except ImportError:
    import json


API_REQUEST_IDLE_TIMEOUT_MS = 15_000
API_MAX_PENDING_CLIENTS = 4
WOULD_BLOCK_ERRORS = (
    errno.EAGAIN,
    getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
    getattr(errno, "WSAEWOULDBLOCK", errno.EAGAIN),
)


class PendingRequest:
    def __init__(self, client):
        self.client = client
        self.data = b""
        self.header_end = -1
        self.content_length = 0
        self.last_activity = time.ticks_ms()


class RenderApiServer:
    def __init__(self, listener):
        self.listener = listener
        self.pending_requests = []


def create_api_server(wlan):
    address = socket.getaddrinfo("0.0.0.0", API_PORT)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(address)
    server.listen(4)
    server.setblocking(False)
    print("Render API: http://{}:{}/render".format(wlan.ifconfig()[0], API_PORT))
    print("Settings: http://{}:{}/settings".format(wlan.ifconfig()[0], API_PORT))
    return RenderApiServer(server)


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


def send_action_response(client, message):
    body = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>E-Ink Desk</title></head><body>"
        "<p>{}</p><p><a href=\"/settings\">Back to settings</a></p>"
        "</body></html>"
    ).format(escape_html(message))
    send_http_response(client, "202 Accepted", body, "text/html")


def escape_html(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def settings_page(saved=False, notice_text=None):
    if notice_text is None and saved:
        notice_text = "Settings saved and display refresh queued."
    notice = (
        '<p class="notice">{}</p>'.format(escape_html(notice_text))
        if notice_text
        else ""
    )
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


def read_http_request(request):
    try:
        chunk = request.client.recv(min(1024, API_MAX_REQUEST_BYTES - len(request.data)))
    except OSError as error:
        if not error.args or error.args[0] not in WOULD_BLOCK_ERRORS:
            raise
        if time.ticks_diff(time.ticks_ms(), request.last_activity) >= API_REQUEST_IDLE_TIMEOUT_MS:
            if not request.data:
                raise EOFError("Idle connection timed out without sending a request")
            raise OSError(errno.ETIMEDOUT)
        return None

    if not chunk:
        if request.data:
            raise ValueError("Incomplete request")
        raise EOFError("Connection closed without sending a request")
    request.data += chunk
    request.last_activity = time.ticks_ms()
    if request.header_end < 0:
        request.header_end = request.data.find(b"\r\n\r\n")
        if request.header_end >= 0:
            for header in request.data[:request.header_end].decode().split("\r\n")[1:]:
                name, separator, value = header.partition(":")
                if separator and name.strip().lower() == "content-length":
                    request.content_length = int(value.strip())
            if request.content_length < 0:
                raise ValueError("Invalid Content-Length")

    expected_length = request.header_end + 4 + request.content_length
    if request.header_end >= 0:
        if expected_length > API_MAX_REQUEST_BYTES:
            raise ValueError("Oversized request")
        if len(request.data) >= expected_length:
            header = request.data[:request.header_end].decode()
            method, path, _ = header.split("\r\n", 1)[0].split(" ", 2)
            body = request.data[request.header_end + 4:expected_length]
            return method, path, body
    if len(request.data) >= API_MAX_REQUEST_BYTES:
        raise ValueError("Invalid or oversized request")
    return None


def handle_http_request(client, method, path, body):
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
        send_action_response(client, "Settings saved. Display update queued.")
        return {"type": "settings", "settings": settings}
    if method == "POST" and path == "/dashboard":
        send_action_response(client, "Dashboard display update queued.")
        return {"type": "dashboard"}
    if method == "POST" and path == "/feed":
        feed_index = parse_feed_index(body)
        send_action_response(client, "Feed selected. Display update queued.")
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


def poll_render_api(server):
    if server is None:
        return None

    if len(server.pending_requests) < API_MAX_PENDING_CLIENTS:
        try:
            client, _ = server.listener.accept()
        except OSError as error:
            if not error.args or error.args[0] not in WOULD_BLOCK_ERRORS:
                print("API accept failed:", error)
        else:
            try:
                client.setblocking(False)
                server.pending_requests.append(PendingRequest(client))
            except Exception:
                client.close()
                raise

    for request in server.pending_requests[:]:
        client = request.client
        keep_pending = False
        stage = "reading request"
        try:
            parsed = read_http_request(request)
            if parsed is None:
                keep_pending = True
                continue
            client.settimeout(15)
            stage = "sending response"
            return handle_http_request(client, *parsed)
        except EOFError as error:
            print("API connection closed:", error)
        except Exception as error:
            print("API request failed while {}: {}".format(stage, error))
            try:
                client.settimeout(15)
                status = "400 Bad Request"
                if isinstance(error, OSError) and error.args and error.args[0] == errno.ETIMEDOUT and stage == "reading request":
                    status = "408 Request Timeout"
                send_http_response(client, status, json.dumps({"error": str(error), "stage": stage}))
            except Exception as response_error:
                print("API error response failed:", response_error)
        finally:
            if not keep_pending:
                server.pending_requests.remove(request)
                client.close()
    return None