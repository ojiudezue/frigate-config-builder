#!/bin/bash
# Test runner for Frigate Config Builder
# Version: 0.4.0.5
# Date: 2026-01-18

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "Frigate Config Builder Test Suite"
echo "==================================="
echo ""

# Check for pytest
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Install with: pip install pytest pytest-asyncio pytest-cov pyyaml"
    exit 1
fi

# Install test dependencies if needed
if [ "$1" == "--install" ]; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
    echo ""
fi

# Run standalone tests (no HA dependencies)
echo "Running standalone tests (no HA dependencies)..."
echo "------------------------------------------------"
pytest tests/test_standalone.py tests/validation/ -v --tb=short

echo ""
echo "==================================="
echo "Standalone tests completed!"
echo "==================================="

# Check if homeassistant is available for full tests
if python3 -c "import homeassistant" 2>/dev/null; then
    echo ""
    echo "Home Assistant package detected. Running full test suite..."
    echo "------------------------------------------------------------"
    pytest tests/ -v --tb=short --ignore=tests/test_standalone.py --ignore=tests/validation/
    
    echo ""
    echo "==================================="
    echo "Full test suite completed!"
    echo "==================================="
else
    echo ""
    echo "Note: Home Assistant package not installed."
    echo "To run full integration tests, install homeassistant:"
    echo "  pip install homeassistant"
    echo ""
fi

# Run with coverage if requested
if [ "$1" == "--coverage" ]; then
    echo ""
    echo "Running with coverage..."
    pytest tests/ --cov=custom_components/frigate_config_builder --cov-report=html --cov-report=term-missing
    echo ""
    echo "Coverage report generated in htmlcov/"
fi
