## Description

Prometheus exporter built in Python that publishes kubernetes service availability metrics:
* srv_ready_pods (displays current numbers of service endpoints - pods that are ready to serve traffic)
* srv_not_ready_pods (displays current number of service pods that aren'r ready to serve traffic)

# Run script locally, from outside the cluster

Note: Use `config.load_kube_config()` method to authenticate to k8s cluster when running this script localy (from outside cluster)!

```
# create python3 virtual env
python3 -m venv venv

# activate python env
source venv/bin/activate

# install pip packages
pip install -r requirements.txt

# run script
python main.py
```

# Run script as k8s deployment

Note: Use `config.load_incluster_config()` method to authenticate to k8s cluster when running this script as deployment, from inside the cluster!

```
# build container image
docker build -f Dockerfile -t andreistefanciprian/endpoints-prom-exporter:latest .
docker image push andreistefanciprian/endpoints-prom-exporter

# build k8s resources
kubectl apply -f deployment.yaml

# check app logs
kubectl logs -l app=endpoints-prom-exporter -f

# testing
kubectl apply -f foo_deployment.yaml
kubectl set image pod foo-f88c97f79-5dvph blabla=nginx:fail
kubectl set image deployment foo blabla=nginx:1.12.0
kubectl scale deployment foo -n default --replicas 0
```