#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include "esphome/components/select/select.h"
#include "esphome/components/tuya_ble_tracker/common.h"

namespace esphome {
namespace tuya_ble {

// Enum datapoint that can be read and written (e.g. a mode). The option index is the raw enum value.
class TuyaBLESelect : public select::Select, public Component {
  public:
    void dump_config() override;
    void set_dp_id(uint8_t dp_id) { this->dp_id_ = dp_id; }

    void register_node(TYBLENode *node) {
      ESP_LOGD("tuya_ble_select", "Select registered for DP%u", this->dp_id_);
      this->node_ = node;
      node->register_dp_callback(this->dp_id_, [this](uint8_t dp_type, unsigned char *value, size_t len) {
        this->on_dp(dp_type, value, len);
      });
    }

  protected:
    uint8_t dp_id_;
    TYBLENode *node_{nullptr};

    void control(size_t index) override;
    void on_dp(uint8_t dp_type, unsigned char *value, size_t len);
};

}  // namespace tuya_ble
}  // namespace esphome
