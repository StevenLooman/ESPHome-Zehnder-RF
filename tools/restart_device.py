#!/usr/bin/env python3
"""Press the device's restart button over the native API.

Used to test whether an SPI/radio wedge is a soft fault (recovered by reboot)
or a hard fault (persists). Reuses the PSK from secrets.yaml.
"""
import asyncio
import re
from pathlib import Path

from aioesphomeapi import APIClient

HOST = "192.168.178.40"
PORT = 6053


def read_psk() -> str:
    secrets = (Path(__file__).resolve().parent.parent / "secrets.yaml").read_text()
    m = re.search(r"esphome_utility_bridge_api_password:\s*(\S+)", secrets)
    if not m:
        raise SystemExit("API key not found in secrets.yaml")
    return m.group(1).strip().strip("'\"")


async def main() -> None:
    cli = APIClient(HOST, PORT, "", noise_psk=read_psk())
    await cli.connect(login=True)
    try:
        entities, _services = await cli.list_entities_services()
        # entities is a flat list of entity-info objects; find a button whose
        # name mentions restart/herstart.
        buttons = [e for e in entities
                   if ("restart" in e.name.lower() or "herstart" in e.name.lower())]
        if not buttons:
            raise SystemExit("restart button not found")
        btn = buttons[0]
        print(f"Pressing button: {btn.name} (key={btn.key})")
        result = cli.button_command(btn.key)
        if asyncio.iscoroutine(result):
            await result
        await asyncio.sleep(2)
    finally:
        await cli.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
