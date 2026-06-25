import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import fan
from esphome.const import CONF_ID, CONF_UPDATE_INTERVAL

from esphome.components.nrf905 import nRF905Component


DEPENDENCIES = ["nrf905"]

zehnder_ns = cg.esphome_ns.namespace("zehnder")
ZehnderRF = zehnder_ns.class_("ZehnderRF", cg.Component, fan.Fan)

CONF_NRF905 = "nrf905"

# Optional: pin the paired identity (captured via the start_pairing service) so it
# survives a flash erase / fresh install without re-running discovery. network_id,
# main_unit_id and device_id must be given together; the type fields default to the
# usual ComfoFan values (main=0x01, device=0x03 REMOTE_CONTROL).
CONF_NETWORK_ID = "network_id"
CONF_MAIN_UNIT_TYPE = "main_unit_type"
CONF_MAIN_UNIT_ID = "main_unit_id"
CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_ID = "device_id"

# Self-healing: consecutive poll timeouts before the device auto re-pairs. On by
# default (10 ≈ 10 min at the 60 s poll interval); set 0 to disable.
CONF_SELF_HEAL_AFTER = "self_heal_after"

CONF_PAIRING_KEYS = (CONF_NETWORK_ID, CONF_MAIN_UNIT_ID, CONF_DEVICE_ID)


def _validate_pairing(config):
    present = [k for k in CONF_PAIRING_KEYS if k in config]
    if present and len(present) != len(CONF_PAIRING_KEYS):
        raise cv.Invalid(
            f"To pin the pairing, set all of {', '.join(CONF_PAIRING_KEYS)} together "
            f"(missing: {', '.join(k for k in CONF_PAIRING_KEYS if k not in config)})"
        )
    return config


CONFIG_SCHEMA = cv.All(
    fan.fan_schema(ZehnderRF)
    .extend(
        {
            cv.Required(CONF_NRF905): cv.use_id(nRF905Component),
            cv.Optional(CONF_UPDATE_INTERVAL, default="30s"): cv.update_interval,
            cv.Optional(CONF_NETWORK_ID): cv.hex_uint32_t,
            cv.Optional(CONF_MAIN_UNIT_TYPE, default=0x01): cv.hex_uint8_t,
            cv.Optional(CONF_MAIN_UNIT_ID): cv.hex_uint8_t,
            cv.Optional(CONF_DEVICE_TYPE, default=0x03): cv.hex_uint8_t,
            cv.Optional(CONF_DEVICE_ID): cv.hex_uint8_t,
            cv.Optional(CONF_SELF_HEAL_AFTER, default=10): cv.uint32_t,
        }
    )
    .extend(cv.COMPONENT_SCHEMA),
    _validate_pairing,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await fan.register_fan(var, config)

    nrf905 = await cg.get_variable(config[CONF_NRF905])
    cg.add(var.set_rf(nrf905))

    cg.add(var.set_update_interval(config[CONF_UPDATE_INTERVAL]))
    cg.add(var.set_self_heal_threshold(config[CONF_SELF_HEAL_AFTER]))

    if all(k in config for k in CONF_PAIRING_KEYS):
        cg.add(
            var.set_paired_config(
                config[CONF_NETWORK_ID],
                config[CONF_MAIN_UNIT_TYPE],
                config[CONF_MAIN_UNIT_ID],
                config[CONF_DEVICE_TYPE],
                config[CONF_DEVICE_ID],
            )
        )
