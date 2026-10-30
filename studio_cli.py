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

def get_elements():
    try:
        r = requests.get(f"{SERVER_URL}/api/elements", timeout=3)
        return r.json()
    except Exception as e:
        print(f"Error fetching elements: {e}")
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

    # Command: elements
    subparsers.add_parser("elements", help="Inspect SVG paths, bounding boxes, and colors")

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
    recolor_p.add_argument("--color", required=True, help="Hex or CSS color string (e.g. #ef4444)")

    # Command: auto (Autonomous Differences)
    auto_p = subparsers.add_parser("auto", help="Autonomous generation of subtle differences")
    auto_p.add_argument("--diffs", type=int, default=5, help="Number of differences to create (default: 5)")
    auto_p.add_argument("--difficulty", choices=["easy", "medium", "subtle"], default="medium", help="Difficulty preset")

    # Command: undo, redo, reset
    subparsers.add_parser("undo", help="Undo last modification")
    subparsers.add_parser("redo", help="Redo undone modification")
    subparsers.add_parser("reset", help="Reset puzzle back to original unmodified state")

    # Command: export
    export_p = subparsers.add_parser("export", help="Export puzzle challenge and solution sheet")
    export_p.add_argument("--output-dir", default="./puzzle_export", help="Directory to save exported files")
    export_p.add_argument("--scale", type=float, default=2.0, help="Resolution scale (e.g. 1.0, 2.0, 4.0, 8.0)")
    export_p.add_argument("--format", choices=["png", "svg"], default="png", help="Export format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "state":
        res = get_state()
        print(json.dumps(res, indent=2))

    elif args.command == "diffs":
        res = get_diffs()
        print(json.dumps(res, indent=2))

    elif args.command == "elements":
        res = get_elements()
        print(json.dumps(res, indent=2))

    elif args.command == "load":
        res = load_file(args.file_path)
        print(json.dumps(res, indent=2))

    elif args.command == "erase":
        res = send_action("erase", {"x": args.x, "y": args.y, "index": args.index})
        print(json.dumps(res, indent=2))

    elif args.command == "pull":
        res = send_action("pull", {
            "x": args.x,
            "y": args.y,
            "dx": args.dx,
            "dy": args.dy,
            "radius": args.radius,
            "strength": args.strength
        })
        print(json.dumps(res, indent=2))

    elif args.command == "recolor":
        res = send_action("recolor", {
            "x": args.x,
            "y": args.y,
            "index": args.index,
            "color": args.color
        })
        print(json.dumps(res, indent=2))

    elif args.command == "auto":
        res = send_action("autoGenerateDiffs", {
            "count": args.diffs,
            "difficulty": args.difficulty
        })
        print(json.dumps(res, indent=2))

    elif args.command == "undo":
        res = send_action("undo")
        print(json.dumps(res, indent=2))

    elif args.command == "redo":
        res = send_action("redo")
        print(json.dumps(res, indent=2))

    elif args.command == "reset":
        res = send_action("reset")
        print(json.dumps(res, indent=2))

    elif args.command == "export":
        res = send_action("exportPuzzle", {
            "outputDir": args.output_dir,
            "scale": args.scale,
            "format": args.format
        })
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
