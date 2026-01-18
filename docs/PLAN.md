# Frigate Config Builder - Project Plan

## Overview

**Project:** HACS Integration for Home Assistant  
**Purpose:** Auto-discover cameras from HA integrations and generate complete Frigate NVR configuration files  
**Repository:** `frigate-config-builder`  
**GitHub:** https://github.com/ojiudezue/frigate-config-builder  
**Local Path:** `/Users/ojiudezue/Library/CloudStorage/OneDrive-Personal/2025/frigate-config-builder`  
**Target HA:** MadroneHAOS  
**Current Version:** 0.4.0.0

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

### Milestone 1: Foundation ✅ COMPLETE
**Goal:** Integration installs, config flow works, generates static config sections

#### Deliverables
- [x] Valid HACS repository structure
- [x] `manifest.json` with correct dependencies
- [x] `const.py` with all constants and defaults
- [x] `__init__.py` with async_setup_entry, coordinator pattern
- [x] `config_flow.py` with all 5 setup steps
- [x] `generator.py` producing valid YAML (static sections only)
- [x] `strings.json` with UI text

---

### Milestone 2: Camera Discovery ✅ COMPLETE
**Goal:** Auto-discover cameras from UniFi Protect, Amcrest, Reolink

#### Deliverables
- [x] `discovery/coordinator.py` - orchestrates all adapters
- [x] `discovery/base.py` - abstract adapter interface
- [x] `discovery/unifiprotect.py` - UniFi Protect adapter (primary)
- [x] `discovery/amcrest.py` - Amcrest/Dahua adapter
- [x] `discovery/reolink.py` - Reolink adapter (with disabled entity support)
- [x] `discovery/manual.py` - Manual camera definitions
- [x] Generator updated to include discovered cameras

---

### Milestone 3: Entities & UI ✅ COMPLETE
**Goal:** Camera selection UI, status entities, generate button

#### Deliverables
- [x] Options flow with camera selection checkboxes
- [x] `button.py` - Generate and Refresh button entities
- [x] `sensor.py` - Status sensors (camera count, last generated)
- [x] `binary_sensor.py` - Config stale sensor
- [x] `services.yaml` - Service definitions
- [x] Camera groups from HA Areas (auto-generation option)
- [x] Event firing for new camera discovery
- [x] Exclude unavailable cameras toggle

---

### Milestone 4: Polish & Release ✅ COMPLETE (v0.4.0.0)
**Goal:** Production readiness, edge cases, documentation

#### Deliverables
- [x] Frigate API push support (`frigate_url`, `auto_push`)
- [x] Push to Frigate button entity
- [x] Frigate connection sensor (version, status)
- [x] Diagnostic sensors (discovery status, per-adapter info)
- [x] Improved error handling with user-friendly messages
- [x] HACS `hacs.json` metadata with zip_release
- [x] Comprehensive `README.md` with use cases and examples
- [x] GitHub Actions for HACS validation and code checks
- [x] Customer-friendly UI text throughout
- [x] Fast initialization with 5s delay + retry logic

#### Acceptance Criteria
- [x] HACS validation workflow configured
- [x] Config push to Frigate API implemented
- [x] README documents all features with examples
- [x] Handles edge cases (disabled entities, unavailable cameras)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.4.0.0 | 2026-01-17 | Milestone 4 complete - Push to Frigate, diagnostics, polish |
| 0.3.0.3 | 2026-01-17 | Reolink disabled entities fix, Refresh Cameras button |
| 0.3.0.2 | 2026-01-17 | Exclude unavailable cameras UI |
| 0.3.0.0 | 2026-01-17 | Milestone 3 complete - Entities & UI |
| 0.2.2.0 | 2026-01-17 | Milestone 2 complete - Camera discovery |

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
| `reolink` | Reolink cameras | Handles disabled entities |

---

## Development Workflow

```bash
# Local development
cd /Users/ojiudezue/Library/CloudStorage/OneDrive-Personal/2025/frigate-config-builder

# Validate syntax
python3 -m py_compile custom_components/frigate_config_builder/*.py
python3 -m py_compile custom_components/frigate_config_builder/discovery/*.py

# After changes, commit and push
git add .
git commit -m "Description of changes"
git push

# To test on MadroneHAOS:
# Copy custom_components to HA config, or use HACS custom repo
```

---

## Key Files

```
custom_components/frigate_config_builder/
├── __init__.py          # Integration setup, services
├── manifest.json        # Dependencies, version
├── const.py             # Constants and defaults
├── config_flow.py       # 5-step setup wizard + options flow
├── coordinator.py       # Data coordinator
├── generator.py         # YAML generation
├── output.py            # File writing, Frigate API push
├── button.py            # Generate, Push, Refresh buttons
├── sensor.py            # Status and diagnostic sensors
├── binary_sensor.py     # Config stale sensor
├── services.yaml        # Service definitions
├── strings.json         # UI text
├── translations/en.json # English translations
└── discovery/
    ├── coordinator.py   # Discovery orchestrator
    ├── base.py          # Abstract adapter
    ├── unifiprotect.py  # UniFi Protect adapter
    ├── amcrest.py       # Amcrest/Dahua adapter
    ├── reolink.py       # Reolink adapter
    └── manual.py        # Manual cameras
```
