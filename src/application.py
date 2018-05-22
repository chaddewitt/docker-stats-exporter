import json
import time
import os
import six
import traceback
import sys
import logging
from docker import Client
from flask import Flask, make_response, jsonify
from flask_caching import Cache
from psuedo_file_metrics import PseudoFileStats
import re

METRICS = None
REFRESH_INTERVAL = os.environ.get('REFRESH_INTERVAL', 60)
CONTAINER_REFRESH_INTERVAL = os.environ.get('CONTAINER_REFRESH_INTERVAL', 120)
DOCKER_CLIENT = Client(
    base_url=os.environ.get('DOCKER_CLIENT_URL', 'unix://var/run/docker.sock'))
USE_PSEUDO_FILES = bool(os.environ.get('USE_PSEUDO_FILES', 1))
CGROUP_DIRECTORY = os.environ.get('CGROUP_DIRECTORY', '/sys/fs/cgroup')
PROC_DIRECTORY = os.environ.get('PROC_DIRECTORY', '/proc')


def initialize_app():
    flask_app = Flask(__name__)
    flask_app.config['PROPAGATE_EXCEPTIONS'] = True
    flask_cache = Cache(
        flask_app,
        config={
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': REFRESH_INTERVAL
        })
    return flask_app, flask_cache


app, cache = initialize_app()
app.logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)


def format_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2)
    error = traceback.format_exception(
        exc_type, exc_value, exc_traceback, limit=2)
    app.logger.error(error)
    return error


@app.errorhandler(Exception)
def handle_error(ex):
    global METRICS
    global DOCKER_CLIENT
    app.logger.error(str(ex))
    error = format_exception()
    response = jsonify(message=str(error))
    response.status_code = getattr(ex, 'code', 500)
    DOCKER_CLIENT = Client(
        base_url=os.environ.get('DOCKER_CLIENT_URL',
                                'unix://var/run/docker.sock'))
    METRICS = update_metrics()
    return response


@cache.cached()
@app.route('/metrics', methods=['GET'])
def get_metrics():
    global METRICS
    if not METRICS:
        METRICS = update_metrics()
    metrics = METRICS.next()
    response = make_response(metrics)
    response.headers["content-type"] = "text/plain"
    return response


def update_metrics():
    update_stats = update_pseudo_file_stats if USE_PSEUDO_FILES else update_container_stats
    parse_stats = parse_pseudo_file_metrics if USE_PSEUDO_FILES else parse_api_metrics
    stats, update_ts = update_stats()
    while True:
        if update_ts <= time.time():
            stats, update_ts = update_container_stats(stats_dict=stats)
        metrics = {}
        for container_name, container_stats in six.iteritems(stats):
            metrics[str(container_name)] = json.loads(container_stats.next())
        parsed_metrics = parse_stats(metrics)
        yield parsed_metrics


def parse_api_metrics(m):
    lines = [
        '# HELP See documentation for the docker stats API as each metric directly correlates to a stat value returned '
        'from the API'
    ]
    for container, stats in six.iteritems(m or {}):
        lines.append(make_line('last_seen', container, 1))
        cpu_stats = stats.get('cpu_stats', {})
        lines.append(
            make_line('system_cpu_usage', container,
                      cpu_stats['system_cpu_usage']))
        for stat_name in cpu_stats.get('cpu_usage'):
            lines.append(
                make_line('cpu_usage_%s' % stat_name, container,
                          cpu_stats['cpu_usage'][stat_name]))
        memory_stats = stats.get('memory_stats')
        for stat_name in memory_stats:
            if stat_name != 'stats':
                lines.append(
                    make_line('memory_stats_%s' % stat_name, container,
                              memory_stats[stat_name]))
        for stat_name in memory_stats.get('stats'):
            lines.append(
                make_line('memory_stats_%s' % stat_name, container,
                          memory_stats['stats'][stat_name]))
        io_stats = stats.get('blkio_stats',
                             {}).get('io_service_bytes_recursive')
        io_stats_dict = {i.get('op'): i.get('value') for i in io_stats}
        for stat_name, stat_value in six.iteritems(io_stats_dict):
            lines.append(
                make_line('blkio_stats_io_service_bytes_%s' % stat_name.lower(),
                          container, stat_value))
        network_stats = stats.get('networks')
        for stat_name, interface_stats in six.iteritems(network_stats or {}):
            for metric_name, metric_value in six.iteritems(
                            interface_stats or {}):
                lines.append(
                    make_line('networks_%s_%s' % (stat_name, metric_name),
                              container, metric_value))
    lines.sort()
    string_buffer = "\n".join(lines)
    string_buffer += "\n"
    return string_buffer


def make_line(metric_name, container, metric):
    metric_name = metric_name.replace('.', '_').replace('-', '_').lower()
    return str('docker_stats_%s{container="%s"} %s' % (metric_name, container,
                                                       int(metric)))


def update_container_stats(stats_dict=None):
    stats_dict = stats_dict or {}
    running_containers = DOCKER_CLIENT.containers()
    for container in running_containers:
        container_name = container['Names'][0].lstrip('/')
        if not stats_dict.get(container_name):
            stats_dict.update(
                {
                    container_name: DOCKER_CLIENT.stats(container=container['Id'], stream=True)
                }
            )
    container_names = [container['Names'][0].lstrip('/') for container in running_containers]
    for container_name, _ in six.iteritems(dict(stats_dict)):
        if container_name not in container_names:
            stats_dict.pop(container_name)
    return stats_dict, time.time() + CONTAINER_REFRESH_INTERVAL


def update_pseudo_file_stats(stats_dict=None):
    stats_dict = stats_dict or {}
    running_containers = DOCKER_CLIENT.containers()
    for c in running_containers:
        c_name = c['Names'][0].lstrip('/')
        c_inspect = DOCKER_CLIENT.inspect_container(str(c['Id']))
        stats_dict.update({
            c_name:
                PseudoFileStats(CGROUP_DIRECTORY, PROC_DIRECTORY, c_inspect)
        })
    container_names = [c['Names'][0].lstrip('/') for c in running_containers]
    for c_name, v in six.iteritems(dict(stats_dict)):
        if c_name not in container_names:
            stats_dict.pop(c_name)
    return stats_dict, time.time() + CONTAINER_REFRESH_INTERVAL


def parse_pseudo_file_metrics(m):
    lines = [
        "# Help See https://docs.docker.com/v1.8/articles/runmetrics/#metrics-from-cgroups-memory-cpu-block-i-o"
    ]
    for container, stats in six.iteritems(m or {}):
        lines.append(make_line('is_up', container, stats.pop('is_up')))
        lines.append(make_line('healthy', container, stats.pop('healthy')))
        for default_k, s in six.iteritems(stats):
            for k, v in six.iteritems(s or {}):
                if default_k == 'net':
                    for net_k, net_v in six.iteritems(v):
                        for nest_net_k, nest_net_v in six.iteritems(net_v):
                            key = '{}_{}_{}'.format(k, net_k, nest_net_k)
                            lines += parse_line_value(default_k, key,
                                                      nest_net_v, container)
                else:
                    lines += parse_line_value(default_k, k, v, container)
    lines.sort()
    string_buffer = "\n".join(lines)
    string_buffer += "\n"
    return string_buffer


def parse_line_value(default_k, k, v, container):
    k = '{}_{}'.format(default_k, k) if default_k not in k else k
    lines = []
    if isinstance(v, list):
        for i, item in enumerate(v):
            if re.match('^[A-Za-z_]+\s[0-9]+$', item):
                key, value = item.split(' ')
                lines.append(
                    make_line('{}_{}'.format(k, key), container, value))
            elif re.match('^[0-9]+:[0-9]+\s[A-Za-z_]+\s[0-9]+', item):
                _, key, value = item.split(' ')
                lines.append(
                    make_line('{}_{}'.format(k, key), container, value))
            elif re.match('^[0-9]+$', item):
                if len(v) > 1:
                    lines.append(
                        make_line('{}_{}'.format(k, i), container, item))
                else:
                    lines.append(make_line(k, container, item))
    else:
        lines.append(make_line(k, container, v))
    return lines


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
