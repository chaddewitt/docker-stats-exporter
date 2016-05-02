import json
import time

import six
import argparse
from docker import Client
from flask import Flask, make_response, jsonify
from flask.ext.cache import Cache

METRICS = None
CONTAINER_REFRESH_INTERVAL = None
DOCKER_CLIENT = None


def initialize_app():
    global CONTAINER_REFRESH_INTERVAL, DOCKER_CLIENT
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker_client_url', '-url', dest='docker_client_url', default='unix://var/run/docker.sock')
    parser.add_argument('--refresh_interval', '-r', dest='refresh_interval', default=60)
    parser.add_argument('--container_refresh_interval', dest='container_refresh_interval', default=120)
    args, remaining_args = parser.parse_known_args()
    flask_app = Flask(__name__)
    flask_app.config['PROPAGATE_EXCEPTIONS'] = True
    flask_cache = Cache(flask_app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': args.refresh_interval})
    CONTAINER_REFRESH_INTERVAL = args.container_refresh_interval
    DOCKER_CLIENT = Client(base_url=args.docker_client_url)
    return flask_app, flask_cache

app, cache = initialize_app()


@app.errorhandler(Exception)
def handle_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = getattr(ex, 'code', 500)
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
    stats, update_ts = update_container_stats()
    while True:
        if update_ts <= time.time():
            stats, update_ts = update_container_stats(stats_dict=stats)
        metrics = {}
        for c_name, s in six.iteritems(stats):
            metrics[str(c_name)] = json.loads(s.next())
        yield parse_metrics(metrics)


def parse_metrics(m):
    lines = [
        '# HELP See documentation for the docker stats API as each metric directly coorelates to a stat value returned '
        'from the API'
    ]
    for container, stats in six.iteritems(m or {}):
        lines.append(make_line('last_seen', container, 1))
        cpu_stats = stats.get('cpu_stats', {})
        lines.append(make_line('system_cpu_usage', container, cpu_stats['system_cpu_usage']))
        for stat_name in cpu_stats.get('cpu_usage'):
            lines.append(make_line('cpu_usage_%s' % stat_name, container, cpu_stats['cpu_usage'][stat_name]))
        memory_stats = stats.get('memory_stats')
        for stat_name in memory_stats:
            if stat_name != 'stats':
                lines.append(make_line('memory_stats_%s' % stat_name, container, memory_stats[stat_name]))
        for stat_name in memory_stats.get('stats'):
            lines.append(make_line('memory_stats_%s' % stat_name, container, memory_stats['stats'][stat_name]))
        io_stats = stats.get('blkio_stats', {}).get('io_service_bytes_recursive')
        io_read_stats = [i.get('value') for i in io_stats if i.get('op') is 'Read']
        lines.append(make_line('blkio_stats_io_service_bytes_read', container, io_read_stats[0] if io_read_stats else 0))
        io_write_stats = [i.get('value') for i in io_stats if i.get('op') is 'Write']
        lines.append(make_line('blkio_stats_io_service_bytes_write', container, io_write_stats[0] if io_write_stats else 0))
        network_stats = stats.get('networks')
        for stat_name, interface_stats in six.iteritems(network_stats or {}):
            for metric_name, metric_value in six.iteritems(interface_stats or {}):
                lines.append(make_line('networks_%s_%s' % (stat_name, metric_name), container, metric_value))
    lines.sort()
    string_buffer = "\n".join(lines)
    string_buffer += "\n"
    return string_buffer


def make_line(metric_name, container, metric):
    if not isinstance(metric, int):
        metric = 0
    return str('docker_stats_%s{container="%s"} %s' % (metric_name, container, metric))


def update_container_stats(stats_dict=None):
    stats_dict = stats_dict or {}
    running_containers = DOCKER_CLIENT.containers()
    for c in running_containers:
        k = c['Names'][0].lstrip('/')
        if not stats_dict.get(k):
            stats_dict.update({k: DOCKER_CLIENT.stats(container=c['Id'], stream=True)})
    container_names = [c['Names'][0].lstrip('/') for c in running_containers]
    for k, v in six.iteritems(dict(stats_dict)):
        if k not in container_names:
            stats_dict.pop(k)
    return stats_dict, time.time() + CONTAINER_REFRESH_INTERVAL

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
