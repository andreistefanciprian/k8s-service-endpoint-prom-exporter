from kubernetes import client, config
import logging
import time
from prometheus_client import start_http_server, Gauge
import os
import signal


class MetricsCollector:

    """
    Monitors a kubernetes service endpoints and reports available endpoints
    and not_ready pod ip addresses as prometheus metrics.
    """

    logging.basicConfig(
        format="%(levelname)s:%(asctime)s:%(message)s", level=logging.INFO
    )

    def __init__(self, polling_interval_seconds=5, service=None, namespace=None):
        self.polling_interval_seconds = polling_interval_seconds
        self.core_api = client.CoreV1Api()
        self._k8s_client_connected = False
        self.service = service
        self.namespace = namespace
        self.prom_endpoint_addresses_counter = Gauge(
            "srv_ready_pods",
            "Number of current pods that are serving traffic to service.",
        )
        self.prom_not_ready_addresses_counter = Gauge(
            "srv_not_ready_pods",
            "Number of current pods that are not serving traffic to service.",
        )

    def __time_track(func):
        """
        Decorator used for measuring time execution of methods.
        """

        def wrapper(*arg, **kw):
            t1 = time.time()
            result = func(*arg, **kw)
            total_time = time.time() - t1
            print(f"{func.__name__} ran in {total_time} seconds.")
            return result

        return wrapper

    # @__time_track
    def _initialise_client(self):
        """
        Initialise k8s sdk client if not already initialised.
        Returns bool.
        """

        if not self._k8s_client_connected:
            try:
                client.CoreV1Api
            except Exception as e:
                logging.info(e)
                raise
            else:
                logging.debug("Connection to K8s client was established.")
                self._k8s_client_connected = True
                return True
        else:
            return True

    def collect_metrics_loop(self):
        """Metrics collector loop"""

        while True:
            self.get_endpoints()
            time.sleep(self.polling_interval_seconds)

    # @__time_track
    def get_endpoints(self):
        """
        Returns a list of service endpoints for a namespaced service.
        Returns a list of not ready pod IPs for a namespaced service.
        """

        if self._initialise_client():
            try:
                # Fetch raw status data from the application
                result = self.core_api.read_namespaced_endpoints(
                    self.service, self.namespace
                )
            except Exception as e:
                logging.debug(e)
            else:
                endpoint_addresses = 0
                not_ready_addresses = 0
                dbg_eps_list = []  # tobedeleted
                dbg_eps_count = 0  # tobedeleted
                dbg_not_ready_list = []  # tobedeleted
                dbg_not_ready_count = 0  # tobedeleted
                # Update Prometheus metrics with application metrics
                if result.subsets is not None:
                    for i in result.subsets:
                        if i.addresses is not None:
                            for j in i.addresses:
                                dbg_eps_list.append(j.ip)  # tobedeleted
                                endpoint_addresses += 1
                        if i.not_ready_addresses is not None:
                            for j in i.not_ready_addresses:
                                not_ready_addresses += 1
                                dbg_not_ready_list.append(j.ip)  # tobedeleted
                dbg_not_ready_count = len(dbg_not_ready_list)  # tobedeleted
                dbg_eps_count = len(dbg_eps_list)  # tobedeleted
                self.prom_endpoint_addresses_counter.set(endpoint_addresses)
                self.prom_not_ready_addresses_counter.set(not_ready_addresses)
                logging.info(f"ready count: {dbg_eps_count}")  # tobedeleted
                logging.info(f"ready IPs: {dbg_eps_list}")  # tobedeleted
                logging.info(f"not ready count: {dbg_not_ready_count}")  # tobedeleted
                logging.info(f"not ready IPs: {dbg_not_ready_list}")  # tobedeleted
        else:
            logging.info("Connection to K8s client failed.")


def handler(signum, frame):
    print("Program was interrupted with CTRL+C")
    exit(0)


def main():
    # define vars
    service_name = "istiod-istio-1611"
    namespace_name = "istio-system"
    exporter_port = int(os.getenv("EXPORTER_PORT", "9153"))

    config.load_incluster_config()  # inside cluster authentication
    # config.load_kube_config()  # outside cluster authentication

    t = MetricsCollector(
        polling_interval_seconds=1,
        service=service_name,
        namespace=namespace_name
        )
    print("Starting server on port", exporter_port)
    start_http_server(exporter_port)
    t.collect_metrics_loop()


if __name__ == "__main__":
    # catch keyboard interrupt signal and exit gracefully
    signal.signal(signal.SIGINT, handler)

    # start exporter
    main()
