## Description

Monitors a kubernetes service and collects endpoint metrics:
* srv_ready_pods (displays current numbers of service endpoints - pods that are ready to serve traffic)
* srv_not_ready_pods (displays current number of service pods that aren'r ready to serve traffic)  
These metrics can be:
* exported to Prometheus (prometheus format)
* sent to Honeycomb as events (json format)  

#### Run script locally, from outside the cluster

```
# create python3 virtual env
python3 -m venv venv

# activate python env
source venv/bin/activate

# install pip packages
pip install -r requirements.txt

# run script
python main.py

# running script with OTEL enabled
export OTEL_API_KEY=<HONEYCOMB_API_KEY>
export OTEL_ENABLED=True
python main.py
```

#### Run script as k8s deployment

```
# If you send honeycomb events you need to define otel api key as secret and
# set OTEL_ENABLED env var in deployment manifest k8s/deployment.yaml
kubectl create secret generic honeycomb --from-literal=otel_api_key=<OTEL API KEY HERE>

# build container image
docker build -f Dockerfile -t andreistefanciprian/endpoints-prom-exporter:latest .
docker image push andreistefanciprian/endpoints-prom-exporter

# build k8s resources
kubectl apply -f k8s/foo_deployment.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/servicemonitor.yaml
kubectl apply -f k8s/deployment.yaml

# check app logs
kubectl logs -l app=endpoints-prom-exporter -f

# testing
kubectl set image pod foo-f88c97f79-5dvph foo=nginx:fail
kubectl set image deployment foo foo=nginx:1.12.0
kubectl scale deployment foo -n default --replicas 0
```