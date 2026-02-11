#!/bin/bash
# Generate data.json for the Multi-Agent Dashboard
# Scans all 3 agent workspaces and produces dashboard/data.json

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$SCRIPT_DIR/data.json"

python3 << 'PYEOF'
import json, os, glob, re
from datetime import datetime
from pathlib import Path

AGENTS = [
    {"id":"hugo","name":"Hugo","emoji":"🚀","role":"Marketing Agent","color":"#F5A623","workspace":"/Users/alfred/.openclaw/workspace-hugo"},
    {"id":"alfred","name":"Alfred","emoji":"🐸","role":"HR & Recruiting Agent","color":"#00b894","workspace":"/Users/alfred/.openclaw/workspace"},
    {"id":"rainman","name":"Rainman","emoji":"📊","role":"Data Analyst","color":"#3b82f6","workspace":"/Users/alfred/.openclaw/workspace-rainman"},
]

EXCLUDE_DIRS = {'.git','node_modules','.next','cache','__pycache__','.DS_Store','trash'}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "data.json")

def parse_projects(ws):
    path = os.path.join(ws, "PROJECTS.md")
    if not os.path.isfile(path):
        return []
    projects = []
    try:
        with open(path, 'r') as f:
            content = f.read()
    except:
        return []
    # Split by ## headings
    blocks = re.split(r'^## ', content, flags=re.MULTILINE)
    for block in blocks[1:]:  # skip preamble
        lines = block.strip().split('\n')
        title_line = lines[0].strip()
        # Extract emoji icon if present
        icon = "📄"
        m = re.match(r'^([\U0001F000-\U0001FFFF\u2600-\u27BF])\s*(.+)', title_line)
        if m:
            icon, title_line = m.group(1), m.group(2)
        title = re.sub(r'\s*\[.*?\]\s*$', '', title_line).strip()
        
        body = '\n'.join(lines[1:])
        status = "backlog"
        for s in ["done","ongoing","active","blocked","backlog"]:
            if re.search(r'(?i)\b'+s+r'\b', body) or re.search(r'(?i)\b'+s+r'\b', title_line):
                status = s; break
        # Also check for status patterns like **Status:** done
        sm = re.search(r'(?i)status[:\s]+(\w+)', body)
        if sm:
            sv = sm.group(1).lower()
            if sv in ("done","ongoing","active","blocked","backlog","progress"):
                status = "active" if sv == "progress" else sv

        pct = 0
        pm = re.search(r'(\d+)\s*%', body)
        if pm: pct = int(pm.group(1))
        
        nxt = ""
        nm = re.search(r'(?i)next[:\s]+(.+)', body)
        if nm: nxt = nm.group(1).strip()
        
        files = 0
        fm = re.search(r'(?i)files?[:\s]+(\d+)', body)
        if fm: files = int(fm.group(1))
        
        date = ""
        dm = re.search(r'(\d{4}-\d{2}-\d{2})', body)
        if dm: date = dm.group(1)
        
        detail = body.strip()[:300] if body.strip() else ""
        
        projects.append({"icon":icon,"title":title,"status":status,"pct":pct,"next":nxt,"files":files,"date":date,"detail":detail})
    return projects

def parse_knowledge(ws):
    path = os.path.join(ws, "KNOWLEDGE.md")
    if not os.path.isfile(path):
        return []
    items = []
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                if '✅' in line:
                    name = re.sub(r'[✅🟡🔴\-\*#]+', '', line).strip()
                    if name: items.append({"name":name,"status":"learned"})
                elif '🟡' in line:
                    name = re.sub(r'[✅🟡🔴\-\*#]+', '', line).strip()
                    if name: items.append({"name":name,"status":"partial"})
                elif '🔴' in line:
                    name = re.sub(r'[✅🟡🔴\-\*#]+', '', line).strip()
                    if name: items.append({"name":name,"status":"missing"})
    except:
        pass
    return items

def parse_heartbeat(ws):
    path = os.path.join(ws, "HEARTBEAT.md")
    if not os.path.isfile(path):
        return []
    tasks = []
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                # Look for lines with frequency patterns
                m = re.search(r'([\U0001F000-\U0001FFFF\u2600-\u27BF])?\s*(.+?)\s*[—–-]\s*(.+)', line)
                if m:
                    icon = m.group(1) or "⚡"
                    name = m.group(2).strip().strip('*').strip()
                    freq = m.group(3).strip()
                    tasks.append({"icon":icon,"name":name,"freq":freq})
                elif re.search(r'\d+\s*(min|h|hour|daily|weekly)', line, re.I):
                    fm = re.search(r'(\d+\s*(?:min|h|hour|s|daily|weekly))', line, re.I)
                    freq = fm.group(1) if fm else ""
                    name = re.sub(r'[\-\*]+', '', line).strip()
                    name = re.sub(r'\d+\s*(?:min|h|hour|s|daily|weekly)', '', name, flags=re.I).strip().strip('—–-').strip()
                    if name: tasks.append({"icon":"⚡","name":name[:50],"freq":freq})
    except:
        pass
    return tasks

def parse_timeline(ws):
    mem_dir = os.path.join(ws, "memory")
    if not os.path.isdir(mem_dir):
        return []
    events = []
    files = sorted(glob.glob(os.path.join(mem_dir, "*.md")), reverse=True)[:3]
    for fp in files:
        try:
            date_part = os.path.basename(fp).replace('.md','')
            with open(fp, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if line.startswith('- ') or line.startswith('* '):
                        text = line.lstrip('-* ').strip()
                        if len(text) < 5: continue
                        icon = "📌"
                        im = re.match(r'^([\U0001F000-\U0001FFFF\u2600-\u27BF])\s*(.+)', text)
                        if im: icon, text = im.group(1), im.group(2)
                        # Extract time if present
                        tm = re.search(r'(\d{1,2}:\d{2})', text)
                        time_str = tm.group(1) if tm else "00:00"
                        events.append({"date":f"{date_part} {time_str}","text":text[:120],"icon":icon})
        except:
            pass
    return events[:20]

def build_file_tree(ws):
    ws_path = Path(ws)
    if not ws_path.is_dir():
        return {"name": os.path.basename(ws), "children": []}
    
    def scan(p, depth=0):
        if depth > 4: return None
        name = p.name
        if name in EXCLUDE_DIRS: return None
        if p.is_dir():
            children = []
            try:
                for child in sorted(p.iterdir()):
                    node = scan(child, depth+1)
                    if node: children.append(node)
            except PermissionError:
                pass
            if not children and depth > 0: return None
            return {"name": name, "children": children}
        else:
            try:
                size = p.stat().st_size
                if size < 1024: s = f"{size}B"
                elif size < 1048576: s = f"{size/1024:.1f}KB"
                else: s = f"{size/1048576:.1f}MB"
            except:
                s = ""
            return {"name": name, "size": s}
    
    result = scan(ws_path)
    return result or {"name": os.path.basename(ws), "children": []}

data = {
    "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "agents": []
}

for ag in AGENTS:
    ws = ag["workspace"]
    exists = os.path.isdir(ws)
    agent_data = {
        "id": ag["id"],
        "name": ag["name"],
        "emoji": ag["emoji"],
        "role": ag["role"],
        "color": ag["color"],
        "status": "active" if exists else "offline",
        "projects": parse_projects(ws) if exists else [],
        "tasks": parse_heartbeat(ws) if exists else [],
        "knowledge": parse_knowledge(ws) if exists else [],
        "timeline": parse_timeline(ws) if exists else [],
        "files": build_file_tree(ws) if exists else {"name": os.path.basename(ws), "children": []}
    }
    data["agents"].append(agent_data)

with open(OUTPUT, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ data.json generated with {len(data['agents'])} agents")
for ag in data["agents"]:
    print(f"   {ag['emoji']} {ag['name']}: {len(ag['projects'])} projects, {len(ag['knowledge'])} knowledge, {len(ag['timeline'])} events, {len(ag['tasks'])} tasks")
PYEOF
