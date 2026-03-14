#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a flower blocktype JSON and append a worldgen patch entry "
            "using the pnwplants Digitalis pattern."
        )
    )
    parser.add_argument(
        "slug",
        help="Species slug used in folder/file naming (example: trillium-ovatum).",
    )
    parser.add_argument(
        "--shape",
        default=None,
        help=(
            "Shape JSON file name inside the species shape directory. "
            "If omitted, script uses the only .json file found there."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite blocktypes/plant/<slug>.json if it already exists.",
    )
    parser.add_argument("--min-temp", type=float, default=30.0)
    parser.add_argument("--min-rain", type=float, default=0.75)
    parser.add_argument("--min-forest", type=float, default=0.9)
    parser.add_argument("--chance", type=float, default=1.25)
    parser.add_argument("--quantity-avg", type=int, default=1)
    parser.add_argument("--quantity-var", type=int, default=0)
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def discover_shape_file(shape_dir: Path, shape_name: str | None) -> Path:
    if shape_name:
        shape_path = shape_dir / shape_name
        if not shape_path.exists():
            fail(f"Shape file not found: {shape_path}")
        return shape_path

    candidates = sorted(shape_dir.glob("*.json"))
    if not candidates:
        fail(f"No shape JSON files found in: {shape_dir}")
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        fail(f"Multiple shape JSON files found. Use --shape. Found: {names}")
    return candidates[0]


def discover_texture_file(texture_dir: Path, slug: str) -> Path:
    preferred = texture_dir / f"{slug}.png"
    if preferred.exists():
        return preferred

    candidates = sorted(texture_dir.glob("*.png"))
    if not candidates:
        fail(f"No texture PNG files found in: {texture_dir}")
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        fail(
            "Could not determine a single texture file. "
            f"Expected {slug}.png or exactly one PNG. Found: {names}"
        )
    return candidates[0]


def build_blocktype(slug: str, texture_rel: str, shape_rel: str) -> dict:
    return {
        "code": f"flower-{slug}",
        "class": "BlockPlant",
        "textures": {
            slug: {"base": texture_rel},
            "plant2a": {"base": texture_rel},
            "plant2b": {"base": texture_rel},
            "plant2astem": {"base": texture_rel},
            "plant2bstem": {"base": texture_rel},
        },
        "behaviors": [{"name": "DropNotSnowCovered"}],
        "attributes": {"butterflyFeed": True, "beeFeed": True},
        "creativeinventory": {"general": ["*"], "flora": ["*"]},
        "renderpass": "BlendNoCull",
        "drawtype": "json",
        "shape": {"base": shape_rel},
        "randomDrawOffset": False,
        "randomizeRotations": True,
        "randomizeAxes": "xz",
        "sideopaque": {"all": False},
        "sidesolid": {"all": True},
        "blockmaterial": "Plant",
        "replaceable": 3000,
        "lightAbsorption": 0,
        "resistance": 0.5,
        "collisionbox": None,
        "sounds": {
            "place": "game:block/plant",
            "break": "game:block/plant",
            "hit": "game:block/plant",
            "inside": "game:walk/inside/leafy/bushrustle*",
        },
        "rainPermeable": False,
        "materialDensity": 200,
        "combustibleProps": {"burnTemperature": 600, "burnDuration": 5},
        "frostable": True,
    }


def append_worldgen_entry(
    worldgen_path: Path,
    block_code: str,
    min_temp: float,
    min_rain: float,
    min_forest: float,
    chance: float,
    quantity_avg: int,
    quantity_var: int,
) -> bool:
    if worldgen_path.exists():
        worldgen = load_json(worldgen_path)
        if not isinstance(worldgen, list):
            fail(f"Expected a JSON array in {worldgen_path}")
    else:
        worldgen = []

    full_code = f"pnwplants:{block_code}"
    already_present = any(
        isinstance(entry, dict)
        and isinstance(entry.get("blockCodes"), list)
        and full_code in entry["blockCodes"]
        for entry in worldgen
    )

    if already_present:
        return False

    worldgen.append(
        {
            "blockCodes": [full_code],
            "minTemp": min_temp,
            "minRain": min_rain,
            "minForest": min_forest,
            "quantity": {"avg": quantity_avg, "var": quantity_var},
            "chance": chance,
        }
    )
    save_json(worldgen_path, worldgen)
    return True


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    shape_dir = repo_root / "assets/pnwplants/shapes/block/plant/flower" / args.slug
    texture_dir = repo_root / "assets/pnwplants/textures/blocks/plant/flower" / args.slug
    blocktype_path = repo_root / "assets/pnwplants/blocktypes/plant" / f"{args.slug}.json"
    worldgen_path = repo_root / "worldgen/blockpatches/flower.json"

    if not shape_dir.exists():
        fail(f"Shape directory does not exist: {shape_dir}")
    if not texture_dir.exists():
        fail(f"Texture directory does not exist: {texture_dir}")

    shape_file = discover_shape_file(shape_dir, args.shape)
    texture_file = discover_texture_file(texture_dir, args.slug)

    if blocktype_path.exists() and not args.overwrite:
        fail(
            f"Blocktype already exists: {blocktype_path}. "
            "Use --overwrite to replace it."
        )

    texture_rel = f"blocks/plant/flower/{args.slug}/{texture_file.name}"
    shape_rel = f"pnwplants:shapes/block/plant/flower/{args.slug}/{shape_file.name}"
    block_data = build_blocktype(args.slug, texture_rel, shape_rel)

    blocktype_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(blocktype_path, block_data)

    appended = append_worldgen_entry(
        worldgen_path=worldgen_path,
        block_code=block_data["code"],
        min_temp=args.min_temp,
        min_rain=args.min_rain,
        min_forest=args.min_forest,
        chance=args.chance,
        quantity_avg=args.quantity_avg,
        quantity_var=args.quantity_var,
    )

    print(f"Created blocktype: {blocktype_path}")
    if appended:
        print(f"Appended worldgen entry to: {worldgen_path}")
    else:
        print("Worldgen already had this block code. No entry appended.")


if __name__ == "__main__":
    main()