import socket
import json
import subprocess
import time
import sys
from pathlib import Path

from .ezcad_sdk import EzcadSDK


class SDKClient:
    DEFAULT_PORT = 59123
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, sdk_path: Path = None, port: int = None, python_32bit: str = "py -3.12-32"):
        if self._initialized:
            return
        self.port = port or self.DEFAULT_PORT
        self.sdk_path = sdk_path or EzcadSDK._SDK_PATH
        self.python_32bit = python_32bit
        self.server_process = None
        self.socket = None
        self._initialized = True
    
    @classmethod
    def reset(cls):
        if cls._instance:
            cls._instance.close()
            cls._instance = None
    
    def start_server(self):
        if self.server_process is not None:
            return
        
        server_script = Path(__file__).parent / "sdk_server.py"
        project_root = Path(__file__).parent.parent.parent
        cmd = f'cd "{self.sdk_path}" && cd "{project_root}" && {self.python_32bit} "{server_script}" {self.port}'
        
        self.server_process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        for _ in range(50):
            time.sleep(0.1)
            if self._try_connect():
                return
        
        raise RuntimeError("Failed to start SDK server")
    
    def _try_connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect(("127.0.0.1", self.port))
            return True
        except (ConnectionRefusedError, socket.timeout):
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def _ensure_connection(self):
        if self.socket is None:
            if not self._try_connect():
                self.start_server()
    
    def _send_request(self, method: str, **params) -> any:
        self._ensure_connection()
        
        request = {"method": method, "params": params}
        self.socket.sendall(json.dumps(request).encode("utf-8") + b"\n")
        
        buffer = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("Server closed connection")
            buffer += chunk
            if b"\n" in buffer:
                break
        
        response = json.loads(buffer.split(b"\n")[0].decode("utf-8"))
        
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Unknown error"))
        
        return response.get("result")
    
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda **kwargs: self._send_request(name, **kwargs)
    
    def ping(self) -> str:
        return self._send_request("ping")
    
    def close(self):
        if self.socket:
            try:
                self._send_request("shutdown")
            except:
                pass
            self.socket.close()
            self.socket = None
        
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.server_process = None
