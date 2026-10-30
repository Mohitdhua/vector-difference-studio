import subprocess
import json

def call_mcp(tool_name, arguments=None):
    if arguments is None:
        arguments = {}
    p = subprocess.Popen(['python', r'F:\svg puzzle\diff_studio_mcp.py'], 
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    req = {
        'jsonrpc': '2.0', 
        'id': 1, 
        'method': 'tools/call', 
        'params': {'name': tool_name, 'arguments': arguments}
    }
    out, _ = p.communicate(json.dumps(req) + '\n', timeout=10)
    data = json.loads(out)
    content_text = data['result']['content'][0]['text']
    try:
        return json.loads(content_text)
    except Exception:
        return {"raw": content_text}

# 1. Reset
print('Step 1: Resetting canvas...')
call_mcp('studio_reset')

# 2. Add 3 subtle diffs
print('Step 2: Auto-generating 3 subtle differences via MCP...')
res_auto = call_mcp('studio_auto_generate', {'count': 3, 'difficulty': 'subtle'})

# 3. Check diffs
print('Step 3: Querying active differences...')
res_diffs = call_mcp('studio_get_diffs')
diffs_obj = res_diffs.get('diffs', {})
diff_items = diffs_obj.get('diffs', []) if isinstance(diffs_obj, dict) else []

print(f'Done! Active differences count: {len(diff_items)}')
for i, d in enumerate(diff_items):
    t = d.get('type')
    idx = d.get('index')
    bbox = d.get('bbox', {})
    print(f"Diff {i+1}: {t} on path {idx} at ({bbox.get('x')}, {bbox.get('y')})")
