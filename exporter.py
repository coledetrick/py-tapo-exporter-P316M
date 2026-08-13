"""
Prometheus exporter for a TP-Link Tapo P316M power strip.

Polls the strip on an interval via python-kasa and exposes per-outlet
metrics (power, voltage, current, energy, state) on /metrics for
Prometheus to scrape.

Requires "Third-Party Services" enabled in the Tapo app for this device
(Tapo app -> Me -> Third-Party Services -> On). Without it, the device
falls back to the unsupported TPAP encryption scheme and this script
will fail to connect.
"""

import asyncio
import logging
import os
import time

from kasa import Credentials, Discover
from prometheus_client import Gauge, start_http_server

TAPO_HOST = os.environ["TAPO_HOST"]
TAPO_USERNAME = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", "9499"))
SCRAPE_INTERVAL_SECONDS = int(os.environ.get("SCRAPE_INTERVAL_SECONDS", "15"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tapo-p316m-exporter")

LABELS = ["strip", "outlet"]

power_watts = Gauge("tapo_outlet_power_watts", "Current power draw per outlet", LABELS)
voltage_volts = Gauge("tapo_outlet_voltage_volts", "Voltage per outlet", LABELS)
current_amps = Gauge("tapo_outlet_current_amps", "Current per outlet", LABELS)
outlet_state = Gauge("tapo_outlet_state", "Outlet on/off state (1=on, 0=off)", LABELS)
energy_today_kwh = Gauge("tapo_outlet_energy_today_kwh", "Energy consumed today per outlet", LABELS)
energy_month_kwh = Gauge("tapo_outlet_energy_month_kwh", "Energy consumed this month per outlet", LABELS)
scrape_success = Gauge("tapo_exporter_last_scrape_success", "1 if the last scrape succeeded, else 0")
scrape_duration = Gauge("tapo_exporter_last_scrape_duration_seconds", "Duration of the last scrape")


def feature_value(features, name):
    """Safely pull a feature's current value by name, or None if absent."""
    feat = features.get(name)
    return feat.value if feat is not None else None


async def poll_once():
    dev = await Discover.discover_single(
        TAPO_HOST,
        credentials=Credentials(TAPO_USERNAME, TAPO_PASSWORD),
    )
    await dev.update()

    strip_name = dev.alias or dev.model or TAPO_HOST

    for child in dev.children:
        outlet_name = child.alias or child.device_id
        labels = {"strip": strip_name, "outlet": outlet_name}
        feats = child.features

        state_val = feature_value(feats, "state")
        if state_val is not None:
            outlet_state.labels(**labels).set(1 if state_val else 0)

        power_val = feature_value(feats, "current_consumption")
        if power_val is not None:
            power_watts.labels(**labels).set(power_val)

        voltage_val = feature_value(feats, "voltage")
        if voltage_val is not None:
            voltage_volts.labels(**labels).set(voltage_val)

        current_val = feature_value(feats, "current")
        if current_val is not None:
            current_amps.labels(**labels).set(current_val)

        today_val = feature_value(feats, "consumption_today")
        if today_val is not None:
            energy_today_kwh.labels(**labels).set(today_val)

        month_val = feature_value(feats, "consumption_this_month")
        if month_val is not None:
            energy_month_kwh.labels(**labels).set(month_val)

    await dev.disconnect()


def poll_loop():
    while True:
        start = time.monotonic()
        try:
            asyncio.run(poll_once())
            scrape_success.set(1)
            log.info("Scrape succeeded")
        except Exception:
            scrape_success.set(0)
            log.exception("Scrape failed")
        scrape_duration.set(time.monotonic() - start)
        time.sleep(SCRAPE_INTERVAL_SECONDS)


def main():
    start_http_server(EXPORTER_PORT)
    log.info(f"Exporter listening on :{EXPORTER_PORT}/metrics, polling every {SCRAPE_INTERVAL_SECONDS}s")
    poll_loop()


if __name__ == "__main__":
    main()
