## Endpoint Metrics Collector for Kubernetes Services

This tool monitors a Kubernetes service and collects valuable endpoint metrics, enabling you to gain insights into the health and readiness of your service's pods. The collected metrics are particularly useful for understanding the availability and responsiveness of your service's underlying infrastructure.

![Prometheus Metrics Screenshot](prometheus_metrics_screenshot.png)

### Collected Metrics

The tool captures the following metrics for a Kubernetes service:

- **srv_ready_pods**: Displays the current number of service endpoints (pods) that are successfully passing Kubernetes startup, readiness, and liveness probes.

- **srv_not_ready_pods**: Shows the current number of service pods that are not ready to serve traffic. This metric encompasses various scenarios:
    - Pods that are failing Kubernetes startup, readiness, or liveness probes.
    - Pods that encounter issues while pulling container images, among other startup challenges.
    - Please note that this metric doesn't account for pods that are unscheduled due to different constraints.

### Export Options

The collected metrics can be easily exported to Prometheus in the Prometheus format, allowing for seamless integration with Prometheus monitoring systems and dashboards.

### Local Script Execution

To run the script locally, from outside the cluster, follow these steps:

1. Create a Python 3 virtual environment:
   ```bash
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Install required pip packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the script with OpenTelemetry (OTEL) enabled or disabled:
   ```bash
   python main.py --service-name foo --namespace-name default --polling-interval 2
   ```

### Or Kubernetes Deployment

To run the script as a Kubernetes deployment, follow these steps:

1. Build and push the container image:
   ```bash
   docker build -f Dockerfile -t andreistefanciprian/endpoints-prom-exporter:latest .
   docker image push andreistefanciprian/endpoints-prom-exporter
   ```

2. Apply Kubernetes resources for deployment, RBAC, and ServiceMonitor:
   ```bash
   kubectl apply -f k8s/foo_deployment.yaml
   kubectl apply -f k8s/rbac.yaml
   kubectl apply -f k8s/servicemonitor.yaml
   kubectl apply -f k8s/deployment.yaml
   ```

### Testing

For testing purposes, use the following commands:

- Check application logs while testing:
  ```bash
  kubectl logs -l app=endpoints-prom-exporter -f
  ```

- Access the metrics page at http://localhost:9153/

- Execute various test scenarios to observe how the metrics change and adapt:
  ```bash
  # Simulate failures
  kubectl set image pod foo-f88c97f79-5dvph foo=nginx:fail
  kubectl set image deployment foo foo=nginx:1.12.0
  kubectl scale deployment foo -n default --replicas 0
  kubectl scale deployment foo -n default --replicas 10
  kubectl set image deployment foo foo=nginx:fail

  # Fail liveness probe on one of the pods
  kubectl exec -ti foo-f88c97f79-5dvph rm /usr/share/nginx/html/index.html

  # Fail liveness probe on all pods
  for pod in $(kubectl get pods --no-headers | grep foo | grep Running | awk '{print $1}'); do kubectl exec -ti $pod rm /usr/share/nginx/html/index.html; done

  # Fail startup/readiness probe by redeploying with incorrect port number for these probes
  ```

- Note: The **srv_not_ready_pods** counter doesn't capture pods that can't be scheduled for any reason. To simulate this, follow these steps:
  ```bash
  # Cordon all nodes
  for node in $(kubectl get nodes --no-headers | awk '{print $1}'); do kubectl cordon $node; done
  
  # Scale the deployment
  kubectl scale deployment foo -n default --replicas 5
  
  # Uncordon all nodes
  for node in $(kubectl get nodes --no-headers | awk '{print $1}'); do kubectl uncordon $node; done
  ```