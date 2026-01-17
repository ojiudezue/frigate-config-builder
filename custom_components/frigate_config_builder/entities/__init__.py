"""Frigate Config Builder entities.

Version: 0.3.0.0
Date: 2026-01-17

Exports entity platforms for Home Assistant.
"""
from __future__ import annotations

from .binary_sensor import FrigateConfigBuilderConfigStaleSensor
from .button import FrigateConfigBuilderGenerateButton
from .sensor import (
    FrigateConfigBuilderCamerasDiscoveredSensor,
    FrigateConfigBuilderCamerasSelectedSensor,
    FrigateConfigBuilderLastGeneratedSensor,
)

__all__ = [
    "FrigateConfigBuilderGenerateButton",
    "FrigateConfigBuilderCamerasSelectedSensor",
    "FrigateConfigBuilderCamerasDiscoveredSensor",
    "FrigateConfigBuilderLastGeneratedSensor",
    "FrigateConfigBuilderConfigStaleSensor",
]
