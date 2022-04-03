"""Simple tool to monitor system in a thread"""
VERSION = (0, 1)
__version__ = '.'.join([str(i) for i in VERSION])
__author__ = "Anthony Monthe (ZuluPro)"
__email__ = 'contact@cloud-mercato.com'

import time
import threading
import logging
import psutil

logger = logging.getLogger()

class Collector:
    def setup(self):
        pass

    def __call__(self):
        raise NotImplementedError()


class CpuTime(Collector):
    name = "cpus"

    def __call__(self):
        return [dict(i._asdict()) for i in psutil.cpu_times_percent(percpu=True)]


class LoadAvg(Collector):
    name = "loadavg"

    def __call__(self):
        return dict(zip(
            ('1', '5', '15'),
            psutil.getloadavg()
        ))


class Mem(Collector):
    name = "mem"

    def __call__(self):
        return dict(psutil.virtual_memory()._asdict())


class NetIo(Collector):
    name = "net_io"

    def collect(self):
        return {
            net: {
                name: count
                for name, count in counts._asdict().items()
            }
            for net, counts in psutil.net_io_counters(True).items()
        }

    def setup(self):
        self.last = self.collect()
        self._empty = {k: {} for k in self.last}

    def __call__(self):
        data = {k: {} for k in self.last}
        collected = self.collect()
        for net, counts in collected.items():
            for name, count in counts.items():
                data[net][name] = count - self.last[net][name]
        self.last = collected
        return data


COLLECTORS = {
    'cpus': CpuTime,
    'loadavg': LoadAvg,
    'mem': Mem,
    'net_io': NetIo,
}


class Monitoring:
    """
    Manage multiple collector with the ablity to run in background.

    >>> m = Monitoring()
    >>> m.start()
    >>> # Monitorin in progress
    >>> m.stop()
    """
    def __init__(self, types=None, delay=5):
        self.types = types or list(COLLECTORS)
        self.data = {}
        for type_ in self.types:
            self.data[type_] = {}
        self.delay = delay
        self.thread = threading.Thread(
            target=self.monitor,
        )
        self.collectors = []
        self._running = False

    def setup(self):
        for type_ in self.types:
            collector = COLLECTORS[type_]()
            collector.setup()
            self.collectors.append(collector)

    def collect(self):
        now = int(time.time())
        for collector in self.collectors:
            data = collector()
            logger.debug("Collect %s: %s", collector, data)
            self.data[collector.name][now] = data

    def monitor(self):
        while self._running:
            self.collect()
            time.sleep(self.delay)
        logger.info("Ended monitoring")

    def start(self):
        self._running = True
        self.thread.start()

    def stop(self):
        self._running = False
