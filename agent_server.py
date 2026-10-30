import http.server
import socketserver
import json
import os
import queue
import time
import urllib.parse
import threading

PORT = 8080
DIRECTORY = r'F:\svg puzzle'

# Global thread-safe queues and state
command_queue = queue.Queue()
state_lock = threading.Lock()
current_client_state = {
    "connected": False,
    "hasSvgLoaded": False,
    "fileName": "",
    "diffCount": 0,
    "dimensions": {"width": 1000, "height": 1000},
    "diffs": [],
    "lastUpdated": 0
}

# Pending action result futures
pending_results = {}
result_lock = threading.Lock()

class AgentBridgeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        # Quiet logging for SSE and polling to avoid console spam
        if '/api/agent-events' in args[0] or '/api/state' in args[0]:
            return
        super().log_message(format, *args)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        
        # 1. Server-Sent Events (SSE) Stream for Browser
        if url.path == '/api/agent-events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with state_lock:
                current_client_state["connected"] = True

            # Send initial handshake
            init_msg = json.dumps({"type": "handshake", "message": "Agent Bridge Connected"})
            self.wfile.write(f"data: {init_msg}\n\n".encode('utf-8'))
            self.wfile.flush()

            try:
                while True:
                    try:
                        # Wait for agent commands with a 2-second timeout to send heartbeats
                        cmd = command_queue.get(timeout=2.0)
                        msg = json.dumps(cmd)
                        self.wfile.write(f"data: {msg}\n\n".encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        # Heartbeat ping
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError):
                with state_lock:
                    current_client_state["connected"] = False
            return

        # 2. Get Live Editor State
        elif url.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with state_lock:
                data = json.dumps(current_client_state)
            self.wfile.write(data.encode('utf-8'))
            return

        # 3. Get Differences List
        elif url.path == '/api/diffs':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with state_lock:
                data = json.dumps({
                    "diffCount": current_client_state.get("diffCount", 0),
                    "diffs": current_client_state.get("diffs", [])
                })
            self.wfile.write(data.encode('utf-8'))
            return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)

        # Helper to read JSON body
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else '{}'
        try:
            body = json.loads(post_body)
        except Exception:
            body = {}

        # 1. Browser reporting its updated state
        if url.path == '/api/report-state':
            with state_lock:
                current_client_state.update(body)
                current_client_state["connected"] = True
                current_client_state["lastUpdated"] = time.time()

            # If this state report includes a correlation action result, notify waiting agents
            action_id = body.get("actionId")
            if action_id:
                with result_lock:
                    if action_id in pending_results:
                        pending_results[action_id]["response"] = body
                        pending_results[action_id]["event"].set()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        # 2. Agent Dispatching an Action to Browser
        elif url.path == '/api/action':
            action = body.get("action")
            params = body.get("params", {})
            action_id = f"act_{int(time.time()*1000)}_{os.urandom(2).hex()}"

            cmd_envelope = {
                "actionId": action_id,
                "action": action,
                "params": params,
                "timestamp": time.time()
            }

            # Prepare wait event if synchronous response is requested
            wait_for_result = body.get("sync", True)
            ev = threading.Event()
            if wait_for_result:
                with result_lock:
                    pending_results[action_id] = {"event": ev, "response": None}

            command_queue.put(cmd_envelope)

            resp_payload = {"status": "dispatched", "actionId": action_id}
            if wait_for_result:
                # Wait up to 5 seconds for the browser to execute and reply
                finished = ev.wait(timeout=5.0)
                with result_lock:
                    res_obj = pending_results.pop(action_id, None)
                if finished and res_obj and res_obj["response"]:
                    resp_payload = {
                        "status": "success",
                        "actionId": action_id,
                        "result": res_obj["response"]
                    }
                else:
                    resp_payload["warning"] = "Action queued, but browser did not confirm within 5s"

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload).encode('utf-8'))
            return

        # 3. Load SVG File from Disk
        elif url.path == '/api/load-file':
            file_path = body.get("filePath")
            if not file_path or not os.path.exists(file_path):
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error": "File not found"}')
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                raw_svg = f.read()

            file_name = os.path.basename(file_path)
            cmd_envelope = {
                "actionId": f"load_{int(time.time()*1000)}",
                "action": "loadSvg",
                "params": {
                    "svg": raw_svg,
                    "fileName": file_name
                }
            }
            command_queue.put(cmd_envelope)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "loaded", "fileName": file_name}).encode('utf-8'))
            return

        # 4. Save Exported Card/Image directly to Disk
        elif url.path == '/api/save-export':
            out_path = body.get("outputPath")
            data_url = body.get("dataUrl", "")
            if not out_path or not data_url:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Missing outputPath or dataUrl"}')
                return

            import base64
            header, encoded = data_url.split(',', 1)
            raw_bytes = base64.b64decode(encoded)
            with open(out_path, 'wb') as f:
                f.write(raw_bytes)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "saved", "path": out_path, "bytes": len(raw_bytes)}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AgentBridgeHandler) as httpd:
        print(f"Agent Bridge Server listening at http://localhost:{PORT}")
        print(f"SSE Command Stream at http://localhost:{PORT}/api/agent-events")
        print(f"REST API at http://localhost:{PORT}/api/action")
        httpd.serve_forever()

if __name__ == '__main__':
    run_server()
