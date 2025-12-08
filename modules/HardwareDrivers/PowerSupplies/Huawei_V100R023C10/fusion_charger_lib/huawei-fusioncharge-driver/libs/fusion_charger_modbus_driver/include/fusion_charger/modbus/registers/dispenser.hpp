// SPDX-License-Identifier: Apache-2.0
// Copyright 2020 - 2025 Pionix GmbH and Contributors to EVerest
#pragma once
#include <ctime>

#include "raw.hpp"
#include "utils.hpp"

namespace fusion_charger::modbus_driver {
using namespace modbus::registers::data_providers;
using namespace modbus_extensions;

struct DispenserRegistersConfig {
  uint16_t              manufacturer;
  uint16_t              model;
  uint16_t              protocol_version;
  uint16_t              hardware_version;
  std::string           software_version;
  std::string           esn;
  uint32_t              connector_count;
  std::function<bool()> get_door_status_alarm;
  std::function<bool()> get_water_alarm;
  std::function<bool()> get_epo_alarm;
  std::function<bool()> get_tilt_alarm;
};

struct DispenserRegisters {
  DataProviderHolding<uint16_t> manufacturer;
  DataProviderHolding<uint16_t> model;
  DataProviderHolding<uint16_t> protocol_version;
  DataProviderHolding<uint16_t> hardware_version;
  DataProviderStringHolding<48> software_version;

  DataProviderHolding<uint16_t>                charging_connectors_count;
  DataProviderStringHolding<22>                esn_dispenser;
  DataProviderCallbacksUnsolicitated<uint32_t> time_sync;
  DataProviderCallbacksUnsolicitated<uint16_t> door_status_alarm;
  DataProviderCallbacksUnsolicitated<uint16_t> water_alarm;
  DataProviderCallbacksUnsolicitated<uint16_t> epo_alarm;
  DataProviderCallbacksUnsolicitated<uint16_t> tilt_alarm;

  DispenserRegisters(DispenserRegistersConfig config)
      : manufacturer(config.manufacturer),
        model(config.model),
        protocol_version(config.protocol_version),
        hardware_version(config.hardware_version),
        software_version(config.software_version.c_str()),

        charging_connectors_count(config.connector_count),
        esn_dispenser(config.esn.c_str()),
        time_sync([]() { return std::time(NULL); },
                  utils::ignore_write<uint32_t>,
                  utils::always_report),
        door_status_alarm(
            utils::wrap_alarm_register_func(config.get_door_status_alarm),
            utils::ignore_write<uint16_t>,
            utils::always_report),
        water_alarm(utils::wrap_alarm_register_func(config.get_water_alarm),
                    utils::ignore_write<uint16_t>,
                    utils::always_report),
        epo_alarm(utils::wrap_alarm_register_func(config.get_epo_alarm),
                  utils::ignore_write<uint16_t>,
                  utils::always_report),
        tilt_alarm(utils::wrap_alarm_register_func(config.get_tilt_alarm),
                   utils::ignore_write<uint16_t>,
                   utils::always_report) {}
  void add_to_registry(
      modbus::registers::registry::ComplexRegisterRegistry& registry) {
    raw_registers::CommonDispenserRegisters::DataProviders
        common_data_providers{manufacturer, model, protocol_version,
                              hardware_version, software_version};

    raw_registers::CollectedDispenserRegisters::DataProviders
        collected_data_providers{
            charging_connectors_count,
            esn_dispenser,
            time_sync,
        };

    raw_registers::AlarmDispenserRegisters::DataProviders alarm_data_providers{
        door_status_alarm,
        water_alarm,
        epo_alarm,
        tilt_alarm,
    };

    registry.add(std::make_unique<raw_registers::CommonDispenserRegisters>(
        common_data_providers));
    registry.add(std::make_unique<raw_registers::CollectedDispenserRegisters>(
        collected_data_providers));
    registry.add(std::make_unique<raw_registers::AlarmDispenserRegisters>(
        alarm_data_providers));
  }
};

};  // namespace fusion_charger::modbus_driver
