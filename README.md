# Frigate Config Builder

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ojiudezue/frigate-config-builder.svg)](https://github.com/ojiudezue/frigate-config-builder/releases)
[![License](https://img.shields.io/github/license/ojiudezue/frigate-config-builder.svg)](LICENSE)

**Stop hand-coding your Frigate config.** This Home Assistant integration automatically discovers all your cameras and generates a complete, optimized [Frigate NVR](https://frigate.video/) configuration file with one click.

---

## ⚠️ Prerequisites

Before installing Frigate Config Builder, you need:

### Required

| Dependency | Description | Link |
|------------|-------------|------|
| **Frigate NVR** | The NVR this tool generates configs for | [frigate.video](https://frigate.video/) |

### Recommended

| Dependency | Description | Link |
|------------|-------------|------|
| **expose-camera-stream-source** | **Required for UniFi Protect cameras.** Exposes RTSP URLs that Home Assistant normally hides. | [HACS](https://github.com/felipecrs/hass-expose-camera-stream-source) |

> **📌 Important:** Without `expose-camera-stream-source`, UniFi Protect cameras will not be discovered. This is because Home Assistant's UniFi Protect integration doesn't expose RTSP stream URLs by default.

---

## 🆕 What's New in v0.4.0.7

### Frigate 0.16 as Stable Baseline

This release updates to **Frigate 0.16** as the stable baseline:

| Change | Description |
|--------|-------------|
| **Default Version** | Now 0.16 (was 0.14) |
| **TensorRT Removed** | Use ONNX for Nvidia GPUs |
| **Detection Default** | 0.16+ disables detection by default - we always enable it |
| **Audio Codec** | go2rtc accepts any audio codec in 0.16+ |
| **Record Presets** | Updated to use `preset-record-generic-audio-aac` |

### HACS Integration Discovery Fix

Fixed camera discovery for HACS custom integrations:
- **Amcrest Custom** (bcpearce/HomeAssistant-Amcrest-Custom)
- **Dahua** (rroller/dahua)

Both use different config entry keys (`address` vs `host`, `rtsp_port` vs `port`).

---

## Why Use This?

Setting up Frigate is powerful but tedious. For each camera you need to:
- Find the RTSP URL (different for every manufacturer)
- Configure separate streams for recording vs detection
- Set up go2rtc for live viewing
- Add hardware acceleration settings
- Configure MQTT for Home Assistant integration

**Frigate Config Builder does all of this automatically.**

---

## What Can You Do With It?

### 🎯 Use Case 1: First-Time Frigate Setup

You just installed Frigate and have 8 cameras across UniFi Protect, Reolink, and an old Amcrest. Instead of spending hours researching RTSP URLs and YAML syntax:

1. Install this integration
2. Walk through the 5-step wizard
3. Click "Generate Config"
4. Copy the file to Frigate

**Time saved: 2-4 hours**

### 🔄 Use Case 2: Adding New Cameras

You bought 3 new cameras. Instead of manually editing your frigate.yml:

1. Add cameras to Home Assistant as usual
2. Open Frigate Config Builder settings
3. Check the new cameras
4. Click "Generate Config"

The integration detects new cameras automatically and alerts you when your config needs updating.

### 🏠 Use Case 3: Multi-Brand Camera Systems

You have cameras from different manufacturers (UniFi + Reolink + generic RTSP). Each has different URL formats:

- UniFi: `rtsps://192.168.1.1:7441/...`
- Reolink: `rtsp://192.168.1.50:554/h264Preview_01_main`
- Amcrest/Dahua: `rtsp://192.168.1.60/cam/realmonitor?channel=1&subtype=0`
- Generic: `rtsp://admin:pass@192.168.1.100/stream1`

This integration normalizes everything into a consistent Frigate config with proper high-res (recording) and low-res (detection) streams.

### ⚡ Use Case 4: Hardware Optimization

You have a Coral TPU and Intel QuickSync but aren't sure how to configure them. The setup wizard asks about your hardware and generates optimized settings:

```yaml
detectors:
  coral:
    type: edgetpu
    device: usb

ffmpeg:
  hwaccel_args: preset-vaapi
```

### 🤖 Use Case 5: GenAI Event Descriptions (Frigate 0.17+)

Want AI-generated descriptions of security events? Enable GenAI in the features step:

```yaml
genai:
  enabled: true
  provider: ollama
  model: llava
```

### 🔔 Use Case 6: Automated Config Updates

Want Frigate to always stay in sync? Create an automation:

```yaml
automation:
  - alias: "Regenerate Frigate config when cameras change"
    trigger:
      - platform: state
        entity_id: binary_sensor.frigate_config_builder_config_stale
        to: "on"
    action:
      - service: frigate_config_builder.generate
        data:
          push: true
```

---

## Supported Cameras

| Integration | Status | Notes |
|-------------|--------|-------|
| **UniFi Protect** | ✅ Full support | All cameras, doorbells, package cameras. **Requires [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source)** |
| **Reolink** | ✅ Full support | Including multi-lens cameras like TrackMix |
| **Amcrest** | ✅ Full support | Core HA integration + HACS Custom integration |
| **Dahua** | ✅ Full support | Core HA + HACS rroller/dahua integration |
| **Generic RTSP** | ✅ Full support | Any camera added via HA's Generic Camera integration |
| **Manual** | ✅ Full support | User-defined RTSP URLs via options |

---

## Frigate Version Compatibility

| Frigate Version | Support Level | Notes |
|-----------------|---------------|-------|
| **0.16.x** | ✅ Full support | **Current stable** - recommended for production |
| **0.17.x** | ✅ Full support | Latest features: GenAI, YOLOv9, tiered retention |

### Key Changes in Frigate 0.16

If you were using 0.14, be aware of these 0.16 changes (handled automatically by this integration):

1. **Detection disabled by default** - Must explicitly set `detect: enabled: true`
2. **TensorRT removed** - Use ONNX detector for Nvidia GPUs
3. **ROCm MIGraphX removed** - Use ONNX detector for AMD GPUs
4. **Audio codec flexibility** - go2rtc now accepts any audio codec
5. **HA Add-on config location** - Moved from `/config/frigate.yml` to `/addon_configs/`

### Breaking Changes in Frigate 0.17

If upgrading from 0.16 to 0.17:

1. **Retention Structure** - Recording retention is now fully tiered (alerts/detections separate)
2. **GenAI Config** - Global config only configures provider; object settings moved per-camera
3. **LPR Model** - The "small" model in 0.17 outperforms the old "large" model
4. **strftime_fmt** - Deprecated in 0.16, fully removed in 0.17

The integration handles these differences automatically when you select your Frigate version.

---

## Installation

### Step 1: Install Prerequisites

Before installing Frigate Config Builder:

1. **Install Frigate NVR** - Follow the [official Frigate documentation](https://docs.frigate.video/)

2. **Install expose-camera-stream-source** (Required for UniFi Protect):
   - Open HACS in Home Assistant
   - Search for "expose-camera-stream-source"
   - Click **Download**
   - Restart Home Assistant

### Step 2: Install Frigate Config Builder

#### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click ⋮ → **Custom repositories**
3. Add: `https://github.com/ojiudezue/frigate-config-builder`
4. Select type: **Integration**
5. Click **Download**
6. Restart Home Assistant

#### Manual Installation

1. Download the [latest release](https://github.com/ojiudezue/frigate-config-builder/releases)
2. Extract to `config/custom_components/frigate_config_builder/`
3. Restart Home Assistant

---

## Quick Start

### Step 1: Add the Integration

Go to **Settings → Devices & Services → Add Integration → Frigate Config Builder**

### Step 2: Configure Your Setup

The wizard guides you through:

| Step | What You'll Configure |
|------|----------------------|
| **Version & Output** | Frigate version (0.16/0.17), where to write frigate.yml, optional API connection |
| **Hardware** | Detector (Coral, ONNX, CPU), GPU acceleration, network interfaces |
| **MQTT** | Auto-detected from Home Assistant or manual entry |
| **Features** | Face recognition, license plates, audio detection, GenAI (0.17+), etc. |
| **GenAI** | (0.17+ only) Provider selection, API keys for cloud services |
| **Retention** | How long to keep recordings |

### Step 3: Select Your Cameras

Click **Configure** on the integration to see all discovered cameras:

- ✅ Check cameras to include
- See which cameras are online/offline
- Cameras auto-group by Home Assistant area

### Step 4: Generate!

Press the **Generate Config** button or call the service:

```yaml
service: frigate_config_builder.generate
```

Your config is saved to the path you specified (default: `/config/www/frigate.yml`).

---

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `button.generate_config` | Button | Create the Frigate configuration file |
| `button.push_to_frigate` | Button | Send config to Frigate and restart (if URL configured) |
| `button.refresh_cameras` | Button | Re-scan for new cameras |
| `button.check_frigate_updates` | Button | Check GitHub for latest Frigate versions |
| `sensor.cameras_selected` | Sensor | Number of cameras in your config |
| `sensor.cameras_found` | Sensor | Total discovered cameras |
| `sensor.last_generated` | Sensor | When config was last generated |
| `sensor.discovery_status` | Sensor | Per-adapter discovery stats |
| `sensor.frigate_status` | Sensor | Frigate version and connection (if URL configured) |
| `sensor.frigate_releases` | Sensor | Latest stable/beta Frigate releases from GitHub |
| `binary_sensor.config_needs_update` | Binary Sensor | ON when cameras changed |

---

## Services

### `frigate_config_builder.generate`

Generate a new Frigate configuration file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `push` | boolean | false | Also send to Frigate API and restart |

**Example:**
```yaml
service: frigate_config_builder.generate
data:
  push: true
```

### `frigate_config_builder.refresh_cameras`

Re-scan all integrations for cameras.

```yaml
service: frigate_config_builder.refresh_cameras
```

---

## Generated Config Example

### Frigate 0.16.x Config

```yaml
mqtt:
  host: 192.168.1.10
  port: 1883
  user: mqtt_user
  password: mqtt_pass

detectors:
  default:
    type: edgetpu
    device: usb

ffmpeg:
  hwaccel_args: preset-vaapi

detect:
  enabled: true
  width: 640
  height: 360
  fps: 5

record:
  enabled: true
  retain:
    days: 7
    mode: motion
  alerts:
    retain:
      days: 30
      mode: motion
  detections:
    retain:
      days: 30
      mode: motion

go2rtc:
  streams:
    front_door:
      - rtsp://192.168.1.1:7441/...

cameras:
  front_door:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://127.0.0.1:8554/front_door
          roles: [detect]
        - path: rtsp://192.168.1.1:7441/...
          roles: [record, audio]
      hwaccel_args: preset-vaapi
      output_args:
        record: preset-record-generic-audio-aac
    detect:
      enabled: true
      width: 1280
      height: 720
      fps: 5

version: "0.16-1"
```

### Frigate 0.17.x Config (with GenAI)

```yaml
mqtt:
  host: 192.168.1.10
  port: 1883

detectors:
  default:
    type: edgetpu
    device: usb

genai:
  enabled: true
  provider: ollama
  model: llava

ffmpeg:
  hwaccel_args: preset-vaapi

detect:
  enabled: true
  width: 640
  height: 360
  fps: 5

record:
  enabled: true
  retain:
    days: 7
    mode: motion
  alerts:
    retain:
      days: 30
  detections:
    retain:
      days: 30

go2rtc:
  streams:
    front_door:
      - rtsp://192.168.1.1:7441/...

cameras:
  front_door:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://127.0.0.1:8554/front_door
          roles: [detect]
        - path: rtsp://192.168.1.1:7441/...
          roles: [record, audio]
    detect:
      enabled: true
      width: 1280
      height: 720
      fps: 5

version: "0.16-1"
```

---

## Troubleshooting

### Cameras not discovered?

| Camera Type | Solution |
|-------------|----------|
| **UniFi Protect** | Install [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) from HACS - **required** |
| **Reolink** | Ensure the Reolink integration is configured in Home Assistant |
| **Amcrest/Dahua** | Ensure the Amcrest or Dahua integration is configured. Works with both core HA and HACS custom integrations. |
| **Generic RTSP** | Add camera via Settings → Devices → Add Integration → Generic Camera |
| **All cameras** | Check that camera entities aren't disabled in Home Assistant |

### UniFi Protect cameras missing?

This is the most common issue. UniFi Protect integration doesn't expose RTSP URLs by default.

**Solution:**
1. Install [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) from HACS
2. Restart Home Assistant
3. Click "Refresh Cameras" in Frigate Config Builder

### Config won't push to Frigate?

1. Verify the Frigate URL is accessible from Home Assistant
2. Check Frigate logs for API errors
3. Ensure Frigate's config path is writable

### Generated config has errors?

1. Check Frigate logs for the specific error
2. Verify hardware acceleration matches your system
3. For 0.17, ensure GenAI provider/API key are correct
4. Open an [issue](https://github.com/ojiudezue/frigate-config-builder/issues) with your config and error

### GenAI not working? (0.17+)

1. **Ollama**: Ensure Ollama is running and accessible from Frigate container
2. **Cloud providers**: Verify API key is correct and has proper permissions
3. Check Frigate logs for GenAI-related errors

---

## Requirements Summary

| Requirement | Required? | Notes |
|-------------|-----------|-------|
| Home Assistant | ✅ Yes | 2024.1.0 or newer |
| Frigate NVR | ✅ Yes | 0.16.x (stable) or 0.17.x (latest) |
| expose-camera-stream-source | ⚠️ For UniFi | Required to discover UniFi Protect cameras |
| Camera integrations | ⚠️ Varies | Reolink, Amcrest, Dahua, etc. as needed |

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

### Adding a New Camera Adapter

Camera adapters live in `discovery/`. See `discovery/base.py` for the interface. A new adapter typically requires <100 lines of code.

---

## Changelog

### v0.4.0.7 (2026-01-19)
- 🔄 Updated to Frigate 0.16 as stable baseline (was 0.14)
- 🔧 TensorRT detector removed - use ONNX for Nvidia GPUs
- 🔧 Updated record presets to use `preset-record-generic-audio-aac`
- 🔧 Version-aware config generation for 0.16 vs 0.17
- 📝 Updated documentation for 0.16 changes

### v0.4.0.6 (2026-01-19)
- 🐛 Fixed HACS integration discovery for Amcrest Custom and Dahua
- 🔧 Handle `address` config key (Dahua HACS)
- 🔧 Distinguish `rtsp_port` from HTTP `port`
- 📝 Added debug logging for camera discovery

### v0.4.0.5 (2026-01-18)
- ✨ Added Frigate 0.17 support
- ✨ New Frigate version selection in setup wizard
- ✨ GenAI configuration (Ollama, Gemini, OpenAI, Azure)
- ✨ YOLOv9 detector option for 0.17+
- ✨ Improved LPR model defaults
- ✨ New Frigate Releases sensor
- ✨ Dahua camera support
- ✨ Generic RTSP camera discovery
- ⚡ Parallel camera discovery

### v0.4.0.4 (2026-01-17)
- 🐛 Fixed Reolink camera detection delay
- ✨ Multi-step options flow for editing settings

### v0.4.0.0 (2026-01-15)
- ✨ Initial release with multi-step setup wizard
- ✨ Camera discovery for UniFi, Reolink, Amcrest
- ✨ Hardware-optimized config generation

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Frigate NVR](https://frigate.video/) - The incredible NVR this generates configs for
- [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) - Essential for UniFi Protect RTSP URL extraction
- [Home Assistant](https://www.home-assistant.io/) - The platform that makes this possible
