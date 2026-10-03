#include "tuya_ble_number.h"
#include <cmath>

namespace esphome {
namespace tuya_ble {

static const char *const TAG = "tuya_ble_number";

void TuyaBLENumber::dump_config() {
  ESP_LOGCONFIG(TAG, "BLE Number");
  ESP_LOGCONFIG(TAG, "  DP id: %u", this->dp_id_);
  LOG_NUMBER("  ", "Number", this);
}

void TuyaBLENumber::control(float value) {
  if(this->node_ == nullptr) {
    return;
  }
  // Tuya "value" datapoints are 4-byte big-endian signed integers.
  int32_t raw = (int32_t) lroundf(value);
  uint32_t u = (uint32_t) raw;
  this->node_->write_dp(this->dp_id_, DP_TYPE_VALUE,
                        {(unsigned char) (u >> 24), (unsigned char) (u >> 16), (unsigned char) (u >> 8), (unsigned char) u});
  // The device confirms with its next DP report; publish optimistically so the UI reacts at once.
  this->publish_state((float) raw);
}

void TuyaBLENumber::on_dp(uint8_t dp_type, unsigned char *value, size_t len) {
  if(dp_type != DP_TYPE_VALUE || len == 0 || len > 4) {
    ESP_LOGW(TAG, "DP%u: unexpected dp_type %u (len %u) for a number", this->dp_id_, dp_type, (unsigned) len);
    return;
  }
  int64_t raw = 0;
  for(size_t i = 0; i < len; i++) {
    raw = (raw << 8) | value[i];
  }
  if(len == 4 && (value[0] & 0x80)) {
    raw -= (int64_t) 1 << 32;
  }
  this->publish_state((float) raw);
}

}  // namespace tuya_ble
}  // namespace esphome
