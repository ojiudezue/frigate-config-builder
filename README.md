# Frigate Config Builder

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ojiudezue/frigate-config-builder.svg)](https://github.com/ojiudezue/frigate-config-builder/releases)
[![License](https://img.shields.io/github/license/ojiudezue/frigate-config-builder.svg)](LICENSE)

A Home Assistant integration that automatically discovers cameras from your HA integrations and generates complete [Frigate NVR](https://frigate.video/) configuration files.

## Features

- **Auto-Discovery**: Automatically discovers cameras from:
  - UniFi Protect
  - Amcrest / Dahua
  - Reolink
  - Manual RTSP entries
  
- **Smart Configuration**: Generates optimized Frigate config with:
  - Separate high-res (record) and low-res (detect) streams
  - Proper hardware acceleration settings
  - go2rtc streams for live view
  - Camera groups from HA Areas
  
- **Easy Selection**: Simple checkbox UI to select which cameras to include

- **One-Click Generation**: Button entity to regenerate config anytime

- **Stale Detection**: Binary sensor alerts you when cameras change

## Requirements

- Home Assistant 2024.1.0 or newer
- [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) HACS integration (for UniFi Protect)
- Frigate NVR (any recent version)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/ojiudezue/frigate-config-builder` as an **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Download the latest release from [GitHub Releases](https://github.com/ojiudezue/frigate-config-builder/releases)
2. Extract to `config/custom_components/frigate_config_builder`
3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Frigate Config Builder"
3. Complete the 5-step setup wizard:

### Step 1: Connection
- **Output Path**: Where to save `frigate.yml` (default: `/config/www/frigate.yml`)
- **Frigate URL**: Optional - for auto-pushing config to Frigate API
- **Auto Push**: Enable to automatically push and restart Frigate

### Step 2: Hardware
- **Detector Type**: `edgetpu` (Coral), `cpu`, `openvino`, `tensorrt`
- **Detector Device**: `usb`, `pci`, etc.
- **Hardware Acceleration**: `vaapi` (Intel), `cuda` (NVIDIA), `qsv`, etc.

### Step 3: MQTT
- Auto-detects from Home Assistant MQTT integration
- Or configure manually

### Step 4: Features
- Audio Detection
- Face Recognition
- Semantic Search
- License Plate Recognition (LPR)
- Bird Classification
- BirdsEye view settings

### Step 5: Retention
- Days to keep alerts, detections, motion, snapshots

## Usage

### Selecting Cameras

1. Go to **Settings** → **Devices & Services**
2. Click **Configure** on Frigate Config Builder
3. Check/uncheck cameras to include
4. Click **Submit**

### Generating Config

**Option 1: Button Entity**
- Find `button.frigate_config_builder_generate` in your entities
- Add to a dashboard or automation
- Press to generate

**Option 2: Service Call**
```yaml
service: frigate_config_builder.generate
data:
  push: false  # Set true to push to Frigate API
```

### Viewing Generated Config

The config is saved to your output path (default `/config/www/frigate.yml`).

Access via: `http://your-ha-ip:8123/local/frigate.yml`

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `button.frigate_config_builder_generate` | Button | Trigger config generation |
| `sensor.frigate_config_builder_cameras_selected` | Sensor | Count of selected cameras |
| `sensor.frigate_config_builder_last_generated` | Sensor | Last generation timestamp |
| `binary_sensor.frigate_config_builder_config_stale` | Binary Sensor | ON when cameras have changed |

## Services

### `frigate_config_builder.generate`
Generate Frigate configuration file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `push` | boolean | false | Push to Frigate API and restart |

### `frigate_config_builder.refresh_cameras`
Re-run camera discovery.

## Automations

### Notify When Config is Stale
```yaml
automation:
  - alias: "Notify Frigate Config Stale"
    trigger:
      - platform: state
        entity_id: binary_sensor.frigate_config_builder_config_stale
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Frigate Config"
          message: "Camera configuration has changed. Regenerate your Frigate config."
```

### Auto-Regenerate Weekly
```yaml
automation:
  - alias: "Weekly Frigate Config Regeneration"
    trigger:
      - platform: time
        at: "03:00:00"
    condition:
      - condition: time
        weekday: sun
    action:
      - service: frigate_config_builder.generate
        data:
          push: true
```

## Supported Cameras

### UniFi Protect
- All camera models
- Doorbells (including package cameras)
- Automatic high/low resolution stream detection
- Requires [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source)

### Amcrest / Dahua
- All models with RTSP support
- Credentials pulled from HA config entry
- Channel selection (default: 1, configurable for multi-channel NVRs)

### Reolink
- All models with RTSP support
- HTTP-FLV streams for go2rtc compatibility
- Credentials pulled from HA config entry

### Manual Cameras
- Any RTSP camera not auto-discovered
- Configure via Options flow

## Troubleshooting

### Cameras not discovered

1. Ensure the camera integration is configured in Home Assistant
2. For UniFi Protect: Install [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source)
3. Check that camera entities are not disabled in HA

### RTSP URLs not working

1. Verify camera credentials in HA integration
2. Check network connectivity to camera
3. Try the URL directly in VLC to test

### Generated config has errors

1. Check Frigate logs for specific error
2. Ensure hardware acceleration settings match your system
3. Verify MQTT broker is accessible from Frigate

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Frigate NVR](https://frigate.video/) - The amazing NVR this generates configs for
- [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) - For UniFi Protect RTSP discovery
- [Home Assistant](https://www.home-assistant.io/) - The platform that makes this possible
