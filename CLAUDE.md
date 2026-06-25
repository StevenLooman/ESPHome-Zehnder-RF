# CLAUDE.md — ESPHome Zehnder RF fan controller

Project-specific guidance for Claude Code. Read this first when resuming.

## What this is

ESPHome external component that drives a **Zehnder/BUVA ventilation fan** over a
**nRF905 433 MHz radio** wired to an **ESP32** (board `esp32doit-devkit-v1`,
Arduino framework). It joins the fan's RF network, polls fan state, sends
set-speed/timer commands, and (new work) passively decodes RF frames from *other*
remotes so external changes show up in Home Assistant immediately instead of only
on the 60 s poll.

- Device IP: **192.168.178.40** (web server on :80, HA API on :6053).
- Main config: `utility-bridge.yaml`. Components in `components/{nrf905,zehnder}/`.
- ESPHome **2026.6.2**, run from the repo venv.

## Build / upload / logs

Always use the repo virtualenv:

```bash
.venv/bin/esphome compile utility-bridge.yaml     # build only
.venv/bin/esphome upload  utility-bridge.yaml      # OTA flash (device must be up)
.venv/bin/esphome run     utility-bridge.yaml      # compile + upload + logs
.venv/bin/esphome logs    utility-bridge.yaml      # stream logs over the network
```

OTA upload is the normal path — the ESP32 is deployed, not on USB. Standing
permission (from the user) to **build & upload firmware autonomously** while
debugging. Logger level is `DEBUG`; `LOGV` lines (e.g. "Write config OK") are
hidden, `LOGE` ("Config write failed") always show.

## Hard rules

- **Commit/push ONLY when the user explicitly asks.** Lots of debug scaffolding is
  uncommitted on purpose; do not commit it unprompted.
- **`secrets.yaml`** holds the HA API encryption key
  (`esphome_utility_bridge_api_password`, a noise PSK) and Wi-Fi/OTA passwords.
  Read it only to extract a key for a local API client; keep values local/redacted,
  never paste them into committed files or logs.
- Current working branch: `debug/state-trace-esphome-2026-compat`.

## Hardware wiring (nRF905 ⇆ ESP32)

MCU module: **Espressif ESP32-WROOM-32** (on an `esp32doit-devkit-v1` dev board).
Physical mounting: the ESP32+nRF905 sits **on the main Zehnder unit** (inches away),
so **RF range is never the cause** — if we can't hear the main unit, it's identity/
pairing or RX config, not distance.
Fan model: **Zehnder ComfoFan S** (RF-controlled extract/MVHR unit). The real remote
on its network is `type=0x16 id=0x2E`, addressing the main as `to[Main 0x01 id=0x00]`
(the `0x00` is a broadcast-to-main convention, NOT the main's real id — see below).

## Fan pairing & identity (discovered 2026-06-24)

The controller joins the fan's RF network and is registered by the main unit. The
**known-good identity** captured by a successful re-pair:

| Field | Value |
|---|---|
| Network id (`fan_networkId`, = nRF905 rx/tx address) | `0xCB109EA2` |
| Main unit type / id | `0x01` / **`0xD9`** |
| Our device type / id | `0x03` (REMOTE_CONTROL) / `0x86` (random) |

A *wrong* stored `fan_main_unit_id` (`0xB7`) was the cause of "fan ignores all our
commands/polls" — we addressed a main id that doesn't exist, so the unit never
replied. The real main id is **`0xD9`**. If polls time out with healthy SPI again,
suspect a corrupted/stale pairing first; re-pair to recover.

**Re-pairing procedure** (after the `createDeviceID` random→sequential hack broke the
original auto-discovered pairing): power-cycle the ComfoFan S (off ~10 s, on) to open
its ~10 min join window, then call the **`start_pairing`** API service. Discovery
captures the correct network/main id, registers our (random) device id, and saves to
flash (`pref_.save` on join complete). The unit does NOT answer join requests outside
the power-up window. After a join you can read `FAN_SETTINGS` (live speed/voltage/
timer) and commands take effect (verified: High → speed 1→3, 30 V→90 V).

SPI bus: `clk=GPIO14  mosi=GPIO13  miso=GPIO12`. Control: `cs=GPIO23  cd=GPIO33
ce=GPIO27  pwr=GPIO26  txen=GPIO25  am=GPIO32  dr=GPIO35`. SPI clock 1 MHz.

Radio facts that matter when debugging:
- **Half-duplex.** Must go to standby/Idle before TX (the `startTx` standby fix).
- Status bits: **DR** (Data Ready, bit 5), **AM** (Address Match, bit 7). No RSSI.
- SPI register access is per-CSN-cycle; config registers are retained in PowerDown.
- **MISO = GPIO12 is an ESP32 strapping pin with an internal pull-DOWN** → an open
  MISO reads a clean deterministic `0x00`. So a disconnected MISO produces a
  *consistent* total read failure, not erratic noise (relevant to the wedge below).

## The "radio stops after a while" wedge — investigation status

Symptom: after some healthy runtime the nRF905 SPI **reads** return garbage/zeros →
`writeConfigRegisters()` readback verify fails ("Config write failed", LOGE) on
every TX **and** RX payloads come back all-zero. It does NOT clear on ESP soft
reboot, nor on a PWR-pin power-down/re-init, nor a brief unplug.

**RESOLVED (2026-06-24):** root cause was a **loose 3.3 V** rail browning out the
nRF905 — garbage SPI reads (`Config write failed`) *and* dead RF; the ~hours onset
was thermal drift shifting a marginal contact. Fix: reseat, and permanently
**solder** the 3.3 V. (Confirmed live: wiggling the rail toggled `Config write
failed` OK↔FAIL in real time.) The separate "polls time out with healthy SPI" issue
was unrelated — a wrong stored main-unit id; see the pairing section above.

Remaining diagnostics (the forensic break-history sensors + `reset_radio` service
were removed once the cause was known):

- **Idle SPI health-probe**: every 5 s while in Receive (gated to skip within 2 s of
  a TX) it does a read-only config-register verify and **logs the wedge/recovery
  transition** (`Idle SPI probe: config readback FAILED` / `… responding again`).
- `getLastConfigWriteOk()` — live SPI health, exposed as the **`RF SPI healthy`**
  binary sensor (ON = healthy; OFF = SPI wedged → check the 3.3 V rail).

### Reading on-device sensors (web server)

ESPHome **2026.7.0 removes the old object_id URLs** (`/sensor/radio_break_count`).
Use the **entity NAME**, URL-encoded (`%20` for spaces) — verified working on
2026.6.2. Note the numeric (`/sensor/`) vs text (`/text_sensor/`) path split.

```bash
enc() { echo "${1// /%20}"; }                              # spaces -> %20
# numeric sensors
for n in "Fan self-heal threshold" "Fan poll success rate"; do
  curl -s "http://192.168.178.40/sensor/$(enc "$n")"; echo
done
# SPI health (binary_sensor): ON/true = healthy
curl -s "http://192.168.178.40/binary_sensor/$(enc "RF SPI healthy")"; echo
# identity text_sensors
for n in "Fan network id" "Fan main unit id" "Fan main unit type" \
         "Fan controller id" "Fan controller type"; do
  curl -s "http://192.168.178.40/text_sensor/$(enc "$n")"; echo
done
# Snapshot everything at once (SSE stream, not deprecated):
curl -sN "http://192.168.178.40/events" & sleep 2; kill %1
```

The native-API helpers in `tools/` (aioesphomeapi) are the stable path and are
**unaffected** by the URL deprecation.

## RF logging & tooling

Every frame is decoded + raw-dumped to the log (DEBUG level): `RX FRAME`/`RX RAW`
on receive and `TX FRAME`/`TX RAW` on transmit — handy for watching the protocol
live. The idle SPI health-probe also logs wedge/recovery transitions.

The earlier one-off debug scaffolding has been trimmed: TRACE state-machine
logging, the `replay_frame` service + `tools/replay_test.py`, the PWR-pin
`reset_radio`, the persisted break-history, and the `createDeviceID`
random→sequential hack are all gone (the SPI-wedge cause — loose 3.3 V — and the
pairing fix made them moot).

API services: `set_speed`, `start_pairing` (re-pair, needs the unit's join
window), and `reinit_radio` — re-applies the nRF905 config + TX address without a
reboot. `reinit_radio` recovers a soft config glitch and logs whether SPI
verified, but it does NOT power-cycle the chip, so it can't clear a true wedge (a
VCC cut is still required for that).

`tools/` holds aioesphomeapi clients that read the PSK from `secrets.yaml`:
`restart_device.py`, `press_button.py`, `call_service.py`.

## Pointers

- In-repo handoff: `docs/superpowers/status/2026-06-21-rf-listening-external-ha.md`.
- Claude long-term memory index: `~/.claude/projects/.../memory/MEMORY.md`
  (`zehnder-rf-listening-work`, `zehnder-rf-replay-harness`).
