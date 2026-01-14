#!/usr/bin/env python3
"""
Generate Frigate camera configuration from Home Assistant UniFi Protect integration.

Run this script from the HA Terminal/SSH add-on:
    python3 generate_frigate_config.py

Requirements:
    - expose-camera-stream-source HACS integration installed
    - UniFi Protect integration configured with RTSP enabled
    - Script must run inside HA environment (uses SUPERVISOR_TOKEN)
"""

import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Configuration
NVR_IP = "192.168.15.173"  # Updated NVR IP
HA_API_BASE = "http://supervisor/core/api"

def get_supervisor_token():
    """Get the supervisor token from environment."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        print("ERROR: SUPERVISOR_TOKEN not found. Run this from HA Terminal/SSH add-on.")
        sys.exit(1)
    return token

def ha_api_request(endpoint, token):
    """Make a request to the HA API."""
    url = f"{HA_API_BASE}{endpoint}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"HTTP Error {e.code} for {endpoint}: {e.reason}")
        return None

def get_stream_source(entity_id, token):
    """Get the RTSP stream source URL for a camera entity."""
    endpoint = f"/camera_stream_source/{entity_id}"
    url = f"{HA_API_BASE}{endpoint}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        with urlopen(req, timeout=30) as response:
            return response.read().decode().strip().strip('"')
    except HTTPError as e:
        if e.code == 404:
            return None
        print(f"  Warning: Could not get stream for {entity_id}: {e}")
        return None

def get_all_camera_entities(token):
    """Get all camera entities from HA."""
    states = ha_api_request("/states", token)
    if not states:
        return []
    
    cameras = []
    for entity in states:
        entity_id = entity.get("entity_id", "")
        if entity_id.startswith("camera."):
            cameras.append(entity)
    return cameras

def get_unifi_protect_cameras(token):
    """Filter and organize UniFi Protect cameras."""
    all_cameras = get_all_camera_entities(token)
    
    cameras = {}
    
    for cam in all_cameras:
        entity_id = cam["entity_id"]
        friendly_name = cam.get("attributes", {}).get("friendly_name", "")
        state = cam.get("state", "")
        attribution = cam.get("attributes", {}).get("attribution", "")
        
        if "UniFi Protect" not in attribution:
            continue
        
        if state == "unavailable":
            print(f"  Skipping unavailable: {entity_id}")
            continue
        
        if "_insecure" in entity_id:
            continue
        
        match = re.match(r"camera\.(.+?)_(high|medium|low)_resolution_channel$", entity_id)
        if match:
            cam_name = match.group(1)
            resolution = match.group(2)
        elif entity_id.endswith("_package_camera"):
            cam_name = entity_id.replace("camera.", "").replace("_package_camera", "")
            resolution = "package"
        else:
            continue
        
        if cam_name not in cameras:
            cameras[cam_name] = {"high": None, "medium": None, "low": None, "package": None}
        
        cameras[cam_name][resolution] = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "state": state,
            "attributes": cam.get("attributes", {})
        }
    
    return cameras

def convert_url_for_frigate(url):
    """Convert HA stream URL to Frigate format."""
    if url and not url.endswith("?enableSrtp"):
        return f"{url}?enableSrtp"
    return url

def get_detect_dimensions(attributes, resolution):
    """Get detect dimensions based on camera attributes."""
    width = attributes.get("width", 640)
    height = attributes.get("height", 360)
    
    if width > 1280:
        ratio = height / width
        width = 640
        height = int(640 * ratio)
    
    return width, height

def generate_frigate_cameras_yaml(cameras, token):
    """Generate the cameras section of frigate.yml."""
    
    yaml_lines = []
    
    for cam_name, resolutions in sorted(cameras.items()):
        high = resolutions.get("high")
        low = resolutions.get("low")
        package = resolutions.get("package")
        
        if not high:
            print(f"  Skipping {cam_name}: no high-res stream")
            continue
        
        high_url = None
        low_url = None
        pkg_url = None
        
        if high:
            high_url = get_stream_source(high["entity_id"], token)
            print(f"  {cam_name} high: {high_url}")
        if low:
            low_url = get_stream_source(low["entity_id"], token)
            print(f"  {cam_name} low: {low_url}")
        if package:
            pkg_url = get_stream_source(package["entity_id"], token)
            print(f"  {cam_name} package: {pkg_url}")
        
        if not high_url:
            print(f"  Skipping {cam_name}: could not get stream URL")
            continue
        
        high_url = convert_url_for_frigate(high_url)
        if low_url:
            low_url = convert_url_for_frigate(low_url)
        if pkg_url:
            pkg_url = convert_url_for_frigate(pkg_url)
        
        if low:
            detect_width, detect_height = get_detect_dimensions(low["attributes"], "low")
        else:
            detect_width, detect_height = 640, 360
        
        yaml_lines.append(f"  {cam_name}: # <------ {high.get('friendly_name', cam_name).replace(' High resolution channel', '')}")
        yaml_lines.append(f"    enabled: true")
        yaml_lines.append(f"    ffmpeg:")
        yaml_lines.append(f"      inputs:")
        yaml_lines.append(f"        - path: {high_url} # <----- The stream you want to use for recording")
        yaml_lines.append(f"          roles:")
        yaml_lines.append(f"            - record")
        yaml_lines.append(f"            - audio")
        
        detect_url = low_url if low_url else high_url
        yaml_lines.append(f"        - path: {detect_url} # <----- The stream you want to use for detection")
        yaml_lines.append(f"          roles:")
        yaml_lines.append(f"            - detect")
        yaml_lines.append(f"      hwaccel_args: preset-vaapi")
        yaml_lines.append(f"    detect:")
        yaml_lines.append(f"      enabled: true")
        yaml_lines.append(f"      width: {detect_width}")
        yaml_lines.append(f"      height: {detect_height}")
        yaml_lines.append("")
        
        if pkg_url:
            pkg_name = f"{cam_name}_package"
            yaml_lines.append(f"  {pkg_name}: # <------ {cam_name} Package Camera")
            yaml_lines.append(f"    enabled: true")
            yaml_lines.append(f"    ffmpeg:")
            yaml_lines.append(f"      inputs:")
            yaml_lines.append(f"        - path: {pkg_url}")
            yaml_lines.append(f"          roles:")
            yaml_lines.append(f"            - record")
            yaml_lines.append(f"            - audio")
            yaml_lines.append(f"            - detect")
            yaml_lines.append(f"      hwaccel_args: preset-vaapi")
            yaml_lines.append(f"    detect:")
            yaml_lines.append(f"      enabled: true")
            yaml_lines.append(f"      width: 400")
            yaml_lines.append(f"      height: 300")
            yaml_lines.append("")
    
    return "\n".join(yaml_lines)

def generate_go2rtc_streams_yaml(cameras, token):
    """Generate the go2rtc streams section."""
    
    yaml_lines = []
    
    for cam_name, resolutions in sorted(cameras.items()):
        high = resolutions.get("high")
        package = resolutions.get("package")
        
        if not high:
            continue
        
        high_url = get_stream_source(high["entity_id"], token)
        if high_url:
            go2rtc_url = high_url.replace("rtsps://", "rtspx://")
            yaml_lines.append(f"    {cam_name}:")
            yaml_lines.append(f"      - {go2rtc_url}")
        
        if package:
            pkg_url = get_stream_source(package["entity_id"], token)
            if pkg_url:
                go2rtc_url = pkg_url.replace("rtsps://", "rtspx://")
                yaml_lines.append(f"    {cam_name}_package:")
                yaml_lines.append(f"      - {go2rtc_url}")
    
    return "\n".join(yaml_lines)

def main():
    print("=" * 60)
    print("Frigate Config Generator for UniFi Protect")
    print("=" * 60)
    print()
    
    token = get_supervisor_token()
    print(f"Using NVR IP: {NVR_IP}")
    print()
    
    print("Discovering UniFi Protect cameras...")
    cameras = get_unifi_protect_cameras(token)
    print(f"Found {len(cameras)} UniFi Protect cameras")
    print()
    
    for name, resolutions in sorted(cameras.items()):
        available = [r for r, data in resolutions.items() if data]
        print(f"  {name}: {', '.join(available)}")
    print()
    
    print("Fetching stream URLs...")
    cameras_yaml = generate_frigate_cameras_yaml(cameras, token)
    go2rtc_yaml = generate_go2rtc_streams_yaml(cameras, token)
    
    print()
    print("=" * 60)
    print("CAMERAS SECTION (paste into frigate.yml under 'cameras:')")
    print("=" * 60)
    print()
    print(cameras_yaml)
    
    print()
    print("=" * 60)
    print("GO2RTC STREAMS SECTION (paste into frigate.yml under 'go2rtc: streams:')")
    print("=" * 60)
    print()
    print(go2rtc_yaml)
    
    with open("/tmp/frigate_cameras.yml", "w") as f:
        f.write("cameras:\n")
        f.write(cameras_yaml)
    
    with open("/tmp/frigate_go2rtc.yml", "w") as f:
        f.write("go2rtc:\n  streams:\n")
        f.write(go2rtc_yaml)
    
    print()
    print("=" * 60)
    print("Files saved to:")
    print("  /tmp/frigate_cameras.yml")
    print("  /tmp/frigate_go2rtc.yml")
    print("=" * 60)

if __name__ == "__main__":
    main()
