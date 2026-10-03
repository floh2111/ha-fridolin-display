#include "tuya_ble_switch.h"

namespace esphome {
namespace tuya_ble {

static const char *const TAG = "tuya_ble_switch";

void TuyaBLESwitch::dump_config() {
  ESP_LOGCONFIG(TAG, "BLE Switch");
  ESP_LOGCONFIG(TAG, "  DP id: %u", this->dp_id_);
  LOG_SWITCH("  ", "Switch", this);
}

void TuyaBLESwitch::write_state(bool state) {
  if(this->node_ == nullptr) {
    return;
  }
  this->node_->write_dp(this->dp_id_, DP_TYPE_BOOL, {(unsigned char) (state ? 1 : 0)});
  // The device confirms with its next DP report; publish optimistically so the UI reacts at once.
  this->publish_state(state);
}

void TuyaBLESwitch::on_dp(uint8_t dp_type, unsigned char *value, size_t len) {
  if(dp_type != DP_TYPE_BOOL || len < 1) {
    ESP_LOGW(TAG, "DP%u: unexpected dp_type %u (len %u) for a switch", this->dp_id_, dp_type, (unsigned) len);
    return;
  }
  this->publish_state(value[0] != 0);
}

}  // namespace tuya_ble
}  // namespace esphome
