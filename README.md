# ESPHome-Zehnder-RF

## Installation

```shell
# Install venv.
$ python3 -m venv .venv

# Activate venv.
$ source .venv/bin/activate

# Install esphome (version pinned in requirements.txt).
$ pip install -r requirements.txt
```

## Developing

```shell
# Activate venv.
$ source .venv/bin/activate

# Build.
$ esphome compile utility-bridge.yaml

# Upload.
$ esphome upload utility-bridge.yaml

# View logs
$ esphome logs utility-bridge.yaml
```

## Other sources

* Forked from: https://github.com/Sanderhuisman/ESPHome-Zehnder-RF
* Other implementation: https://github.com/eelcohn/nRF905-API
* CAN bus based implementation: https://github.com/yoziru/esphome-zehnder-comfoair
