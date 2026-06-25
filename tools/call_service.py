#!/usr/bin/env python3
"""Call a no-arg user service on the device over the native API."""
import asyncio, re, sys
from pathlib import Path
from aioesphomeapi import APIClient
HOST, PORT = "192.168.178.40", 6053
def read_psk():
    s = (Path(__file__).resolve().parent.parent / "secrets.yaml").read_text()
    m = re.search(r"esphome_utility_bridge_api_password:\s*(\S+)", s)
    return m.group(1).strip().strip("'\"")
async def main(name):
    cli = APIClient(HOST, PORT, "", noise_psk=read_psk())
    await cli.connect(login=True)
    try:
        _e, services = await cli.list_entities_services()
        svc = next((s for s in services if s.name == name), None)
        if svc is None:
            raise SystemExit(f"service {name!r} not found")
        print(f"Calling service: {name}")
        r = cli.execute_service(svc, {})
        if asyncio.iscoroutine(r): await r
        await asyncio.sleep(2)
    finally:
        await cli.disconnect()
asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "reset_radio"))
