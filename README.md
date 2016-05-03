docker-stats-exporter
============

docker-stats-exporter is a Prometheus Metrics Exporter which integrates with the Docker API to transform Docker stats into Prometheus metrics.
The application was built on top of the Flask framework.

The project was created to give an alternative to the popular cAdvisor metrics exporter for Prometheus. This application aims to be a light weight alternative.

Dependencies
============

The required dependencies to build the application
* GNU Make 4.1
* Python 2.7.11+
* virtualenv 15.0.1

The required python package to run the application
* Flask >= 0.10.1
* Flask-Cache >= 0.13.1
* docker-py >= 1.8.1
* uWSGI >= 2.0.12

Other requirements
* docker >= 1.6.1

Development
=======
To setup a development environment
```
make venv
make requirements
```

Build
=======
To build the docker image locally
```
make docker
```

Run
=======
To run the exporter
```
docker run \
       -p 8081:8081 \
       -v "/var/run/docker.sock:/var/run/docker.sock" \
       -v "/sys/fs/cgroup:/sys/fs/cgroup:ro" \
       -v "/proc:/proc:ro" \
       cdewitt/docker-stats-exporter
```

Configuration
=======
To configure the service to use pseudo files instead of the docker api for stats set the USE_PSEUDO_FILES environment variable and be sure
to mount the proper cgroup and proc volumes.

```
docker run \
       -p 8081:8081 \
       -v "/var/run/docker.sock:/var/run/docker.sock" \
       -v "/sys/fs/cgroup:/sys/fs/cgroup:ro" \
       -v "/proc:/proc:ro" \
       -e "USE_PSEUDO_FILES=1" \
       cdewitt/docker-stats-exporter
```
To figure out where your control groups are mounted, you can run
```
grep cgroup /proc/mounts
```


Here is a full list of the available environment variables you can set and a short explanation for each.
* REFRESH_INTERVAL
  * Determines the time in seconds between cache expirations on the /metrics endpoint.
  * Defaults to 60 seconds
* CONTAINER_REFRESH_INTERVAL
  * The time in seconds between refreshing the list of available containers. Depending on the number of containers on the docker host this may be an expensive process so a higher interval may be suitable.
  * Defaults to 120 seconds
* DOCKER_CLIENT_URL
  * The URL with which the service will communicate with the docker api
  * Defaults to unix://var/run/docker.sock
* USE_PSEUDO_FILES
  * Determines if the exporter will use the docker stats api or the cgroup and proc files to determines metrics. Metric names will be slightly different due to differences in parsing.
  * Defaults to False
* CGROUP_DIRECTORY
  * Determines the volume the service will parse for pseudo files
  * Defaults to /sys/fs/cgroup
* PROC_DIRECTORY
  * Determines the volume the service will parse for network information
  * Defaults to /proc

Roadmap
=======
* Implement a 100% test coverage