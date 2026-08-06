import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from protocol import parse_raw_command


def test_hub_sniff_short_form_expands_to_targeted_command():
    cmd = parse_raw_command("sniff:on")

    assert cmd.action == "sniff"
    assert cmd.target == "hub"
    assert cmd.parameter == "on"
    assert cmd.validate("hub") is True
    assert cmd.to_string() == "sniff:hub:on\n"


def test_hub_sniff_off_short_form_expands_to_targeted_command():
    cmd = parse_raw_command("sniff:off")

    assert cmd.action == "sniff"
    assert cmd.target == "hub"
    assert cmd.parameter == "off"
    assert cmd.validate("hub") is True
    assert cmd.to_string() == "sniff:hub:off\n"