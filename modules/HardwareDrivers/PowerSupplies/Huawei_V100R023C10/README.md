# Huawei V100R023C10 PSU

## Voltage measurements

The Huawei V100R023C10 does not provide voltage measurements, instead it needs an external voltage measurement device that measures the "upstream" voltage (meaning directly after the PSU, before any relay).
Also, Everest needs a voltage and current measurement regularly.

For the upstream voltage two options are available which (see `upstream_voltage_source` config option):
- Using an isolation monitoring device (`IMD`)
- Using an overvoltage monitoring device (`OVM`)

For the everest measurements two options are available:
- None (not recommended, needs `HACK_publish_requested_voltage_current` to work properly)
- Using a carside powermeter (ideally the powermeter that is connected to the EvseManager's `powermeter_car_side`)
- Using a carside powermeter but during cable check using an `OVM` (see `HACK_use_ovm_while_cable_check` config option)

## Power Supply Mock

The mock is a single executable that simulates the communication behaviour of a Huawei V100R023C10 power supply. It is used to test the software stack without needing the actual hardware.

It opens a socket on port 8502 to accept connections from the everest module and receives and answers goose messages.

The mock is built together with the everest module, but can also be [built separately](#build-separately-from-module) if needed.
The mock is not installed by default but can be if `INSTALL_FUSION_CHARGER_MOCK` is set to `ON` in cmake.

Note that the mock uses a constant hmac key instead of generating a new one for each charge session.

### Build separately from module

```bash
cd modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib
mkdir build
cd build
cmake ..
make -j$(nproc)
```

Binary is located in `modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib/build/fusion-charger-dispenser-library/power_stack_mock/fusion_charger_mock`

### Mock options

The mock has a few environment variables (enable or disable by setting them to `1`/`true` or `0`/`false`):
- `FUSION_CHARGER_MOCK_DISABLE_SEND_HMAC`: If set the mock will disable securing the goose messages with an hmac. They are still sent, just not secured.
- `FUSION_CHARGER_MOCK_DISABLE_VERIFY_HMAC`: If set the mock will disable verifying the hmac of the received goose messages. This also allows to receive completely unsigned messages.
- `FUSION_CHARGER_MOCK_ETH`: The ethernet interface to use for receiving and sending goose messages. Defaults to `veth0`.

It also has one optional command line argument, being the path to a folder with certificates and keys for [mTLS](#mock-mtls).

### Mock mTLS

The mock can be run with mTLS enabled. For this, one needs to create a folder with the following files:
- `dispenser_ca.crt.pem`: The CA certificate used to sign the dispensers' certificates.
- `psu.crt.pem`: The certificate used by the mock to identify itself as a PSU.
- `psu.key.pem`: The private key of the PSU certificate.

These files can be generated with dummy values using the script located here (Note that this also generates the corresponding files for the dispenser): `modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib/fusion-charger-dispenser-library/user-acceptance-tests/test_certificates/generate.sh`

## Running the SIL

### Single connector SIL

To run the single connector SIL, the following commands are needed to create the virtual ethernet interface:

```bash
sudo ip link add veth0 type veth peer name veth1
sudo ip link set dev veth0 up
sudo ip link set dev veth1 up
```

After that, run the SIL in one terminal: `sudo -E ./run-scripts/run-huawei-fusion-charge-sil.sh`

In another Terminal start the power supply mock: `sudo ./modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib/fusion-charger-dispenser-library/power_stack_mock/fusion_charger_mock`

In a third terminal start NodeRed: `./run-scripts/nodered-sil-dc.sh`

### Dual Connector SIL

In addition to the `veth` creation process for the single connector SIL run the following commands, as they are needed to simulate the iso15118 between the two virtual cars:

```bash
sudo ip link add veth00 type veth peer name veth01
sudo ip link set dev veth00 up
sudo ip link set dev veth01 up
sudo ip link add veth10 type veth peer name veth11
sudo ip link set dev veth10 up
sudo ip link set dev veth11 up
```

After that, run the dual SIL in one terminal: `sudo -E ./run-scripts/run-huawei-fusion-charge-sil-dual.sh`

In another Terminal start the power supply mock: `sudo ./modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib/fusion-charger-dispenser-library/power_stack_mock/fusion_charger_mock`

In a third terminal start NodeRed: `./run-scripts/nodered-sil-dc-dual.sh`


### Quad Connector SIL

In addition to the `veth` creation process for the single and dual connector SILs run the following commands:

```bash
sudo ip link add veth20 type veth peer name veth21
sudo ip link set dev veth20 up
sudo ip link set dev veth21 up
sudo ip link add veth30 type veth peer name veth31
sudo ip link set dev veth30 up
sudo ip link set dev veth31 up
```

After that, run the dual SIL in one terminal: `sudo -E ./run-scripts/run-huawei-fusion-charge-sil-quad.sh`

In another Terminal start the power supply mock: `sudo ./modules/HardwareDrivers/PowerSupplies/Huawei_V100R023C10/fusion_charger_lib/fusion-charger-dispenser-library/power_stack_mock/fusion_charger_mock`

In a third terminal start NodeRed: `./run-scripts/nodered-sil-dc-quad.sh`
