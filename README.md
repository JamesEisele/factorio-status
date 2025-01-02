# Overview
This tool is meant to be deployed alongside a single Factorio server to provide a simple, stateless status page and a Prometheus `/metrics` endpoint that can be used for monitoring and alerting around game-specific details.

Since this relies entirely on Factorio RCON commands to pull data, there's no need for client-side or server-side mods but it does mean we're extremely limited in what we can scrape. For a more in depth approach to in-game monitoring via Prometheus, you should look at [celestialorb's Factorio Prometheus Exporter](https://github.com/celestialorb/factorio-prometheus-exporter).

## Out-of-scope
- Hardware stats (CPU, RAM usage) should come from a separate exporter like [node_exporter](https://github.com/prometheus/node_exporter) or [cAdvisor](https://github.com/google/cadvisor). It doesn't make sense to integrate them within this project.
- Monitoring more than one server with a single instance of this utility is out out-of-scope as the use case isn't obvious and it doesn't seem worthwhile to support things like asyncronous scraping with purposefully small resource footprint.
- We don't have any built-in mechanisms to setup HTTPS on the status page because we don't want to make any assumptions about your certificate and/or proxy setup. In the future, it might make sense to add a basic certificate request for a single provide like Cloudflare for demo purposes.

# Setup

## Exporter configuration
Regardless of how install and run the exporter, you'll need to:
1. Have a Factorio server running with it's RCON endpoint available.
2. Download or clone this repo.
3. Copy the `.env-sample` file and enter your Factorio server's info:
    ```shell
    $ cp .env-sample .env
    $ nano .env
    ```

## Full Docker compose stack

## Docker

## Python (recommended for dev / local testing only)
If you want to run the exporter and status page without Docker, you can do so if you've got Python 3.8 or greater already installed (`python3 --version`)
1. Clone the repo and `cd` into the project directory.
2. Setup your virtual environment:
    ```shell
    $ python3 -m venv venv

    # Linux venv activation:
    $ source venv/bin/activate
    (venv) $
    ```
3. Install dependencies:
    ```shell
    (venv) $ pip install -r requirements.txt
    ```
4. Run the utility:
    ```shell
    (venv) $ python3 factorio-status.py
    ```

# Prometheus scrape config
Wherever you're running your Prometheus instance, edit it's `prometheus.yml` config file to add a job for our exporter by adding a new `scrape_config` block with the appropriate exporter endpoint info and scrape interval.

If you adjusted the `SCRAPE_INTERVAL_S` variable from the default 15 seconds in the `.env` file that sets the interval that the *exporter* checks in with the game server, you'll want to adjust this scrape interval to match.

> `prometheus.yml`
```yaml
scrape_configs:
  - job_name: "factorio-exporter"
    static_configs:
      - targets: ["localhost:9042"]
    scrape_interval: 15s

```

After editing the `prometheus.yml` file, reload the Prometheus config to apply the changes. This can usually be done by sending a SIGHUP signal to the Prometheus process if it's been configured to allow it:

```shell
$ curl -X POST prometheus.example.com:9090/-/reload
```