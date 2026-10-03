import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.components import tuya_ble_node
from esphome.const import CONF_MAX_VALUE, CONF_MIN_VALUE, CONF_STEP

from .. import tuya_ble_node_ns

DEPENDENCIES = ["tuya_ble_node"]

CONF_DP_ID = "dp_id"

TuyaBLENumber = tuya_ble_node_ns.class_("TuyaBLENumber", number.Number, cg.Component)

CONFIG_SCHEMA = cv.All(
    number.number_schema(TuyaBLENumber)
    .extend(
        {
            cv.Required(CONF_DP_ID): cv.int_range(0, 255),
            cv.Required(CONF_MIN_VALUE): cv.float_,
            cv.Required(CONF_MAX_VALUE): cv.float_,
            cv.Optional(CONF_STEP, default=1.0): cv.positive_float,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(tuya_ble_node.TUYA_BLE_NODE_SCHEMA)
)


async def to_code(config):
    var = await number.new_number(
        config,
        min_value=config[CONF_MIN_VALUE],
        max_value=config[CONF_MAX_VALUE],
        step=config[CONF_STEP],
    )
    await cg.register_component(var, config)

    cg.add(var.set_dp_id(config[CONF_DP_ID]))

    parent = await cg.get_variable(config[tuya_ble_node.CONF_TUYA_BLE_NODE_ID])
    cg.add(var.register_node(parent))
