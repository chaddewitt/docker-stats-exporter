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
                        metrics[f] = [l.replace('\n', '') for l in pseudo_file.readlines()]
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
                    labels = [l.replace(' ', '').replace('\n', '') for l in lines[0].split('|') if l.replace(' ', '')]
                    for i, label in enumerate(labels[1:], 1):
                        metrics[label] = {}
                        metric_names = lines[1].split('|')[i].split()
                        interfaces = [il.split()[:1][0].replace(':', '') for il in lines[2:]]
                        for interface_index, interface in enumerate(interfaces, 2):
                            if i < 2:
                                metric_values = lines[interface_index].split()[1:][:len(metric_names)]
                            else:
                                metric_values = lines[interface_index].split()[1:][len(metric_names):]
                            metrics[label].update({interface: dict(zip(metric_names, metric_values))})
        except (IOError, OSError):
            pass
    return metrics


class PseudoFileStats(object):
    def __init__(self, cgroup_dir, proc_dir, cid, pid):
        self.cgroup_dir = cgroup_dir
        self.proc_dir = proc_dir
        self.cid = cid
        self.pid = pid

    def get_psuedo_stat_dir(self, stat):
        if stat == 'net':
            d = join(self.proc_dir, '{pid}/net/dev'.format(pid=self.pid))
        else:
            d = join(self.cgroup_dir, '{stat}/docker/{cid}/'.format(stat=stat, cid=self.cid))
        return d

    def get_metrics(self):
        metrics = {}
        cpu = self.get_psuedo_stat_dir('cpu')
        cpuacct = self.get_psuedo_stat_dir('cpuacct')
        memory = self.get_psuedo_stat_dir('memory')
        blkio = self.get_psuedo_stat_dir('blkio')
        net = self.get_psuedo_stat_dir('net')
        metrics['cpu'] = parse_pseduo_dir(cpu)
        metrics['cpu'].update(parse_pseduo_dir(cpuacct))
        metrics['memory'] = parse_pseduo_dir(memory)
        metrics['blkio'] = parse_pseduo_dir(blkio)
        metrics['net'] = parse_net_dev(net)
        return metrics

    def next(self):
        return json.dumps(self.get_metrics())
