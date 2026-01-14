# Frigate Config Builder - Project Plan

## Overview

**Project:** HACS Integration for Home Assistant  
**Purpose:** Auto-discover cameras from HA integrations and generate complete Frigate NVR configuration files  
**Repository:** `frigate-config-builder`  

---

## Philosophy

**"Discover everything, select what you want, generate once."**

- Auto-discover all cameras from HA integrations
- User selects which cameras to include (checkbox list)
- No per-camera config in UI (that's Frigate's job)
- Generate a complete, working config file
- Advanced users edit zones/masks directly in Frigate

---

## Milestones

### Milestone 1: Foundation
**Goal:** Integration installs, config flow works, generates static config sections

#### Deliverables
- [ ] Valid HACS repository structure
- [ ] `manifest.json` with correct dependencies
- [ ] `const.py` with all constants and defaults
- [ ] `__init__.py` with async_setup_entry, coordinator pattern
- [ ] `config_flow.py` with all 5 setup steps
- [ ] `generator.py` producing valid YAML (static sections only)
- [ ] `strings.json` with UI text

#### Acceptance Criteria
- [ ] Integration appears in HACS (custom repo)
- [ ] "Add Integration" shows Frigate Config Builder
- [ ] Config flow completes all 5 steps without errors
- [ ] Generates valid `frigate.yml` to configured output path
- [ ] Generated YAML has: mqtt, detectors, ffmpeg, record, snapshots, features sections
- [ ] Cameras section has placeholder comment (no discovery yet)

#### Files
```
custom_components/frigate_config_builder/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── generator.py
├── strings.json
└── translations/
    └── en.json
```

---

### Milestone 2: Camera Discovery
**Goal:** Auto-discover cameras from UniFi Protect, Amcrest, Reolink

#### Deliverables
- [ ] `discovery/coordinator.py` - orchestrates all adapters
- [ ] `discovery/base.py` - abstract adapter interface
- [ ] `discovery/unifiprotect.py` - UniFi Protect adapter (primary)
- [ ] `discovery/amcrest.py` - Amcrest/Dahua adapter
- [ ] `discovery/reolink.py` - Reolink adapter
- [ ] `discovery/manual.py` - Manual camera definitions
- [ ] Generator updated to include discovered cameras

#### Acceptance Criteria
- [ ] Discovers all UniFi Protect cameras via `expose-camera-stream-source`
- [ ] Each UniFi camera has high-res (record) and low-res (detect) URLs
- [ ] Package cameras (G6 Doorbell) handled correctly
- [ ] Discovers Amcrest cameras using HA config entry credentials
- [ ] Discovers Reolink cameras using HA config entry credentials
- [ ] Generated config includes `go2rtc.streams` section
- [ ] Generated config includes `cameras` section with proper structure
- [ ] Detect stream separated from record stream (Frigate best practice)

#### Files
```
custom_components/frigate_config_builder/
└── discovery/
    ├── __init__.py
    ├── coordinator.py
    ├── base.py
    ├── unifiprotect.py
    ├── amcrest.py
    ├── reolink.py
    └── manual.py
```

---

### Milestone 3: Entities & UI
**Goal:** Camera selection UI, status entities, generate button

#### Deliverables
- [ ] `options_flow.py` - camera selection checkboxes, group config
- [ ] `button.py` - Generate button entity
- [ ] `sensor.py` - Status sensors (camera count, last generated)
- [ ] `binary_sensor.py` - Config stale sensor
- [ ] `services.yaml` - Service definitions
- [ ] Camera groups from HA Areas (auto-generation)
- [ ] Event firing for new camera discovery

#### Acceptance Criteria
- [ ] Options flow shows discovered cameras grouped by source
- [ ] Checkboxes to enable/disable each camera
- [ ] NEW badge on cameras not in previous config
- [ ] UNAVAIL badge on cameras currently unavailable
- [ ] "Generate" button triggers config generation
- [ ] `sensor.frigate_config_builder_cameras_selected` shows count
- [ ] `sensor.frigate_config_builder_last_generated` shows timestamp
- [ ] `binary_sensor.frigate_config_builder_config_stale` turns on when cameras change
- [ ] Camera groups auto-generated from HA Areas
- [ ] `frigate_config_builder.generate` service works

#### Files
```
custom_components/frigate_config_builder/
├── options_flow.py
├── button.py
├── sensor.py
├── binary_sensor.py
└── services.yaml
```

---

### Milestone 4: Polish & Release (Optional)
**Goal:** Production readiness, edge cases, documentation

#### Deliverables
- [ ] Frigate API push support (`frigate_url`, `auto_push`)
- [ ] Push button entity
- [ ] Frigate connection sensors (version, uptime)
- [ ] Diagnostic sensors (per-adapter counts, discovery duration)
- [ ] Improved error handling with user-friendly messages
- [ ] HACS `hacs.json` metadata
- [ ] `README.md` with installation and usage
- [ ] GitHub Actions for HACS validation

#### Acceptance Criteria
- [ ] HACS validation workflow passes
- [ ] Config push to Frigate API works
- [ ] Frigate auto-restarts after push
- [ ] README documents all features with screenshots
- [ ] Handles edge cases gracefully (see Risk Register)

---

## Dependencies

### Required
| Dependency | Purpose | Install |
|------------|---------|---------|
| `expose-camera-stream-source` | Get RTSP URLs from UniFi Protect | HACS custom repo |
| Home Assistant 2024.1+ | Minimum HA version | Core |

### Optional (for camera discovery)
| Integration | Cameras Discovered | Notes |
|-------------|-------------------|-------|
| `unifiprotect` | UniFi Protect cameras | Most common |
| `amcrest` | Amcrest/Dahua cameras | Uses config entry creds |
| `reolink` | Reolink cameras | Uses config entry creds |

---

## Configuration Schema

### Config Flow (One-time Setup)

| Step | Options |
|------|---------|
| 1. Connection | `output_path`, `frigate_url` (optional), `auto_push` |
| 2. Hardware | `detector_type`, `detector_device`, `hwaccel`, `network_interfaces` |
| 3. MQTT | `mqtt_auto`, `mqtt_host`, `mqtt_port`, `mqtt_user`, `mqtt_password` |
| 4. Features | `audio_detection`, `face_recognition`, `semantic_search`, `lpr`, `birdseye_*` |
| 5. Retention | `retain_alerts`, `retain_detections`, `retain_motion`, `retain_snapshots` |

### Options Flow (Runtime)

| Section | Options |
|---------|---------|
| Cameras | `selected_cameras` (multi-select checkboxes) |
| Groups | `auto_groups_from_areas`, `manual_groups` |
| Manual | `manual_cameras` (list of {name, record_url, detect_url}) |
| Overrides | `credential_overrides` (per-host credentials) |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `expose-camera-stream-source` API changes | High | Low | Pin version, document dependency |
| UniFi Protect entity structure changes | Medium | Low | Use entity attributes, not ID patterns |
| HA config entry format changes | Medium | Low | Version check, graceful fallback |
| Large camera count (50+) | Low | Low | Pagination in options flow |
| Frigate schema changes | Medium | Medium | Include `version` field, validate against schema |
| RTSP URL contains special chars | Medium | High | URL encode passwords in generator |
| Camera unavailable during discovery | Low | High | Mark as unavailable, don't fail entirely |

---

## Timeline Estimate

| Milestone | Generation Time | Testing Time | Total |
|-----------|----------------|--------------|-------|
| M1: Foundation | 45 min | 30 min | 1h 15m |
| M2: Discovery | 30 min | 45 min | 1h 15m |
| M3: Entities & UI | 30 min | 30 min | 1h |
| M4: Polish | 30 min | 30 min | 1h |

**Total: ~4.5 hours** (generation + testing)

---

## Success Metrics

1. **Functional:** Generated config accepted by Frigate without errors
2. **Complete:** All cameras discovered with correct RTSP URLs  
3. **Accurate:** Generated config matches working reference (`frigate.yml`)
4. **Usable:** Non-technical user completes setup via UI
5. **Maintainable:** New camera adapter requires <100 lines

---

## Reference Files

| File | Purpose | Location |
|------|---------|----------|
| Working Frigate config | Reference output | `/mnt/user-data/outputs/frigate.yml` |
| Discovery script | UniFi Protect URL extraction | `/mnt/user-data/outputs/generate_frigate_config.py` |
| Quality plan | Test definitions | `QUALITY.md` |
| Build plan | Architecture & snippets | `BUILD.md` |
