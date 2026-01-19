# Frigate Config Builder

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ojiudezue/frigate-config-builder.svg)](https://github.com/ojiudezue/frigate-config-builder/releases)
[![License](https://img.shields.io/github/license/ojiudezue/frigate-config-builder.svg)](LICENSE)

**Stop hand-coding your Frigate config.** This Home Assistant integration automatically discovers all your cameras and generates a complete, optimized [Frigate NVR](https://frigate.video/) configuration file with one click.

---

## 🆕 What's New in v0.4.0.5

### Frigate 0.17 Support

This release adds full support for Frigate 0.17's new features:

| Feature | Description |
|---------|-------------|
| **Version Selection** | Choose between Frigate 0.14.x (stable) or 0.17.x (latest) in setup |
| **GenAI Integration** | Configure AI-powered event descriptions using Ollama, Gemini, OpenAI, or Azure |
| **YOLOv9 Detector** | New detector option for Frigate 0.17+ |
| **Improved LPR** | 0.17's "small" model now outperforms the old "large" model |
| **Tiered Retention** | 0.17's new retention structure (alerts/detections separate from motion) |
| **Release Tracking** | New sensor shows latest Frigate stable and beta releases |

### New Entities

- **Frigate Releases Sensor** - Shows latest stable/beta versions from GitHub, notifies when updates are available

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
2. Walk through the 5-step wizard (now with Frigate version selection!)
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
  provider: ollama  # Or gemini, openai, azure_openai
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
| **UniFi Protect** | ✅ Full support | All cameras, doorbells, package cameras |
| **Reolink** | ✅ Full support | Including multi-lens cameras like TrackMix |
| **Amcrest/Dahua** | ✅ Full support | All RTSP-capable models |
| **Generic RTSP** | ✅ Manual entry | Any camera with RTSP URL |

---

## Frigate Version Compatibility

| Frigate Version | Support Level | Notes |
|-----------------|---------------|-------|
| **0.14.x** | ✅ Full support | Stable release, recommended for production |
| **0.17.x** | ✅ Full support | Latest features: GenAI, YOLOv9, tiered retention |

### Breaking Changes in Frigate 0.17

If upgrading from 0.14 to 0.17, be aware of these changes:

1. **Retention Structure** - Recording retention is now fully tiered (alerts/detections separate from motion)
2. **GenAI Config** - Global config only configures provider; object-specific settings moved to per-camera config
3. **LPR Model** - The "small" model in 0.17 outperforms the old "large" model
4. **strftime_fmt** - Fully removed in 0.17

The integration handles these differences automatically when you select your Frigate version.

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click ⋮ → **Custom repositories**
3. Add: `https://github.com/ojiudezue/frigate-config-builder`
4. Select type: **Integration**
5. Click **Download**
6. Restart Home Assistant

### Manual Installation

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
| **Version & Output** | Frigate version (0.14/0.17), where to write frigate.yml, optional API connection |
| **Hardware** | Coral TPU (or YOLOv9 for 0.17), GPU acceleration, network interfaces |
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
| `sensor.cameras_selected` | Sensor | Number of cameras in your config |
| `sensor.cameras_found` | Sensor | Total discovered cameras |
| `sensor.last_generated` | Sensor | When config was last generated |
| `sensor.discovery_status` | Sensor | Per-adapter discovery stats |
| `sensor.frigate_status` | Sensor | Frigate version and connection (if URL configured) |
| `sensor.frigate_releases` | Sensor | Latest stable/beta Frigate releases from GitHub |
| `binary_sensor.config_needs_update` | Binary Sensor | ON when cameras changed |

### Frigate Releases Sensor

The new releases sensor polls GitHub daily and provides:

- **State**: Latest stable Frigate version
- **Attributes**:
  - `latest_stable` - Current stable release (e.g., "0.14.1")
  - `latest_beta` - Current beta/RC release (e.g., "0.17.0-beta1")
  - `stable_release_date` - When stable was released
  - `beta_release_date` - When beta was released
  - `configured_version` - Your configured Frigate version
  - `update_available` - True if a newer version exists
  - `recent_releases` - Last 5 releases

**Example Automation - Notify on New Frigate Release:**

```yaml
automation:
  - alias: "Notify on new Frigate release"
    trigger:
      - platform: state
        entity_id: sensor.frigate_config_builder_frigate_releases
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: notify.mobile_app
        data:
          title: "New Frigate Release"
          message: "Frigate {{ states('sensor.frigate_config_builder_frigate_releases') }} is available!"
```

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

## Example Automations

### Notify When New Cameras Found

```yaml
automation:
  - alias: "New camera discovered"
    trigger:
      - platform: event
        event_type: frigate_config_builder_cameras_refreshed
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new_cameras | length > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "New Camera Found"
          message: "{{ trigger.event.data.new_cameras | join(', ') }}"
```

### Weekly Config Regeneration

```yaml
automation:
  - alias: "Weekly Frigate config update"
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

### Dashboard Button Card

```yaml
type: button
name: Generate Frigate Config
icon: mdi:file-cog
tap_action:
  action: call-service
  service: frigate_config_builder.generate
  data:
    push: false
```

---

## Generated Config Example

### Frigate 0.14.x Config

```yaml
mqtt:
  enabled: true
  host: 192.168.1.10
  port: 1883

detectors:
  coral:
    type: edgetpu
    device: usb

ffmpeg:
  hwaccel_args: preset-vaapi

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
          roles: [record]
    detect:
      width: 1280
      height: 720
    record:
      enabled: true
      retain:
        days: 7
        mode: motion
      events:
        retain:
          default: 30
```

### Frigate 0.17.x Config (with GenAI)

```yaml
mqtt:
  enabled: true
  host: 192.168.1.10
  port: 1883

detectors:
  coral:
    type: edgetpu
    device: usb

genai:
  enabled: true
  provider: ollama
  model: llava

ffmpeg:
  hwaccel_args: preset-vaapi

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
          roles: [record]
    detect:
      width: 1280
      height: 720
    record:
      enabled: true
      retain:
        days: 1
      alerts:
        retain:
          days: 30
      detections:
        retain:
          days: 30
```

---

## Troubleshooting

### Cameras not discovered?

1. **UniFi Protect**: Install [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) from HACS
2. **Reolink**: Ensure the camera integration is configured in Home Assistant
3. **All cameras**: Check that camera entities aren't disabled in Home Assistant

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

## Requirements

- Home Assistant 2024.1.0 or newer
- Frigate NVR 0.14.x or 0.17.x
- For UniFi Protect: [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) HACS integration

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

### v0.4.0.5 (2026-01-18)
- ✨ Added Frigate 0.17 support
- ✨ New Frigate version selection in setup wizard
- ✨ GenAI configuration (Ollama, Gemini, OpenAI, Azure)
- ✨ YOLOv9 detector option for 0.17+
- ✨ Improved LPR model defaults (0.17's "small" > 0.14's "large")
- ✨ New Frigate Releases sensor - tracks latest stable/beta versions
- 🔧 Version-aware config generation

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
- [expose-camera-stream-source](https://github.com/felipecrs/hass-expose-camera-stream-source) - For UniFi Protect RTSP URL extraction
- [Home Assistant](https://www.home-assistant.io/) - The platform that makes this possible
