import os
import importlib.util
from pathlib import Path

# Allow Pygame to initialize without a physical display in CI.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "game final.py"

spec = importlib.util.spec_from_file_location("visionplay_app", SOURCE_FILE)
visionplay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visionplay)


def test_sx_scales_horizontal_coordinates():
    assert visionplay.sx(100) == 128


def test_sy_scales_vertical_coordinates():
    assert visionplay.sy(100) == 120


def test_smin_uses_smaller_scale():
    assert visionplay.smin(100) == 120


def test_display_sx_scales_target_display_width():
    assert visionplay.display_sx(1920) == 1280


def test_display_sy_scales_target_display_height():
    assert visionplay.display_sy(1080) == 720
