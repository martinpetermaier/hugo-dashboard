#!/usr/bin/env python3
"""Live Dashboard Server - serves index.html and generates data.json on every request."""
import http.server
import json
import os
import subprocess
import sys
from pathlib import Path

PORT = 7777
DASHBOARD_DIR = Path(__file__).parent
GENERATE_SCRIPT = DASHBOARD_DIR / "generate_data.sh"

class LiveHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        # Regenerate data.json on every request to it
        if self.path == "/data.json" or self.path.startswith("/data.json?"):
            try:
                subprocess.run(
                    ["bash", str(GENERATE_SCRIPT)],
                    cwd=str(DASHBOARD_DIR),
                    capture_output=True, timeout=30
                )
            except Exception as e:
                print(f"⚠️ generate failed: {e}", file=sys.stderr)
            
            # Add CORS and no-cache headers
            data_path = DASHBOARD_DIR / "data.json"
            if data_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data_path.read_bytes())
                return
        
        # Everything else served normally
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

if __name__ == "__main__":
    print(f"🚀 Live Dashboard: http://localhost:{PORT}")
    print(f"   data.json regenerated on every request")
    server = http.server.HTTPServer(("0.0.0.0", PORT), LiveHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
