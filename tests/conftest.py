import json
from pathlib import Path

import pytest

from custom_components.creality_cloud.api import parse_device

DEVICE = json.loads((Path(__file__).parent / "device.json").read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def device():
    return json.loads(json.dumps(DEVICE))


@pytest.fixture
def printers(device):
    p = parse_device(device)
    return {p.id: p}
