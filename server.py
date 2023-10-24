import subprocess
import threading
import yaml
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
from typing import Dict, List
from queue import Queue
import time
import os


processes = []

def port_forward_thread(context: str, resource_name: str, namespace: str, local_port: int, remote_port: int) -> None:
    while True:
        cmd = ["kubectl", "--context", context, "port-forward", resource_name, "--namespace", namespace, f"{local_port}:{remote_port}"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(proc)
        time.sleep(5)
        print(f"Connected to service {resource_name} on port {local_port}")
        while True:
            # Run TCP check using `nc`
            nc_cmd = ["nc", "-z", "localhost", str(local_port)]
            nc_result = subprocess.run(nc_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # If TCP check fails, kill `kubectl port-forward` and break inner loop to restart it
            if nc_result.returncode != 0:
                print(f"TCP check failed, reconnecting to service {resource_name}")
                proc.terminate()
                processes.remove(proc)
                break

            time.sleep(1)

def update_hosts_file(services: List[Dict[str, str]]) -> None:
    managed_hosts_tag = "# Managed by k8s_port_forward.py"
    lines_to_keep = []
    
    with open("/etc/hosts", "r") as f:
        for line in f:
            if managed_hosts_tag not in line:
                lines_to_keep.append(line.strip())
                
    new_lines = [f"127.0.0.1 {service['name']}.local {managed_hosts_tag}" for service in services]

    with open("/etc/hosts", "w") as f:
        f.write("\n".join(lines_to_keep + new_lines) + "\n")




class ProxyHandler(BaseHTTPRequestHandler):
    config: Dict = {}
    connection_pool: Dict[str, Queue[HTTPConnection]] = {}

    @classmethod
    def get_connection(cls, host: str) -> HTTPConnection:
        if host not in cls.connection_pool:
            print("Creating new connection pool for", host)
            cls.connection_pool[host] = Queue()

        pool = cls.connection_pool[host]

        if pool.empty():
            return HTTPConnection(host)
        else:
            return pool.get()

    @classmethod
    def return_connection(cls, host: str, conn: HTTPConnection) -> None:
        cls.connection_pool[host].put(conn)

    def proxy_request(self) -> None:
        host = self.headers["Host"].split(":")[0]
        if host in self.config:
            conn = self.get_connection(f"localhost:{self.config[host]}")
            headers = {k: self.headers[k] for k in self.headers.keys()}
            conn.request(self.command, self.path, body=self.rfile.read(int(self.headers.get("Content-Length", 0))),
                         headers=headers)

            res = conn.getresponse()
            self.send_response(res.status)
            for key, value in res.getheaders():
                self.send_header(key, value)
            self.end_headers()

            self.wfile.write(res.read())
            self.return_connection(f"localhost:{self.config[host]}", conn)
        else:
            self.send_response(404)
            self.end_headers()

    # ... (Rest of your methods like do_GET, do_POST etc. remain the same)

    def do_GET(self) -> None:
        self.proxy_request()

    def do_POST(self) -> None:
        self.proxy_request()

    def do_PUT(self) -> None:
        self.proxy_request()

    def do_DELETE(self) -> None:
        self.proxy_request()

    def do_HEAD(self) -> None:
        self.proxy_request()

    def do_OPTIONS(self) -> None:
        self.proxy_request()

if __name__ == "__main__":

    config_path = os.path.expanduser("~/.kubeserver")
    config_file = os.path.join(config_path, "config.yaml")

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("No config.yaml found in ~/.kubeserver, create one and try again")

    if "services" not in config or config["services"] is None:
        print("No services found in config.yaml, add some in ~/.kubeserver/config.yaml and try again")
    update_hosts_file(config["services"])

    host_to_port = {}
    for service in config["services"]:
        threading.Thread(target=port_forward_thread, args=(service["context"], service["resource_name"], service["namespace"], service["local_port"], service["remote_port"]), daemon=True).start()
        host_to_port[service["name"] + ".local"] = service["local_port"]

    ProxyHandler.config = host_to_port
    try:
        httpd = ThreadingHTTPServer(("localhost", 80), ProxyHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        for proc in processes:
            proc.terminate()
