from os import listdir
import json
from os.path import join, isfile, isdir


def parse_pseduo_dir(d):
    metrics = {}
    if isdir(d):
        for f in listdir(d):
            if isfile(join(d, f)):
                try:
                    with open(join(d, f), 'r') as pseudo_file:
                        metrics[f] = [
                            l.replace('\n', '')
                            for l in pseudo_file.readlines()
                        ]
                except (IOError, OSError):
                    pass
    return metrics


def parse_net_dev(path):
    metrics = {}
    if isfile(path):
        try:
            with open(path, 'r') as pseudo_file:
                lines = pseudo_file.readlines()
                if len(lines) >= 3:
                    labels = [
                        l.replace(' ', '').replace('\n', '')
                        for l in lines[0].split('|')
                        if l.replace(' ', '')
                    ]
                    for i, label in enumerate(labels[1:], 1):
                        metrics[label] = {}
                        metric_names = lines[1].split('|')[i].split()
                        interfaces = [
                            il.split()[:1][0].replace(':', '')
                            for il in lines[2:]
                        ]
                        for interface_index, interface in enumerate(
                                interfaces, 2):
                            if i < 2:
                                metric_values = lines[interface_index].split()[
                                    1:][:len(metric_names)]
                            else:
                                metric_values = lines[interface_index].split()[
                                    1:][len(metric_names):]
                            metrics[label].update({
                                interface:
                                dict(zip(metric_names, metric_values))
                            })
        except (IOError, OSError):
            pass
    return metrics


class PseudoFileStats(object):

    def __init__(self, cgroup_dir, proc_dir, container_inspection):
        self.cgroup_dir = cgroup_dir
        self.proc_dir = proc_dir
        self.cid = str(container_inspection['Id'])
        self.pid = container_inspection.get('State', {}).get('Pid')
        self.state = container_inspection.get('State', {})
        if self.state.get("Running") and not self.state.get("Restarting"):
            self.is_up = 1
        else:
            self.is_up = 0

        if self.state.get("Health"):
            self.healthy = int(self.state["Health"].get("Status") == 'healthy')
        else:
            self.healthy = self.is_up

    def get_psuedo_stat_dir(self, stat):
        if stat == 'net':
            d = join(self.proc_dir, '{pid}/net/dev'.format(pid=self.pid))
        else:
            d = join(self.cgroup_dir, '{stat}/docker/{cid}/'.format(
                stat=stat, cid=self.cid))
        return d

    def get_metrics(self):
        metrics = {}
        cpu = self.get_psuedo_stat_dir('cpu')
        memory = self.get_psuedo_stat_dir('memory')
        blkio = self.get_psuedo_stat_dir('blkio')
        net = self.get_psuedo_stat_dir('net')
        metrics['cpu'] = parse_pseduo_dir(cpu)
        metrics['memory'] = parse_pseduo_dir(memory)
        metrics['blkio'] = parse_pseduo_dir(blkio)
        metrics['net'] = parse_net_dev(net)
        metrics['is_up'] = self.is_up
        metrics['healthy'] = self.healthy
        return metrics

    def next(self):
        return json.dumps(self.get_metrics())
