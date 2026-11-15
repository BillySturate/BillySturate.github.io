#!/usr/bin/env python3
"""Build and serve the root artifact for local development."""
import argparse
import http.server
import functools
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()
subprocess.run([sys.executable, str(ROOT / 'scripts/build.py'), '--site-url', f'http://localhost:{args.port}'], check=True)
print(f'Preview: http://localhost:{args.port}/ (Ctrl-C to stop)', flush=True)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'dist'))
try:
    http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler).serve_forever()
except KeyboardInterrupt:
    pass
