import socket
import json
import threading
import sys
import os


class SDKServer:
    DEFAULT_PORT = 59123
    
    def __init__(self, sdk_path: str = None, port: int = None):
        self.port = port or self.DEFAULT_PORT
        self.sdk_path = sdk_path
        self.sdk = None
        self.running = False
        self.server_socket = None
        
        if self.sdk_path:
            os.chdir(self.sdk_path)
        
        sdk_module_dir = os.path.dirname(os.path.abspath(__file__))
        if sdk_module_dir not in sys.path:
            sys.path.insert(0, sdk_module_dir)
    
    def _init_sdk(self):
        if self.sdk is None:
            try:
                from .ezcad_sdk import EzcadSDK
            except ImportError:
                from ezcad_sdk import EzcadSDK
            self.sdk = EzcadSDK()
    
    def _handle_request(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "ping":
            return {"success": True, "result": "pong"}
        
        if method == "shutdown":
            self.running = False
            return {"success": True, "result": "shutting_down"}
        
        self._init_sdk()
        
        if not hasattr(self.sdk, method):
            return {"success": False, "error": f"Unknown method: {method}"}
        
        func = getattr(self.sdk, method)
        result = func(**params)
        
        if hasattr(result, 'value'):
            result = result.value
        
        return {"success": True, "result": result}
    
    def _handle_client(self, client_socket: socket.socket):
        client_socket.settimeout(30)
        buffer = b""
        
        while self.running:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    request = json.loads(line.decode("utf-8"))
                    response = self._handle_request(request)
                    client_socket.sendall(json.dumps(response).encode("utf-8") + b"\n")
                    
                    if request.get("method") == "shutdown":
                        client_socket.close()
                        return
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                break
        
        client_socket.close()
    
    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1)
        
        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
        
        self.server_socket.close()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SDKServer.DEFAULT_PORT
    sdk_path = sys.argv[2] if len(sys.argv) > 2 else None
    server = SDKServer(sdk_path=sdk_path, port=port)
    server.start()
