#!/usr/bin/env python3
"""
Vector Difference Studio MCP Server (Model Context Protocol)
Allows Claude Desktop, Claude Code, Antigravity, and other MCP clients
to autonomously control the Vector Difference Studio.
"""

import sys
import json
import requests

STUDIO_URL = "http://localhost:8080"

TOOLS = [
    {
        "name": "studio_get_state",
        "description": "Get current state of the Difference Studio artboard (loaded SVG, diff count, dimensions, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_load_svg",
        "description": "Load an SVG file from the local file system into the active studio session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the .svg file on disk"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "studio_point_pull",
        "description": "Perform linked point pull on an SVG curve, pulling both outline ribbons and underlying color fills together without tearing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "Anchor X coordinate in SVG artboard units"},
                "y": {"type": "number", "description": "Anchor Y coordinate in SVG artboard units"},
                "dx": {"type": "number", "description": "Displacement offset along X axis (+ right, - left)"},
                "dy": {"type": "number", "description": "Displacement offset along Y axis (+ down, - up)"},
                "radius": {"type": "number", "description": "Influence radius (default: 32)", "default": 32},
                "strength": {"type": "number", "description": "Elastic deformation strength % (default: 45)", "default": 45}
            },
            "required": ["x", "y", "dx", "dy"]
        }
    },
    {
        "name": "studio_recolor",
        "description": "Recolor a shape/path either by (x, y) coordinate or by path index to a new hex color.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "New hex color, e.g. '#e53e3e' or '#3b82f6'"},
                "x": {"type": "number", "description": "X coordinate touching the shape"},
                "y": {"type": "number", "description": "Y coordinate touching the shape"},
                "index": {"type": "integer", "description": "Optional index of the path in SVG DOM"}
            },
            "required": ["color"]
        }
    },
    {
        "name": "studio_thicken",
        "description": "Expand contour line thickness locally around (x, y).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "radius": {"type": "number", "default": 32},
                "strength": {"type": "number", "default": 45}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "studio_contract",
        "description": "Shrink contour line thickness locally around (x, y).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "radius": {"type": "number", "default": 32},
                "strength": {"type": "number", "default": 45}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "studio_auto_generate",
        "description": "Autonomously select candidate non-critical paths in the SVG and create N subtle differences with solution coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff_count": {"type": "integer", "description": "Number of differences to create (e.g. 3, 5, 7)", "default": 5},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "subtle"], "default": "medium"}
            }
        }
    },
    {
        "name": "studio_get_diffs",
        "description": "Get current list of all differences on the artboard with their bounding boxes and details.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_export",
        "description": "Export the puzzle as a dual side-by-side challenge card, solution card, or standalone image.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["dual-card", "solution-card", "png", "jpg", "svg"], "default": "dual-card"},
                "scale": {"type": "integer", "enum": [1, 2, 4], "default": 2},
                "output_path": {"type": "string", "description": "Optional absolute path to save file directly on disk"}
            }
        }
    },
    {
        "name": "studio_undo",
        "description": "Undo the last editing step in the studio.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

def handle_rpc(request):
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "difference-studio-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "studio_get_state":
                r = requests.get(f"{STUDIO_URL}/api/state", timeout=4)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_load_svg":
                r = requests.post(f"{STUDIO_URL}/api/load-file", json={"filePath": args.get("file_path")}, timeout=6)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_point_pull":
                payload = {"action": "pull", "params": args, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=6)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_recolor":
                payload = {"action": "recolor", "params": args, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=6)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_thicken":
                payload = {"action": "thicken", "params": args, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=6)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_contract":
                payload = {"action": "contract", "params": args, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=6)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_auto_generate":
                p = {"count": args.get("diff_count", 5), "difficulty": args.get("difficulty", "medium")}
                payload = {"action": "autoGenerateDiffs", "params": p, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=8)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_get_diffs":
                r = requests.get(f"{STUDIO_URL}/api/diffs", timeout=4)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_export":
                payload = {
                    "action": "exportPuzzle",
                    "params": {
                        "format": args.get("format", "dual-card"),
                        "scale": args.get("scale", 2),
                        "outputPath": args.get("output_path")
                    },
                    "sync": True
                }
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=10)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            elif tool_name == "studio_undo":
                payload = {"action": "undo", "params": {}, "sync": True}
                r = requests.post(f"{STUDIO_URL}/api/action", json=payload, timeout=4)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": r.text}]}}

            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method {tool_name} not found"}}

        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Unsupported method"}}

def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            resp = handle_rpc(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
