from kubernetes import client, config
import logging
import time
from prometheus_client import start_http_server, Gauge
import os
import signal
import libhoney
from datetime import datetime, timezone
import argparse


class MetricsCollector:

    """
    Monitors a kubernetes service and collects endpoint metrics:
        - pods ready to send traffic (endpoints)
        - pods not ready to send traffic
    These metrics are collected as counters/IP addresses and can be 
        - exported to Prometheus (prometheus format)
        - sent to Honeycomb as events (json format)
    """

    logging.basicConfig(
        format="%(levelname)s:%(asctime)s:%(message)s", level=logging.INFO
    )

    def __init__(self, poll_interval, service, namespace, otel_enabled, otel_api_key=None, otel_serv_name=None):
        self.poll_interval = poll_interval
        self.core_api = client.CoreV1Api()
        self._k8s_client_connected = False
        self.service = service
        self.namespace = namespace
        self.labels = ["namespace", "service"]
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
        self.otel_api_key = os.getenv("OTEL_API_KEY") if otel_api_key is None else otel_api_key
        self.otel_serv_name = service if otel_serv_name is None else otel_serv_name
        self._honeycomb_client_connected = False
        self.otel_enabled = otel_enabled

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

    def _initialise_otel_client(self):
        """
        Initialise honeycomb sdk client if not already initialised.
        Returns bool.
        """

        if not self._honeycomb_client_connected:
            try:
                libhoney.init(
                    writekey=self.otel_api_key,
                    dataset=self.otel_serv_name,
                    debug=False
                )
            except Exception as e:
                logging.info(e)
                raise
            else:
                logging.debug("Connection to Honeycomb was established.")
                self._honeycomb_client_connected = True
                return True
        else:
            return True

    def _send_otel_event(self, data):
        """Send otel event."""

        if self._initialise_otel_client():
            # create a new event
            ev = libhoney.new_event()
            # add data up front
            ev.add(data)
            # ev.add_field("duration_ms", 153.12)
            logging.info(f"Sending event to otel {data}")
            ev.send()

    # @__time_track
    def _initialise_k8s_client(self):
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
                # query k8s api for service endpoints data
                result = self.core_api.read_namespaced_endpoints(
                    self.service, self.namespace
                )
            except Exception as e:
                logging.debug(e)
            else:
                # parse data from k8s api
                endpoint_addresses = 0
                not_ready_addresses = 0
                dbg_eps_list = []  # tobedeleted
                dbg_eps_count = 0  # tobedeleted
                dbg_not_ready_list = []  # tobedeleted
                dbg_not_ready_count = 0  # tobedeleted
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
                
                # set prometheus metrics without labels
                # self.prom_endpoint_addresses_counter.set(endpoint_addresses)
                # self.prom_not_ready_addresses_counter.set(not_ready_addresses)

                # set prometheus metrics with labels
                self.prom_endpoint_addresses_counter.labels(self.namespace, self.service).set(endpoint_addresses)
                self.prom_not_ready_addresses_counter.labels(self.namespace, self.service).set(not_ready_addresses)
                
                # send otel event
                timestamp = datetime.now(timezone.utc).astimezone()
                otel_data = {
                    "timestamp": timestamp.isoformat(),
                    "ready_count": dbg_eps_count,
                    "ready_ips": dbg_eps_list,
                    "not_ready_count": dbg_not_ready_count,
                    "not_ready_ips": dbg_not_ready_list
                }
                if self.otel_enabled:
                    self._send_otel_event(otel_data)
                logging.info(f"Prometheus collected metrics: {otel_data}")  # tobedeleted

        else:
            logging.info("Connection to K8s client failed.")


def handler(signum, frame):
    print("Program was interrupted with CTRL+C")
    exit(0)


def validate_args(args):
    """Validate namespace/service exists."""
    # print(args)
    pass


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
                        help="Period of time in seconds in between metric collection calls.",
                        required=False)
    parser.add_argument('--otel-enabled',
                        type=bool,
                        default=False,
                        help="Send metrics to Honeycomb.",
                        required=False)
    args = parser.parse_args()
    validate_args(args)

    # define vars
    exporter_port = int(os.getenv("EXPORTER_PORT", "9153"))
    kube_auth = os.getenv("KUBE_AUTH_INSIDE_CLUSTER", False)
    # otel_enabled = os.getenv("OTEL_ENABLED")

    # authenticate k8s client
    if kube_auth:
        config.load_incluster_config()  # inside cluster authentication
    else:
        config.load_kube_config()  # outside cluster authentication

    t = MetricsCollector(
        poll_interval=args.polling_interval,
        service=args.service_name,
        namespace=args.namespace_name,
        otel_enabled=args.otel_enabled
        )
    print("Starting server on port", exporter_port)
    start_http_server(exporter_port)
    t.collect_metrics_loop()


if __name__ == "__main__":
    # catch keyboard interrupt signal and exit gracefully
    signal.signal(signal.SIGINT, handler)

    # start exporter
    main()
