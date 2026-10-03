#include "tuya_ble_select.h"

namespace esphome {
namespace tuya_ble {

static const char *const TAG = "tuya_ble_select";

void TuyaBLESelect::dump_config() {
  ESP_LOGCONFIG(TAG, "BLE Select");
  ESP_LOGCONFIG(TAG, "  DP id: %u", this->dp_id_);
  LOG_SELECT("  ", "Select", this);
}

void TuyaBLESelect::control(size_t index) {
  if(this->node_ == nullptr || index > 255) {
    return;
  }
  this->node_->write_dp(this->dp_id_, DP_TYPE_ENUM, {(unsigned char) index});
  // The device confirms with its next DP report; publish optimistically so the UI reacts at once.
  this->publish_state(index);
}

void TuyaBLESelect::on_dp(uint8_t dp_type, unsigned char *value, size_t len) {
  if(dp_type != DP_TYPE_ENUM || len < 1) {
    ESP_LOGW(TAG, "DP%u: unexpected dp_type %u (len %u) for a select", this->dp_id_, dp_type, (unsigned) len);
    return;
  }
  size_t index = value[len - 1];
  if(!this->has_index(index)) {
    ESP_LOGW(TAG, "DP%u: enum value %u has no matching option", this->dp_id_, (unsigned) index);
    return;
  }
  this->publish_state(index);
}

}  // namespace tuya_ble
}  // namespace esphome
