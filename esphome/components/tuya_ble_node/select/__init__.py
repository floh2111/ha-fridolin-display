import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.components import tuya_ble_node
from esphome.const import CONF_OPTIONS

from .. import tuya_ble_node_ns

DEPENDENCIES = ["tuya_ble_node"]

CONF_DP_ID = "dp_id"

TuyaBLESelect = tuya_ble_node_ns.class_("TuyaBLESelect", select.Select, cg.Component)

CONFIG_SCHEMA = cv.All(
    select.select_schema(TuyaBLESelect)
    .extend(
        {
            cv.Required(CONF_DP_ID): cv.int_range(0, 255),
            # The position in this list is the raw enum value of the datapoint.
            cv.Required(CONF_OPTIONS): cv.All(cv.ensure_list(cv.string_strict), cv.Length(min=1, max=256)),
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(tuya_ble_node.TUYA_BLE_NODE_SCHEMA)
)


async def to_code(config):
    var = await select.new_select(config, options=config[CONF_OPTIONS])
    await cg.register_component(var, config)

    cg.add(var.set_dp_id(config[CONF_DP_ID]))

    parent = await cg.get_variable(config[tuya_ble_node.CONF_TUYA_BLE_NODE_ID])
    cg.add(var.register_node(parent))
