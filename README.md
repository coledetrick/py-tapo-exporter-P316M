# Tapo P316M Prometheus Exporter

Polls a Tapo P316M power strip via `python-kasa` and exposes per-outlet
metrics on `/metrics` for Prometheus.

## Prerequisite

"Third-Party Services" must be enabled on the device (Tapo app -> Me ->
Third-Party Services -> On). Without it, the device uses the unsupported
TPAP encryption scheme and this exporter can't connect.

## Metrics exposed

- `tapo_outlet_power_watts{strip, outlet}`
- `tapo_outlet_voltage_volts{strip, outlet}`
- `tapo_outlet_current_amps{strip, outlet}`
- `tapo_outlet_state{strip, outlet}` (1 = on, 0 = off)
- `tapo_outlet_energy_today_kwh{strip, outlet}`
- `tapo_outlet_energy_month_kwh{strip, outlet}`
- `tapo_exporter_last_scrape_success` (1 = last poll of the strip succeeded)
- `tapo_exporter_last_scrape_duration_seconds`

## Run with Docker

```bash
docker build -t tapo-p316m-exporter .

docker run -d --name tapo-p316m-exporter \
  -e TAPO_HOST=172.16.234.89 \
  -e TAPO_USERNAME=your_tplink_email \
  -e TAPO_PASSWORD=your_tplink_password \
  -p 9499:9499 \
  tapo-p316m-exporter
```

Or in compose, alongside your existing Prometheus/Grafana stack:

```yaml
services:
  tapo-p316m-exporter:
    build: ./tapo-exporter
    environment:
      - TAPO_HOST=172.16.234.89
      - TAPO_USERNAME=your_tplink_email
      - TAPO_PASSWORD=your_tplink_password
    ports:
      - "9499:9499"
```

## Add to Prometheus

In `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'tapo_p316m'
    scrape_interval: 15s
    static_configs:
      - targets: ['tapo-p316m-exporter:9499']  # service name if same Docker network
```

Reload Prometheus without restarting it:

```bash
curl -X POST http://localhost:9090/-/reload
```

Then confirm the target shows `UP` at `http://<host_ip>:9090/targets`.

## Notes

- The exporter polls the strip itself every `SCRAPE_INTERVAL_SECONDS`
  (default 15s), independent of how often Prometheus scrapes the
  exporter's `/metrics` endpoint. Keep Prometheus's own
  `scrape_interval` for this job at or above that value.
- If the connection ever reverts to failing with a `TPAP` error again,
  re-check the Third-Party Services toggle in the Tapo app — TP-Link
  firmware updates have been known to reset it.
