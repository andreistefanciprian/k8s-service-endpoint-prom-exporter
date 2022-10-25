from kubernetes import client, config
import logging
import time
from prometheus_client import start_http_server, Gauge
import os


class MetricsCollector:

    """
    Monitors a kubernetes service endpoints and reports available endpoints
    and not_ready pod ip addresses as prometheus metrics.
    """

    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s', level=logging.INFO)

    def __init__(self, polling_interval_seconds=2, service=None, namespace=None):
        self.polling_interval_seconds = polling_interval_seconds
        self.core_api = client.CoreV1Api()
        self._k8s_client_connected = False
        self.service = service
        self.namespace = namespace
        self.prom_endpoint_addresses_counter = Gauge('srv_ready_pods', 'Number of current pods that are serving traffic to service.')
        self.prom_not_ready_addresses_counter = Gauge('srv_not_ready_pods', 'Number of current pods that are not serving traffic to service.')

    def __time_track(func):
        """
        Decorator used for measuring time execution of methods.
        """

        def wrapper(*arg, **kw):
            t1 = time.time()
            result = func(*arg, **kw)
            total_time = time.time() - t1
            print(f'{func.__name__} ran in {total_time} seconds.')
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
                logging.debug('Connection to K8s client was established.')
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
        """"
        Returns a list of service endpoints for a namespaced service.
        Returns a list of not ready pod IPs for a namespaced service.
        """

        if self._initialise_client():
            try:
                # Fetch raw status data from the application
                result = self.core_api.read_namespaced_endpoints(self.service, self.namespace)
            except Exception as e:
                logging.debug(e)
            else:
                endpoint_addresses = 0
                not_ready_addresses = 0
                endpoint_addresses_list = []  # used for debug purposes. To be deleted
                endpoint_addresses_list_counter = 0  # used for debug purposes. To be deleted
                not_ready_addresses_list = []  # used for debug purposes. To be deleted
                not_ready_addresses_list_counter = 0  # used for debug purposes. To be deleted
                # Update Prometheus metrics with application metrics
                if result.subsets is not None:
                    for i in result.subsets:
                        if i.addresses is not None:
                            for j in i.addresses:
                                endpoint_addresses_list.append(j.ip)  # used for debug purposes. To be deleted
                                endpoint_addresses += 1
                        if i.not_ready_addresses is not None:
                            for j in i.not_ready_addresses:
                                not_ready_addresses += 1
                                not_ready_addresses_list.append(j.ip)  # used for debug purposes. To be deleted
                not_ready_addresses_list_counter = len(not_ready_addresses_list)  # used for debug purposes. To be deleted
                endpoint_addresses_list_counter = len(endpoint_addresses_list)  # used for debug purposes. To be deleted
                self.prom_endpoint_addresses_counter.set(endpoint_addresses)
                self.prom_not_ready_addresses_counter.set(not_ready_addresses)
                logging.info(f'ready counter: {endpoint_addresses_list_counter}')  # used for debug purposes. To be deleted
                logging.info(f'ready IPs: {endpoint_addresses_list}')  # used for debug purposes. To be deleted
                logging.info(f'not ready counter: {not_ready_addresses_list_counter}')  # used for debug purposes. To be deleted
                logging.info(f'not ready IPs: {not_ready_addresses_list}')  # used for debug purposes. To be deleted
        else:
            logging.info('Connection to K8s client failed.')


def main():
    # define vars
    service_name = "istiod-istio-1611"
    namespace_name = "istio-system"
    exporter_port = int(os.getenv("EXPORTER_PORT", "9099"))

    # config.load_incluster_config()  # inside cluster authentication
    config.load_kube_config()   # outside cluster authentication

    t = MetricsCollector(service=service_name, namespace=namespace_name)
    start_http_server(exporter_port)
    t.collect_metrics_loop()


if __name__ == '__main__':
    main()
