import os
import json
from pathlib import Path

current_dir = Path(__file__).parent

failed = []
files = os.listdir(current_dir / "_internal" / "products")
for file in files:
    file_path = current_dir / "_internal" / "products" / file
    if file_path.suffix != ".json":
        continue

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load {file}: {e}")
        failed.append((file, str(e)))
        continue

    if "ASINObjects" in data:
        print(f"{file_path.stem} already processed, skipping")
        continue

    try:
        frontside = data.pop("Frontside")
        backside = data.pop("Backside")
        asins = data["ASINs"]
    except KeyError as e:
        if str(e) == "'ASINs'":
            print(f"{file} has very old format, skipping")
        elif str(e) in ("'Frontside'", "'Backside'"):
            print(f"{file} already processed, skipping")
        else:
            print(f"Missing key in {file}: {e}")
            failed.append((file, f"Missing key: {e}"))
        continue

    try:
        new_design = {}
        for asin in asins:
            asin_objects = {
                "Frontside": frontside,
                "Backside": backside
            }
            new_design[asin[0]] = asin_objects
    except Exception as e:
        print(f"Failed to restructure {file}: {e}")
        failed.append((file, str(e)))
        continue

    try:
        data["ASINObjects"] = new_design
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Restructured {file} successfully")
    except Exception as e:
        print(f"Failed to write {file}: {e}")
        failed.append((file, str(e)))
        continue

if len(failed) == 0:
    print("\nSucessfully processed all files!")
else:
    print("\nFailed files:")
    for file, reason in failed:
        print(f"{file}: {reason}")