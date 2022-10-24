from kubernetes import client, config
import logging
import time
from datetime import datetime, timezone


class MetricsCollector:

    """
    Monitors a kubernetes service endpoints and reports available endpoints
    and not_ready pod ip addresses as prometheus metrics.
    """

    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s', level=logging.INFO)

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self._k8s_client_connected = False
        self.endpoint_addresses = []
        self.not_ready_addresses = []
        self.endpoint_addresses_counter = None
        self.not_ready_addresses_counter = None

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

    @__time_track 
    def get_endpoints(self, service_name, namespace):
        """"
        Returns a list of service endpoints for a namespaced service.
        Returns a list of not ready pod IPs for a namespaced service.
        """

        if self._initialise_client():
            try:
                result = self.core_api.read_namespaced_endpoints(service_name, namespace)
                # list_namespaced_endpoint_slice
                # read_namespaced_endpoints
                # list_namespaced_endpoints
                # list_namespaced_endpoint_slice
            except Exception as e:
                logging.debug(e)
                # raise
            else:
                # print(result.subsets[0].not_ready_addresses)
                # print(result.subsets[0].addresses[0].ip)
                if result.subsets is not None:
                    for i in result.subsets:
                        if i.addresses is not None:
                            for j in i.addresses:
                                self.endpoint_addresses.append(j.ip)
                        if i.not_ready_addresses is not None:
                            for j in i.not_ready_addresses:
                                self.not_ready_addresses.append(j.ip)
                self.not_ready_addresses_counter = len(self.not_ready_addresses)
                self.endpoint_addresses_counter = len(self.endpoint_addresses)
                logging.info(f'Endpoints for service {service_name}: {self.endpoint_addresses_counter}')
                logging.info(f'Not ready IPs for service {service_name}: {self.not_ready_addresses_counter}')
                return self.endpoint_addresses, self.not_ready_addresses, self.not_ready_addresses_counter, self.endpoint_addresses_counter
        else:
            logging.info('Connection to K8s client failed.')


def main():
    # define vars
    sleep_time = 1
    service_name = "istiod-istio-1611"
    namespace_name = "istio-system"

    # config.load_incluster_config()  # inside cluster authentication
    config.load_kube_config()   # outside cluster authentication

    while True:
        t = MetricsCollector()
        t.get_endpoints(service_name, namespace_name)
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
