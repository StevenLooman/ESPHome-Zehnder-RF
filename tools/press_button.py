#!/usr/bin/env python3
"""Press a named template button over the native API (substring match)."""
import asyncio, re, sys
from pathlib import Path
from aioesphomeapi import APIClient
HOST, PORT = "192.168.178.40", 6053
def read_psk() -> str:
    secrets = (Path(__file__).resolve().parent.parent / "secrets.yaml").read_text()
    m = re.search(r"esphome_utility_bridge_api_password:\s*(\S+)", secrets)
    if not m: raise SystemExit("API key not found")
    return m.group(1).strip().strip("'\"")
async def main() -> None:
    want = (sys.argv[1] if len(sys.argv) > 1 else "high 10").lower()
    cli = APIClient(HOST, PORT, "", noise_psk=read_psk())
    await cli.connect(login=True)
    try:
        entities, _ = await cli.list_entities_services()
        btns = [e for e in entities if e.name.lower().endswith(want) or want in e.name.lower()]
        # prefer button domain
        btns = [e for e in btns if type(e).__name__ == "ButtonInfo"] or btns
        if not btns: raise SystemExit(f"button matching '{want}' not found")
        b = btns[0]
        print(f"Pressing: {b.name} (key={b.key})")
        r = cli.button_command(b.key)
        if asyncio.iscoroutine(r): await r
        await asyncio.sleep(2)
    finally:
        await cli.disconnect()
asyncio.run(main())
