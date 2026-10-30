#!/usr/bin/env python3
"""
Vector Difference Studio MCP Server (Model Context Protocol)
Allows Claude Desktop, Claude Code, Cursor, Antigravity, and other MCP clients
to autonomously inspect, edit, and create Spot-the-Difference puzzles.
"""

import sys
import json
import requests
import os

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
        "name": "studio_get_elements",
        "description": "Inspect SVG elements in the artboard with their indices, bounding boxes, fill colors, and center coordinates.",
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
        "name": "studio_erase",
        "description": "Cleanly erase/vanish an accessory, prop, or detail element from the puzzle with sister contour suppression and solution alignment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "Index of the path in the SVG element list"},
                "x": {"type": "number", "description": "Optional X coordinate touching the object in SVG units"},
                "y": {"type": "number", "description": "Optional Y coordinate touching the object in SVG units"}
            }
        }
    },
    {
        "name": "studio_point_pull",
        "description": "Perform linked point pull on an SVG curve, pulling both outline ribbons and underlying color fills together smoothly without kinks.",
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
        "description": "Recolor an accessory, clothing item, or decorative shape in the modified puzzle.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "Target CSS/HEX color (e.g. '#3b82f6', '#f59e0b')"},
                "index": {"type": "integer", "description": "Optional index of the path"},
                "x": {"type": "number", "description": "Optional X coordinate touching the shape"},
                "y": {"type": "number", "description": "Optional Y coordinate touching the shape"}
            },
            "required": ["color"]
        }
    },
    {
        "name": "studio_auto_generate",
        "description": "Execute professional Spot-the-Difference puzzle creation rules (balanced erases, subtle color shifts, and curvature nudges).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of differences to create (default: 5)", "default": 5},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "subtle"], "description": "Difficulty preset", "default": "medium"}
            }
        }
    },
    {
        "name": "studio_get_diffs",
        "description": "Get active differences in the puzzle with their bounding boxes, change types, and solution coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_undo",
        "description": "Undo the most recent difference or modification.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_redo",
        "description": "Redo the previously undone action.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_reset",
        "description": "Reset modified artwork back to the original unmodified state.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "studio_export",
        "description": "Export the challenge puzzle sheet and solution key to high-resolution image files on disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_dir": {"type": "string", "description": "Directory to save exported files"},
                "format": {"type": "string", "enum": ["png", "svg"], "default": "png"},
                "scale": {"type": "number", "enum": [1, 2, 4, 8], "default": 2}
            }
        }
    }
]

def handle_rpc(request):
    method = request.get("method")
    req_id = request.get("id")

    # 1. Initialize
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
                    "name": "vector-difference-studio-mcp",
                    "version": "2.0.0"
                }
            }
        }

    # 2. List Tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    # 3. Call Tool
    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "studio_get_state":
                r = requests.get(f"{STUDIO_URL}/api/state", timeout=3)
                data = r.json()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                    }
                }

            elif tool_name == "studio_get_elements":
                r = requests.get(f"{STUDIO_URL}/api/elements", timeout=3)
                data = r.json()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                    }
                }

            elif tool_name == "studio_load_svg":
                r = requests.post(f"{STUDIO_URL}/api/load-file", json={"filePath": args.get("file_path")}, timeout=5)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_erase":
                r = requests.post(f"{STUDIO_URL}/api/action", json={
                    "action": "erase",
                    "params": {"index": args.get("index"), "x": args.get("x"), "y": args.get("y")},
                    "sync": True
                }, timeout=5)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_point_pull":
                r = requests.post(f"{STUDIO_URL}/api/action", json={
                    "action": "pull",
                    "params": {
                        "x": args.get("x"),
                        "y": args.get("y"),
                        "dx": args.get("dx"),
                        "dy": args.get("dy"),
                        "radius": args.get("radius", 32),
                        "strength": args.get("strength", 45)
                    },
                    "sync": True
                }, timeout=5)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_recolor":
                r = requests.post(f"{STUDIO_URL}/api/action", json={
                    "action": "recolor",
                    "params": {
                        "color": args.get("color"),
                        "index": args.get("index"),
                        "x": args.get("x"),
                        "y": args.get("y")
                    },
                    "sync": True
                }, timeout=5)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_auto_generate":
                r = requests.post(f"{STUDIO_URL}/api/action", json={
                    "action": "autoGenerateDiffs",
                    "params": {
                        "count": args.get("count", 5),
                        "difficulty": args.get("difficulty", "medium")
                    },
                    "sync": True
                }, timeout=5)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_get_diffs":
                r = requests.get(f"{STUDIO_URL}/api/diffs", timeout=3)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            elif tool_name == "studio_undo":
                r = requests.post(f"{STUDIO_URL}/api/action", json={"action": "undo", "sync": True}, timeout=3)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": "Undone successfully"}]
                    }
                }

            elif tool_name == "studio_redo":
                r = requests.post(f"{STUDIO_URL}/api/action", json={"action": "redo", "sync": True}, timeout=3)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": "Redone successfully"}]
                    }
                }

            elif tool_name == "studio_reset":
                r = requests.post(f"{STUDIO_URL}/api/action", json={"action": "reset", "sync": True}, timeout=3)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": "Reset to original successfully"}]
                    }
                }

            elif tool_name == "studio_export":
                out_dir = args.get("output_dir", os.getcwd())
                os.makedirs(out_dir, exist_ok=True)
                r = requests.post(f"{STUDIO_URL}/api/action", json={
                    "action": "exportPuzzle",
                    "params": {
                        "format": args.get("format", "png"),
                        "scale": args.get("scale", 2),
                        "outputDir": out_dir
                    },
                    "sync": True
                }, timeout=10)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Tool execution failed: {str(e)}"}
            }

    # 4. Unknown Method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }

def main():
    """Stdio JSON-RPC loop for MCP clients."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_rpc(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
