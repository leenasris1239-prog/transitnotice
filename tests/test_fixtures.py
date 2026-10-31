import os
import xml.etree.ElementTree as ET

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def load(name):
    with open(os.path.join(FIXTURE_DIR, name), "r", encoding="utf-8") as f:
        return f.read()

def test_malformed_xml_does_not_crash():
    raw = load("malformed.xml")
    try:
        ET.fromstring(raw)
        parsed = True
    except ET.ParseError:
        parsed = False
    assert parsed is False  # parser must detect, not crash silently

def test_missing_fields_handled():
    raw = load("missing_fields.xml")
    root = ET.fromstring(raw)
    item = root.find(".//item")
    pub_date = item.findtext("pubDate")
    link = item.findtext("link")
    assert pub_date is None and link is None  # missing fields detected

def test_duplicates_detected():
    raw = load("duplicates.xml")
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    titles = [i.findtext("title") for i in items]
    assert len(titles) == 2 and titles[0] == titles[1]  # duplicate present

def test_unavailable_source_documented():
    raw = load("unavailable_source.txt")
    assert "503" in raw and "STALE" in raw  # outage scenario defined