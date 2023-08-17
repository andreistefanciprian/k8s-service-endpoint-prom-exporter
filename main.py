# Import necessary libraries and modules
from kubernetes import client, config
import logging
import time
from prometheus_client import start_http_server, Gauge
import os
import signal
from datetime import datetime, timezone
import argparse
import json

# Define a class to collect and export metrics
class MetricsCollector:
    """
    Monitors a Kubernetes service and collects endpoint metrics:
    - pods ready to send traffic (endpoints)
    - pods not ready to send traffic
    These metrics can be exported to Prometheus.
    """

    def __init__(self, poll_interval, service, namespace):
        # Initialize metrics collector
        self.poll_interval = poll_interval
        self.core_api = None
        self.__k8s_client_connected = False
        self.service = service
        self.namespace = namespace
        self.labels = ["target_namespace", "target_endpoint"]

        # Define Prometheus metrics (Gauge counters)
        self.prom_endpoint_addresses_counter = Gauge(
            "srv_ready_pods",
            "Number of current pods that are serving traffic to service.",
            self.labels,
        )
        self.prom_not_ready_addresses_counter = Gauge(
            "srv_not_ready_pods",
            "Number of current pods that are not serving traffic to service.",
            self.labels,
        )
        self.__debug_level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")) # Set logging level from env var
        self.__setup_logging()  # Setup logging

    def __setup_logging(self):
        logging.basicConfig(
            format="%(levelname)s:%(asctime)s:%(message)s", level=self.__debug_level
        )

    def __time_track(func):
        """Decorator used for measuring method execution time."""
        def wrapper(*arg, **kw):
            t1 = time.time()
            result = func(*arg, **kw)
            total_time = time.time() - t1
            print(f"{func.__name__} ran in {total_time} seconds.")
            return result

        return wrapper

    def _initialise_k8s_client(self):
        """
        Initialize Kubernetes client if not already initialized
        Returns bool.
        """
        if not self.__k8s_client_connected:
            try: 
                self.core_api = client.CoreV1Api()  # Check if the CoreV1Api is available
            except Exception as e:
                logging.info(e)
                raise
            else:
                logging.debug("Connection to K8s client was established.")
                self.__k8s_client_connected = True
                return True
        else:
            return True

    def start_prom_exporter(self):
        """
        Metrics collector loop.
        Start Prometheus exporter and collect metrics.
        """
        while True:
            self._get_endpoints()
            time.sleep(self.poll_interval)

    # @__time_track
    def _get_endpoints(self):
        """
        Returns a list of service endpoints for a namespaced service.
        Returns a list of not ready pod IPs for a namespaced service.
        """

        if self._initialise_k8s_client():
            try:
                # Query k8s api for service endpoints data
                result = self.core_api.read_namespaced_endpoints(
                    self.service, self.namespace
                )
            except Exception as e:
                logging.debug(e)
            else:
                # Parse data from k8s api
                endpoint_addresses = 0
                not_ready_addresses = 0
                dbg_eps_list = []  # Used for debugging purposes
                dbg_eps_count = 0  # Used for debugging purposes
                dbg_not_ready_list = []  # Used for debugging purposes
                dbg_not_ready_count = 0  # Used for debugging purposes

                if result.subsets is not None:
                    for i in result.subsets:
                        if i.addresses is not None:
                            for j in i.addresses:
                                dbg_eps_list.append(j.ip)
                                endpoint_addresses += 1
                        if i.not_ready_addresses is not None:
                            for j in i.not_ready_addresses:
                                not_ready_addresses += 1
                                dbg_not_ready_list.append(j.ip)

                dbg_not_ready_count = len(dbg_not_ready_list)   # Used for debugging purposes
                dbg_eps_count = len(dbg_eps_list)   # Used for debugging purposes

                
                # Set prometheus metrics without labels
                # self.prom_endpoint_addresses_counter.set(endpoint_addresses)
                # self.prom_not_ready_addresses_counter.set(not_ready_addresses)

                # Set Prometheus metrics with labels
                self.prom_endpoint_addresses_counter.labels(self.namespace, self.service).set(endpoint_addresses)
                self.prom_not_ready_addresses_counter.labels(self.namespace, self.service).set(not_ready_addresses)

                # Create and export debugging data
                timestamp = datetime.now(timezone.utc).astimezone()
                exported_data = {
                    "timestamp": timestamp.isoformat(),
                    "ready_count": dbg_eps_count,
                    "ready_ips": dbg_eps_list,
                    "not_ready_count": dbg_not_ready_count,
                    "not_ready_ips": dbg_not_ready_list
                }   # Used for debugging purposes
                logging.info(f"Prometheus collected metrics: \n{json.dumps(exported_data, indent = 4)}")  # Used for debugging purposes

        else:
            logging.info("Connection to K8s client failed.")

# Define a signal handler to exit gracefully
def handler(signum, frame):
    print("Program was interrupted with CTRL+C")
    exit(0)

# Validate command-line arguments
def validate_args(args):
    # Placeholder for validation logic
    pass

# Main function
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service-name',
                        type=str,
                        help="K8s service name that you want to monitor.",
                        required=True)
    parser.add_argument('--namespace-name',
                        type=str,
                        help="K8s namespace where the service is running.",
                        required=True)
    parser.add_argument('--polling-interval',
                        type=int,
                        default=10,
                        help="Period of time in seconds between metric collection calls.",
                        required=False)
    args = parser.parse_args()
    validate_args(args)

    # Load environment variables
    exporter_port = int(os.getenv("EXPORTER_PORT", "9153"))
    kube_auth = os.getenv("KUBE_AUTH_INSIDE_CLUSTER", False)

    # Authenticate Kubernetes client
    if kube_auth:
        config.load_incluster_config()  # Inside cluster authentication
    else:
        config.load_kube_config()  # Outside cluster authentication

    # Create an instance of MetricsCollector and start the Prometheus exporter
    t = MetricsCollector(
        poll_interval=args.polling_interval,
        service=args.service_name,
        namespace=args.namespace_name,
    )
    print("Starting server on port", exporter_port)
    start_http_server(exporter_port)
    t.start_prom_exporter()

# Entry point
if __name__ == "__main__":
    # Catch keyboard interrupt signal and exit gracefully
    signal.signal(signal.SIGINT, handler)

    # Start the exporter
    main()
