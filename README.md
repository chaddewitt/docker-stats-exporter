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

Roadmap
=======
* Implement a 100% test coverage
* Convert from using the Docker "/containers/$CONTAINER_ID/stats" API to using cgroup pseudo-files for metrics. Currently when using the docker API the docker daemon on the host can consume a significant portion of CPU depending on tghe number of running containers. Using psuedo-files looks to be a promising alternative.