KubeServer
A utility to facilitate local development with Kubernetes by automating the port-forwarding of services and providing a reverse proxy for a more native development experience.

Features
Automatic kubectl port-forward for listed services.
Reverse proxy to maintain original URL structure during local development.
Configuration-driven approach for ease of setup and usage.
Connection pooling to enhance proxy performance.
Automatic hosts file update for service URLs.
Prerequisites
Python 3.x
Poetry (for dependency management)
Kubernetes with kubectl properly set up.
nc (netcat) for TCP checks.
Quick Start
Clone the repository:

bash
Copy code
git clone [repository-url] kubeserver
cd kubeserver
Install dependencies using Poetry:

bash
Copy code
poetry install
Place your configuration in ~/.kubeserver/config.yaml or use the provided example_config.yaml as a template.

Start the server:

bash
Copy code
./start_server.sh
Configuration
The configuration file, located at ~/.kubeserver/config.yaml, defines the Kubernetes services you want to work with. Each service entry should have:

name: A unique name for the service.
context: The Kubernetes context to use.
resource_name: Name of the resource in Kubernetes.
namespace: Namespace of the resource.
local_port: Local port to which the service will be forwarded.
remote_port: The port on the remote service.
Example:

yaml
Copy code
services:
  - name: airflow-prod
    context: my-k8s-context
    resource_name: svc/airflow-webserver
    namespace: prod
    local_port: 8080
    remote_port: 8080
Notes
The server is threaded to handle multiple requests in parallel.
Any edits to the /etc/hosts file by this script are idempotent.
Contribute
Feel free to submit PRs or issues if you find any problems or have suggestions for improvements.

