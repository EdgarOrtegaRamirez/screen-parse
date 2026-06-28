"""Shared fixtures for screen-parse tests."""

from __future__ import annotations

import pathlib
import textwrap

import pytest


SAMPLE_ACCESSIBILITY_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <hierarchy rotation="0">
      <node class="android.widget.FrameLayout"
            package="com.example.app"
            visible-to-user="true"
            enabled="true"
            bounds="[0,0][1080,2340]">
        <node class="android.widget.Toolbar"
              content-desc="Navigation drawer"
              visible-to-user="true"
              enabled="true"
              bounds="[0,0][1080,168]"/>
        <node class="android.widget.TextView"
              text="Welcome to App"
              visible-to-user="true"
              enabled="true"
              bounds="[100,200][500,280]"/>
        <node class="android.widget.Button"
              text="Login"
              visible-to-user="true"
              enabled="true"
              bounds="[100,400][400,500]"/>
        <node class="android.widget.EditText"
              text=""
              content-desc="Email input"
              visible-to-user="true"
              enabled="true"
              bounds="[100,600][500,700]"/>
        <node class="android.widget.ImageView"
              text=""
              content-desc="App logo"
              visible-to-user="true"
              enabled="true"
              bounds="[300,100][700,200]"/>
      </node>
    </hierarchy>
""")

HIDDEN_ELEMENT_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <hierarchy rotation="0">
      <node class="android.widget.TextView"
            text="Visible Text"
            visible-to-user="true"
            bounds="[100,100][500,200]"/>
      <node class="android.widget.Button"
            text="Hidden Button"
            visible-to-user="false"
            bounds="[100,300][500,400]"/>
    </hierarchy>
""")

EMPTY_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <hierarchy rotation="0"/>
""")


@pytest.fixture()
def temp_xml_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write the sample accessibility XML to a temp file."""
    xml_file = tmp_path / "accessibility.xml"
    xml_file.write_text(SAMPLE_ACCESSIBILITY_XML, encoding="utf-8")
    return xml_file


@pytest.fixture()
def temp_hidden_xml_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write XML with hidden elements to a temp file."""
    xml_file = tmp_path / "hidden.xml"
    xml_file.write_text(HIDDEN_ELEMENT_XML, encoding="utf-8")
    return xml_file


@pytest.fixture()
def temp_empty_xml_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write empty XML to a temp file."""
    xml_file = tmp_path / "empty.xml"
    xml_file.write_text(EMPTY_XML, encoding="utf-8")
    return xml_file
