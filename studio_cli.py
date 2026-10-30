#!/usr/bin/env python3
"""
Vector Difference Studio CLI
Allows coding agents (Antigravity, Claude Code, Cursor, Devin, etc.)
and terminal users to programmatically inspect and control the Vector Difference Studio.
"""

import sys
import argparse
import requests
import json

SERVER_URL = "http://localhost:8080"

def get_state():
    try:
        r = requests.get(f"{SERVER_URL}/api/state", timeout=3)
        return r.json()
    except Exception as e:
        print(f"Error connecting to Studio Server at {SERVER_URL}: {e}")
        return None

def get_diffs():
    try:
        r = requests.get(f"{SERVER_URL}/api/diffs", timeout=3)
        return r.json()
    except Exception as e:
        print(f"Error fetching diffs: {e}")
        return None

def send_action(action, params=None, sync=True):
    payload = {
        "action": action,
        "params": params or {},
        "sync": sync
    }
    try:
        r = requests.post(f"{SERVER_URL}/api/action", json=payload, timeout=6)
        return r.json()
    except Exception as e:
        print(f"Error dispatching action '{action}': {e}")
        return None

def load_file(file_path):
    try:
        r = requests.post(f"{SERVER_URL}/api/load-file", json={"filePath": file_path}, timeout=5)
        return r.json()
    except Exception as e:
        print(f"Error loading file '{file_path}': {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Vector Difference Studio - Agent CLI Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available agent commands")

    # Command: state
    subparsers.add_parser("state", help="Get current studio & artboard state")

    # Command: diffs
    subparsers.add_parser("diffs", help="Get list of active differences")

    # Command: load
    load_p = subparsers.add_parser("load", help="Load an SVG file from disk")
    load_p.add_argument("file_path", help="Path to .svg file")

    # Command: erase (Object Erase)
    erase_p = subparsers.add_parser("erase", help="Erase/vanish an object or accessory cleanly from the puzzle")
    erase_p.add_argument("--x", type=float, help="Coordinate X touching the object (SVG space)")
    erase_p.add_argument("--y", type=float, help="Coordinate Y touching the object (SVG space)")
    erase_p.add_argument("--index", type=int, help="Optional index of the path in SVG DOM")

    # Command: pull
    pull_p = subparsers.add_parser("pull", help="Perform linked Bézier point pull on outline + colors")
    pull_p.add_argument("--x", type=float, required=True, help="Anchor X coordinate (SVG space)")
    pull_p.add_argument("--y", type=float, required=True, help="Anchor Y coordinate (SVG space)")
    pull_p.add_argument("--dx", type=float, required=True, help="Displacement shift X")
    pull_p.add_argument("--dy", type=float, required=True, help="Displacement shift Y")
    pull_p.add_argument("--radius", type=float, default=32, help="Influence radius in pixels (default: 32)")
    pull_p.add_argument("--strength", type=float, default=45, help="Elastic strength percentage (default: 45)")

    # Command: recolor
    recolor_p = subparsers.add_parser("recolor", help="Recolor path at coordinate or by index")
    recolor_p.add_argument("--x", type=float, help="Coordinate X (SVG space)")
    recolor_p.add_argument("--y", type=float, help="Coordinate Y (SVG space)")
    recolor_p.add_argument("--index", type=int, help="Path index in SVG")
    recolor_p.add_argument("--color", required=True, help="Hex color code, e.g. #3b82f6")

    # Command: thicken
    thicken_p = subparsers.add_parser("thicken", help="Expand contour line thickness")
    thicken_p.add_argument("--x", type=float, required=True)
    thicken_p.add_argument("--y", type=float, required=True)
    thicken_p.add_argument("--radius", type=float, default=32)
    thicken_p.add_argument("--strength", type=float, default=45)

    # Command: contract
    contract_p = subparsers.add_parser("contract", help="Shrink contour line thickness")
    contract_p.add_argument("--x", type=float, required=True)
    contract_p.add_argument("--y", type=float, required=True)
    contract_p.add_argument("--radius", type=float, default=32)
    contract_p.add_argument("--strength", type=float, default=45)

    # Command: gap
    gap_p = subparsers.add_parser("gap", help="Nudge feature or create gap")
    gap_p.add_argument("--x", type=float, required=True)
    gap_p.add_argument("--y", type=float, required=True)
    gap_p.add_argument("--shift", type=float, default=18)
    gap_p.add_argument("--radius", type=float, default=32)

    # Command: auto
    auto_p = subparsers.add_parser("auto", help="Auto-generate subtle differences autonomously")
    auto_p.add_argument("--diffs", type=int, default=5, help="Number of differences to generate (default: 5)")
    auto_p.add_argument("--difficulty", choices=["easy", "medium", "subtle"], default="medium")

    # Command: export
    export_p = subparsers.add_parser("export", help="Export puzzle challenge or solution card")
    export_p.add_argument("--format", choices=["dual-card", "solution-card", "png", "jpg", "svg"], default="dual-card")
    export_p.add_argument("--scale", type=int, default=2)
    export_p.add_argument("--out", help="Output file path on disk")

    # Command: undo, redo, reset
    subparsers.add_parser("undo", help="Undo last action")
    subparsers.add_parser("redo", help="Redo last action")
    subparsers.add_parser("reset", help="Revert to master baseline")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "state":
        st = get_state()
        print(json.dumps(st, indent=2))

    elif args.command == "diffs":
        df = get_diffs()
        print(json.dumps(df, indent=2))

    elif args.command == "load":
        res = load_file(args.file_path)
        print(json.dumps(res, indent=2))

    elif args.command == "erase":
        params = {}
        if args.index is not None:
            params["index"] = args.index
        elif args.x is not None and args.y is not None:
            params["x"] = args.x
            params["y"] = args.y
        else:
            print("Error: Specify either --index or --x and --y")
            sys.exit(1)
        res = send_action("erase", params)
        print(json.dumps(res, indent=2))

    elif args.command == "pull":
        params = {
            "x": args.x,
            "y": args.y,
            "dx": args.dx,
            "dy": args.dy,
            "radius": args.radius,
            "strength": args.strength
        }
        res = send_action("pull", params)
        print(json.dumps(res, indent=2))

    elif args.command == "recolor":
        params = {"color": args.color}
        if args.index is not None:
            params["index"] = args.index
        elif args.x is not None and args.y is not None:
            params["x"] = args.x
            params["y"] = args.y
        else:
            print("Error: Specify either --index or --x and --y")
            sys.exit(1)
        res = send_action("recolor", params)
        print(json.dumps(res, indent=2))

    elif args.command == "thicken":
        params = {"x": args.x, "y": args.y, "radius": args.radius, "strength": args.strength}
        res = send_action("thicken", params)
        print(json.dumps(res, indent=2))

    elif args.command == "contract":
        params = {"x": args.x, "y": args.y, "radius": args.radius, "strength": args.strength}
        res = send_action("contract", params)
        print(json.dumps(res, indent=2))

    elif args.command == "gap":
        params = {"x": args.x, "y": args.y, "shift": args.shift, "radius": args.radius}
        res = send_action("gap", params)
        print(json.dumps(res, indent=2))

    elif args.command == "auto":
        params = {"count": args.diffs, "difficulty": args.difficulty}
        res = send_action("autoGenerateDiffs", params)
        print(json.dumps(res, indent=2))

    elif args.command == "export":
        params = {"format": args.format, "scale": args.scale, "outputPath": args.out}
        res = send_action("exportPuzzle", params)
        print(json.dumps(res, indent=2))

    elif args.command in ["undo", "redo", "reset"]:
        res = send_action(args.command)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
