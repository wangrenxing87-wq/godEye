"""Local MC Studio SSE bridge client, for reproducible integration checks.

Only connects to loopback. Usage: py -3 tools/studio_rpc.py tools/list
Tool calls read exact JSON arguments from --arguments-file.
"""
import argparse
import json
import urllib.request
from pathlib import Path


class StudioRPC:
    def __init__(self, port=19131):
        self.base = "http://127.0.0.1:%d" % port
        self.stream = urllib.request.urlopen(self.base + "/sse", timeout=45)
        self.counter = 0
        event, data = self.read_event()
        if event != "endpoint" or not data.startswith("/messages?"):
            raise RuntimeError("Unexpected Studio SSE endpoint")
        self.endpoint = self.base + data
        self.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "godeye-local-validation", "version": "1.0"}})
        self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def read_event(self):
        event, lines = "message", []
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("Studio SSE stream closed")
            line = line.decode("utf-8").rstrip("\r\n")
            if not line and lines:
                return event, "\n".join(lines)
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                lines.append(line[5:].strip())

    def post(self, body):
        request = urllib.request.Request(self.endpoint, data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=45) as response:
            response.read()

    def call(self, method, params=None):
        self.counter += 1
        request_id = self.counter
        self.post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        while True:
            _, data = self.read_event()
            response = json.loads(data)
            if response.get("id") == request_id:
                if "error" in response:
                    raise RuntimeError(response["error"])
                return response.get("result")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", help="tools/list, or a Studio tool name")
    parser.add_argument("--arguments-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rpc = StudioRPC()
    try:
        if args.method == "tools/list":
            result = rpc.call("tools/list")
        else:
            arguments = json.loads(args.arguments_file.read_text(encoding="utf-8")) if args.arguments_file else {}
            result = rpc.call("tools/call", {"name": args.method, "arguments": arguments})
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        print(text)
    finally:
        rpc.stream.close()


if __name__ == "__main__":
    main()
