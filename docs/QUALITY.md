# Frigate Config Builder - Quality Plan

## Testing Philosophy

1. **Validate against known-good output** - We have a working `frigate.yml` to compare against
2. **Test at boundaries** - Config flow steps, adapter discovery, YAML generation
3. **Mock HA internals** - Don't require live HA instance for unit tests
4. **Integration tests on real system** - Final validation on MadroneHAOS

---

## Test Categories

### 1. Unit Tests

#### 1.1 Generator Tests (`test_generator.py`)

| Test | Description | Input | Expected Output |
|------|-------------|-------|-----------------|
| `test_generate_mqtt_section` | MQTT config from HA | `mqtt_auto=True`, mock HA MQTT config | Valid `mqtt:` YAML block |
| `test_generate_mqtt_manual` | Manual MQTT config | host, port, user, pass | Valid `mqtt:` YAML block |
| `test_generate_detectors_coral` | Coral USB detector | `detector_type="edgetpu"`, `device="usb"` | Valid `detectors:` block |
| `test_generate_detectors_cpu` | CPU fallback | `detector_type="cpu"` | Valid `detectors:` block |
| `test_generate_hwaccel_vaapi` | Intel VAAPI | `hwaccel="vaapi"` | `preset-vaapi` in ffmpeg |
| `test_generate_hwaccel_cuda` | NVIDIA CUDA | `hwaccel="cuda"` | `preset-nvidia-h264` in ffmpeg |
| `test_generate_retention` | Retention settings | days for each type | Valid `record:` and `snapshots:` blocks |
| `test_generate_features_all_enabled` | All features on | all feature flags True | face_recognition, semantic_search, lpr, audio sections |
| `test_generate_features_minimal` | Minimal features | only audio_detection True | Only `audio:` section |
| `test_generate_camera_single` | Single camera entry | DiscoveredCamera object | Valid camera YAML with ffmpeg inputs |
| `test_generate_camera_dual_stream` | Separate detect/record | camera with both URLs | Two ffmpeg inputs with correct roles |
| `test_generate_camera_single_stream` | Same stream for both | camera with only record_url | One input with all roles |
| `test_generate_go2rtc_streams` | go2rtc section | list of cameras | Valid `go2rtc.streams:` block |
| `test_generate_camera_groups` | Camera groups | group dict | Valid `camera_groups:` block |
| `test_generate_full_config` | Complete config | full FrigateBuilderConfig | Valid complete YAML |
| `test_yaml_special_chars` | Password escaping | password with `@^!` chars | Properly escaped in RTSP URL |
| `test_yaml_valid_syntax` | YAML parses | generated config | `yaml.safe_load()` succeeds |

#### 1.2 Discovery Adapter Tests

##### UniFi Protect (`test_discovery_unifiprotect.py`)

| Test | Description | Mock Data | Expected |
|------|-------------|-----------|----------|
| `test_discover_cameras_basic` | Find all cameras | Mock camera entities | List of DiscoveredCamera |
| `test_discover_high_low_res` | Dual stream detection | Camera with _low_res sibling | Both URLs populated |
| `test_discover_package_camera` | G6 package camera | Entity with "package" in name | Separate camera entry |
| `test_discover_unavailable` | Unavailable camera | Entity with `state=unavailable` | `available=False` in result |
| `test_discover_no_rtsp` | Missing RTSP service | No expose-camera-stream-source | Graceful error, empty list |
| `test_extract_camera_name` | Name normalization | "Front Door - Aerial" | `front_door_aerial` |
| `test_detect_resolution` | Resolution from attributes | Entity attributes | Correct width/height |

##### Amcrest (`test_discovery_amcrest.py`)

| Test | Description | Mock Data | Expected |
|------|-------------|-----------|----------|
| `test_discover_from_config_entry` | Find Amcrest cameras | Mock config entry | List of DiscoveredCamera |
| `test_build_rtsp_url` | URL construction | host, user, pass, channel | Valid RTSP URL |
| `test_channel_0_vs_1` | Channel selection | Different camera models | Correct channel in URL |
| `test_credential_override` | Override password | credential_overrides dict | Override used, not config entry |
| `test_subtype_main_sub` | Main vs sub stream | - | subtype=0 for record, subtype=1 for detect |

##### Reolink (`test_discovery_reolink.py`)

| Test | Description | Mock Data | Expected |
|------|-------------|-----------|----------|
| `test_discover_from_config_entry` | Find Reolink cameras | Mock config entry | List of DiscoveredCamera |
| `test_build_rtsp_url` | URL construction | host, user, pass | Valid RTSP URL |
| `test_main_sub_stream` | Stream URLs | - | `_main` for record, `_sub` for detect |
| `test_http_flv_stream` | FLV URL for go2rtc | - | HTTP FLV URL in go2rtc_url |

##### Manual (`test_discovery_manual.py`)

| Test | Description | Mock Data | Expected |
|------|-------------|-----------|----------|
| `test_parse_manual_camera` | Parse manual entry | Dict with name, urls | DiscoveredCamera object |
| `test_validate_rtsp_url` | URL validation | Various URL formats | Accept valid, reject invalid |

#### 1.3 Config Flow Tests (`test_config_flow.py`)

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| `test_step_connection` | Step 1 completes | output_path | Advance to step 2 |
| `test_step_hardware` | Step 2 completes | detector, hwaccel | Advance to step 3 |
| `test_step_mqtt_auto` | Step 3 auto MQTT | mqtt_auto=True | Detect HA MQTT, advance |
| `test_step_mqtt_manual` | Step 3 manual MQTT | mqtt_auto=False, credentials | Advance to step 4 |
| `test_step_features` | Step 4 completes | feature flags | Advance to step 5 |
| `test_step_retention` | Step 5 completes | retention days | Create entry |
| `test_flow_creates_entry` | Full flow | All steps | Config entry created |
| `test_invalid_output_path` | Bad path | `/root/nope.yml` | Error shown |
| `test_invalid_frigate_url` | Bad URL | `not-a-url` | Error shown |

#### 1.4 Options Flow Tests (`test_options_flow.py`)

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| `test_show_discovered_cameras` | Display cameras | Mock discovered list | All cameras shown |
| `test_select_cameras` | Toggle selection | Check/uncheck cameras | `selected_cameras` updated |
| `test_cameras_grouped_by_source` | Grouping | Mixed sources | Grouped display |
| `test_manual_camera_add` | Add manual camera | Camera details | Added to manual_cameras |
| `test_credential_override` | Add override | Host + credentials | Added to overrides |

#### 1.5 Entity Tests

##### Button (`test_button.py`)

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| `test_generate_button_press` | Trigger generation | Button press | Generator called, file written |
| `test_generate_button_icon` | Correct icon | - | `mdi:file-cog` or similar |

##### Sensors (`test_sensor.py`)

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| `test_cameras_selected_count` | Count selected | 24 selected | State = "24" |
| `test_cameras_selected_attribute` | Camera list | 24 selected | Attribute has names |
| `test_last_generated_timestamp` | Timestamp | After generation | ISO timestamp |
| `test_last_generated_attributes` | Generation details | After generation | camera_count, duration |

##### Binary Sensor (`test_binary_sensor.py`)

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| `test_config_stale_new_camera` | New camera detected | New entity appears | State = ON |
| `test_config_stale_camera_removed` | Camera removed | Entity removed | State = ON |
| `test_config_stale_after_generate` | Fresh config | After generation | State = OFF |
| `test_config_stale_camera_unavailable` | Camera goes offline | Entity unavailable | State unchanged (not stale) |

---

### 2. Integration Tests (on MadroneHAOS)

These require the actual Home Assistant instance.

| Test | Description | Steps | Expected |
|------|-------------|-------|----------|
| `test_install_via_hacs` | HACS installation | Add custom repo, install | Integration available |
| `test_config_flow_real` | Real config flow | Complete all steps | Entry created |
| `test_discover_unifi_real` | Real UniFi discovery | Run discovery | All 20 cameras found |
| `test_discover_amcrest_real` | Real Amcrest discovery | Run discovery | Both Amcrest cameras found |
| `test_discover_reolink_real` | Real Reolink discovery | Run discovery | Reolink camera found |
| `test_generate_matches_reference` | Compare output | Generate config | Matches `/mnt/user-data/outputs/frigate.yml` structure |
| `test_frigate_accepts_config` | Frigate validation | Copy to Frigate, restart | Frigate starts without errors |
| `test_all_cameras_stream` | Streams work | Check each camera | All cameras streaming |

---

### 3. Validation Tests

#### 3.1 YAML Validation

```python
def test_yaml_valid():
    """Generated YAML parses without errors."""
    config = generator.generate()
    parsed = yaml.safe_load(config)
    assert parsed is not None
    assert "cameras" in parsed
    assert "mqtt" in parsed
```

#### 3.2 Frigate Schema Validation

```python
def test_frigate_schema():
    """Generated config matches Frigate JSON schema."""
    config = generator.generate()
    parsed = yaml.safe_load(config)
    # Frigate publishes JSON schema
    schema = load_frigate_schema("0.14")
    validate(parsed, schema)
```

#### 3.3 RTSP URL Validation

```python
def test_rtsp_urls_valid():
    """All RTSP URLs are well-formed."""
    cameras = discovery.discover_all()
    for cam in cameras:
        assert cam.record_url.startswith("rtsp://") or cam.record_url.startswith("rtsps://")
        parsed = urlparse(cam.record_url)
        assert parsed.hostname is not None
        assert parsed.port is not None or parsed.scheme == "rtsp"
```

---

### 4. Reference Comparison Tests

These compare generated output against the known-good `frigate.yml`.

```python
def test_camera_count_matches():
    """Same number of cameras as reference."""
    generated = generator.generate()
    reference = load_reference_config()
    
    gen_cameras = list(yaml.safe_load(generated)["cameras"].keys())
    ref_cameras = list(reference["cameras"].keys())
    
    assert len(gen_cameras) == len(ref_cameras)

def test_camera_names_match():
    """Camera names match reference."""
    generated = generator.generate()
    reference = load_reference_config()
    
    gen_cameras = set(yaml.safe_load(generated)["cameras"].keys())
    ref_cameras = set(reference["cameras"].keys())
    
    assert gen_cameras == ref_cameras

def test_rtsp_urls_match():
    """RTSP URLs match reference."""
    generated = generator.generate()
    reference = load_reference_config()
    
    gen_parsed = yaml.safe_load(generated)
    for cam_name, cam_config in reference["cameras"].items():
        gen_cam = gen_parsed["cameras"][cam_name]
        ref_url = cam_config["ffmpeg"]["inputs"][0]["path"]
        gen_url = gen_cam["ffmpeg"]["inputs"][0]["path"]
        assert gen_url == ref_url, f"URL mismatch for {cam_name}"
```

---

## Test Data

### Mock DiscoveredCamera Objects

```python
MOCK_UNIFI_CAMERA = DiscoveredCamera(
    id="unifi_garage_a",
    name="garage_a",
    friendly_name="Garage A",
    source="unifiprotect",
    record_url="rtsps://192.168.15.173:7441/LimzvgUEin7vTGsf?enableSrtp",
    detect_url="rtsps://192.168.15.173:7441/0tE6FgeTPUfbWNqj?enableSrtp",
    go2rtc_url="rtspx://192.168.15.173:7441/LimzvgUEin7vTGsf",
    width=640,
    height=360,
    area="Garage",
    available=True,
)

MOCK_AMCREST_CAMERA = DiscoveredCamera(
    id="amcrest_192_168_15_96",
    name="armcrest",
    friendly_name="ArmCrest",
    source="amcrest",
    record_url="rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=0",
    detect_url="rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=1",
    go2rtc_url="rtsp://Okosisi:Verycool9277%40%5E@192.168.15.96/cam/realmonitor?channel=1&subtype=0",
    width=704,
    height=480,
    available=True,
)

MOCK_REOLINK_CAMERA = DiscoveredCamera(
    id="reolink_study_porch",
    name="reolink_study_b_porch_ptz",
    friendly_name="Study B Porch PTZ",
    source="reolink",
    record_url="rtsp://admin:Verycool9277@192.168.12.170:554/h264Preview_01_main",
    detect_url="rtsp://admin:Verycool9277@192.168.12.170:554/h264Preview_01_sub",
    go2rtc_url="ffmpeg:http://192.168.12.170/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=Verycool9277",
    width=640,
    height=480,
    available=True,
)
```

### Mock Config Entry

```python
MOCK_AMCREST_CONFIG_ENTRY = {
    "entry_id": "amcrest_1",
    "domain": "amcrest",
    "title": "ArmCrest",
    "data": {
        "host": "192.168.15.96",
        "username": "Okosisi",
        "password": "Verycool9277@^",
        "port": 80,
    },
}
```

---

## Test File Structure

```
tests/
├── conftest.py              # Pytest fixtures, mock HA
├── test_generator.py        # Generator unit tests
├── test_config_flow.py      # Config flow tests
├── test_options_flow.py     # Options flow tests
├── test_button.py           # Button entity tests
├── test_sensor.py           # Sensor tests
├── test_binary_sensor.py    # Binary sensor tests
├── discovery/
│   ├── test_coordinator.py  # Discovery coordinator
│   ├── test_unifiprotect.py # UniFi adapter
│   ├── test_amcrest.py      # Amcrest adapter
│   ├── test_reolink.py      # Reolink adapter
│   └── test_manual.py       # Manual adapter
├── integration/
│   └── test_full_flow.py    # End-to-end on real HA
└── validation/
    ├── test_yaml.py         # YAML validity
    ├── test_schema.py       # Frigate schema
    └── test_reference.py    # Compare to reference
```

---

## Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| `generator.py` | 90%+ |
| `discovery/*.py` | 85%+ |
| `config_flow.py` | 80%+ |
| `options_flow.py` | 80%+ |
| Entities | 75%+ |
| **Overall** | **80%+** |

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-asyncio
          pip install homeassistant  # For type hints
      - name: Run tests
        run: pytest --cov=custom_components/frigate_config_builder --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
```

---

## Manual Testing Checklist

### Pre-Release Checklist

- [ ] Fresh install on clean HA instance
- [ ] Config flow completes without errors
- [ ] All cameras discovered correctly
- [ ] Generated YAML matches expected structure
- [ ] Frigate accepts and starts with config
- [ ] All camera streams working in Frigate
- [ ] Generate button works
- [ ] Sensors show correct values
- [ ] Stale sensor triggers on new camera
- [ ] Options flow camera selection works
- [ ] Manual camera addition works
- [ ] HACS validation passes
