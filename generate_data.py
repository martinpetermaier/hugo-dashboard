#!/usr/bin/env python3
"""Generate data.json for the Multi-Agent Dashboard from local workspace files."""
import json, os, glob, re
from datetime import datetime, timezone
from pathlib import Path

AGENTS = [
    {"id":"hugo","name":"Hugo","emoji":"🚀","role":"Marketing Agent","color":"#F5A623",
     "workspace":"/Users/alfred/.openclaw/workspace-hugo"},
    {"id":"alfred","name":"Alfred","emoji":"🐸","role":"HR & Recruiting Agent","color":"#00b894",
     "workspace":"/Users/alfred/.openclaw/workspace"},
    {"id":"rainman","name":"Rainman","emoji":"📊","role":"Data Analyst","color":"#3b82f6",
     "workspace":"/Users/alfred/.openclaw/workspace-rainman"},
]

EXCLUDE = {'.git','node_modules','.next','cache','__pycache__','.DS_Store','trash','.clawhub','b64','vorlagen','test-results'}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "data.json")

STATUS_MAP = {
    '✅': 'done', 'done': 'done',
    '🔵': 'ongoing', 'ongoing': 'ongoing',
    '🟡': 'active', 'active': 'active', 'in progress': 'active',
    '🔴': 'blocked', 'blocked': 'blocked',
    'backlog': 'backlog',
}

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def parse_projects(ws):
    """Parse PROJECTS.md — handles ### headings with - **Key:** Value fields."""
    content = read_file(os.path.join(ws, "PROJECTS.md"))
    if not content:
        return []
    
    projects = []
    # Split on ### (H3) headings — these are individual projects
    blocks = re.split(r'^###\s+', content, flags=re.MULTILINE)
    
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        if not lines:
            continue
        
        title_line = lines[0].strip()
        
        # Extract emoji icon
        icon = "📄"
        m = re.match(r'^([^\w\s])\s*(.+)', title_line)
        if m and ord(m.group(1)[0]) > 127:
            icon, title_line = m.group(1), m.group(2)
        title = title_line.strip()
        
        body = '\n'.join(lines[1:])
        
        # Parse status
        status = "backlog"
        sm = re.search(r'\*\*Status:\*\*\s*(.+)', body)
        if sm:
            status_text = sm.group(1).lower().strip()
            for key, val in STATUS_MAP.items():
                if key in status_text:
                    status = val
                    break
        
        # Parse percentage
        pct = 0
        pm = re.search(r'(\d+)\s*%', body)
        if pm:
            pct = int(pm.group(1))
        elif status == 'done':
            pct = 100
        elif status == 'ongoing':
            pct = 85
        elif status == 'active':
            pct = 50
        
        # Parse next step
        nxt = ""
        nm = re.search(r'\*\*Next:\*\*\s*(.+)', body)
        if nm:
            nxt = nm.group(1).strip()
        
        # Parse files folder
        folder = ""
        fm = re.search(r'\*\*Files:\*\*\s*(.+)', body)
        if fm:
            folder = fm.group(1).strip()
        
        # Count actual files if folder referenced (exclude build artifacts)
        files_count = 0
        if folder:
            folder_path = os.path.join(ws, folder.rstrip('/'))
            if os.path.isdir(folder_path):
                for dirpath, dirnames, fnames in os.walk(folder_path):
                    dirnames[:] = [d for d in dirnames if d not in EXCLUDE]
                    files_count += len([f for f in fnames if f != '.DS_Store'])
        
        # Parse date
        date = ""
        dm = re.search(r'(\d{4}-\d{2}-\d{2})', body)
        if dm:
            date = dm.group(1)
        
        # Build detail from body
        detail_lines = [l.strip().lstrip('- ') for l in lines[1:] if l.strip() and not l.strip().startswith('**')]
        detail = ' '.join(detail_lines)[:200]
        
        projects.append({
            "icon": icon, "title": title, "status": status,
            "pct": pct, "next": nxt, "files": files_count,
            "date": date, "detail": detail
        })
    
    return projects

def parse_knowledge(ws):
    """Parse KNOWLEDGE.md — sections with ## heading + ✅/🟡/🔴 status."""
    content = read_file(os.path.join(ws, "KNOWLEDGE.md"))
    if not content:
        return []
    
    items = []
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
    
    for section in sections[1:]:
        lines = section.strip().split('\n')
        if not lines:
            continue
        heading = lines[0].strip()
        
        # Determine status from the heading line
        status = "partial"
        if '✅' in heading:
            status = "learned"
            heading = heading.replace('✅', '').strip()
        elif '🟡' in heading:
            status = "partial"
            heading = heading.replace('🟡', '').strip()
        elif '🔴' in heading:
            status = "missing"
            heading = heading.replace('🔴', '').strip()
        
        if heading and len(heading) > 2:
            items.append({"name": heading, "status": status})
    
    return items

def parse_tasks(ws):
    """Parse HEARTBEAT.md + PROJECTS.md recurring tasks section."""
    tasks = []
    
    # Parse from PROJECTS.md "Wiederkehrende Aufgaben" table
    content = read_file(os.path.join(ws, "PROJECTS.md"))
    if content:
        # Find everything between "Wiederkehrende Aufgaben" and next ## heading
        tm = re.search(r'Wiederkehrende Aufgaben\s*\n([\s\S]*?)(?=\n##|\Z)', content)
        if tm:
            table_block = tm.group(1)
            for row in table_block.strip().split('\n'):
                row = row.strip()
                if not row.startswith('|') or row.startswith('|--') or row.startswith('|-'):
                    continue
                cells = [c.strip() for c in row.split('|')]
                cells = [c for c in cells if c]
                if len(cells) >= 2 and cells[0] not in ('Aufgabe', '---', '-'):
                    name = cells[0]
                    freq = cells[1] if len(cells) > 1 else ""
                    # Determine icon based on content
                    icon = "⚡"
                    nl = name.lower()
                    if 'slack' in nl: icon = "💬"
                    elif 'linkedin' in nl: icon = "💼"
                    elif 'knowledge' in nl: icon = "📚"
                    elif 'dashboard' in nl or 'icloud' in nl: icon = "📁"
                    elif 'wettbewerber' in nl or 'competitor' in nl: icon = "🔍"
                    elif 'seo' in nl: icon = "📈"
                    elif 'memory' in nl: icon = "🧠"
                    elif 'kalender' in nl or 'calendar' in nl: icon = "📅"
                    tasks.append({"icon": icon, "name": name.strip(), "freq": freq})
    
    # Also parse HEARTBEAT.md sections
    hb = read_file(os.path.join(ws, "HEARTBEAT.md"))
    if hb:
        sections = re.split(r'^##\s+', hb, flags=re.MULTILINE)
        for section in sections[1:]:
            heading = section.split('\n')[0].strip()
            # Determine frequency from heading
            freq = "Heartbeat"
            heading_lower = heading.lower()
            if 'daily' in heading_lower or 'täglich' in heading_lower or '1x daily' in heading_lower:
                freq = "Täglich"
            elif 'weekly' in heading_lower or 'wöchentlich' in heading_lower:
                freq = "Wöchentlich"
            elif 'heartbeat' in heading_lower or 'every heartbeat' in heading_lower:
                freq = "Alle 5 Min"
            elif 'every' in heading_lower:
                fm = re.search(r'every\s+(\w+)', heading_lower)
                if fm: freq = f"Every {fm.group(1)}"
            
            # Determine icon
            icon = "⚡"
            if 'slack' in heading_lower: icon = "💬"
            elif 'notion' in heading_lower: icon = "📝"
            elif 'google' in heading_lower or 'calendar' in heading_lower or 'kalender' in heading_lower: icon = "📅"
            elif 'cv' in heading_lower or 'extract' in heading_lower: icon = "📄"
            elif 'sync' in heading_lower: icon = "🔄"
            elif 'task' in heading_lower: icon = "✅"
            elif 'inbox' in heading_lower: icon = "📥"
            elif 'chat' in heading_lower: icon = "💬"
            
            # Clean heading for display
            clean = re.sub(r'\(.*?\)', '', heading).strip()
            if clean and len(clean) > 3:
                # Avoid duplicates
                if not any(t['name'].lower() == clean.lower() for t in tasks):
                    tasks.append({"icon": icon, "name": clean[:50], "freq": freq})
        
        # Numbered items fallback (for simple heartbeats like Hugo's)
        if not tasks:
            for line in hb.split('\n'):
                line = line.strip()
                m = re.match(r'^\d+\.\s+(.+)', line)
                if m:
                    text = m.group(1)
                    if 'slack' in text.lower():
                        tasks.append({"icon": "💬", "name": "Slack Mentions checken", "freq": "Alle 5 Min"})
                    elif 'calendar' in text.lower() or 'kalender' in text.lower():
                        tasks.append({"icon": "📅", "name": "Kalender checken", "freq": "Alle 5 Min"})
    
    return tasks

def parse_timeline(ws):
    """Parse memory/*.md for timeline events — extract meaningful entries with timestamps."""
    mem_dir = os.path.join(ws, "memory")
    if not os.path.isdir(mem_dir):
        return []
    
    events = []
    files = sorted(glob.glob(os.path.join(mem_dir, "*.md")), reverse=True)[:5]
    
    for fp in files:
        try:
            date_part = os.path.basename(fp).replace('.md', '')
            # Skip files with extra suffixes like "afternoon"
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
                date_part = re.match(r'(\d{4}-\d{2}-\d{2})', date_part)
                date_part = date_part.group(1) if date_part else "unknown"
            
            content = read_file(fp)
            current_section = ""
            
            for line in content.split('\n'):
                line = line.strip()
                
                # Track section headings
                if line.startswith('## '):
                    current_section = line[3:].strip()
                    # Use section heading as a timeline event
                    icon = "📌"
                    if any(w in current_section.lower() for w in ['slack', 'mention']):
                        icon = "💬"
                    elif any(w in current_section.lower() for w in ['dashboard']):
                        icon = "📊"
                    elif any(w in current_section.lower() for w in ['notion']):
                        icon = "📝"
                    elif any(w in current_section.lower() for w in ['kalender', 'calendar']):
                        icon = "📅"
                    elif any(w in current_section.lower() for w in ['produkt', 'product']):
                        icon = "📦"
                    elif any(w in current_section.lower() for w in ['projekt', 'project']):
                        icon = "🏗️"
                    elif any(w in current_section.lower() for w in ['github']):
                        icon = "🐙"
                    
                    # Try to extract time from the section content
                    time_match = re.search(r'(\d{1,2}:\d{2})', current_section)
                    time_str = time_match.group(1) if time_match else ""
                    
                    events.append({
                        "date": f"{date_part}{' ' + time_str if time_str else ''}",
                        "text": current_section[:120],
                        "icon": icon
                    })
        except Exception as e:
            pass
    
    # Sort by date descending, limit to 15
    events.sort(key=lambda x: x['date'], reverse=True)
    return events[:15]

def build_file_tree(ws, max_depth=3):
    """Build file tree, excluding build artifacts."""
    ws_path = Path(ws)
    if not ws_path.is_dir():
        return {"name": os.path.basename(ws), "children": []}
    
    def format_size(size):
        if size < 1024: return f"{size}B"
        if size < 1048576: return f"{size/1024:.1f}KB"
        return f"{size/1048576:.1f}MB"
    
    def scan(p, depth=0):
        if depth > max_depth:
            return None
        name = p.name
        if name in EXCLUDE or name.startswith('.'):
            return None
        
        if p.is_dir():
            children = []
            try:
                entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                for child in entries:
                    node = scan(child, depth + 1)
                    if node:
                        children.append(node)
            except (PermissionError, OSError):
                pass
            if not children and depth > 1:
                return None
            return {"name": name, "children": children}
        else:
            try:
                size = p.stat().st_size
                return {"name": name, "size": format_size(size)}
            except:
                return {"name": name, "size": ""}
    
    result = scan(ws_path)
    return result or {"name": os.path.basename(ws), "children": []}

# --- Main ---
data = {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "tasks": parse_tasks(ws) if exists else [],
        "knowledge": parse_knowledge(ws) if exists else [],
        "timeline": parse_timeline(ws) if exists else [],
        "files": build_file_tree(ws) if exists else {"name": os.path.basename(ws), "children": []}
    }
    data["agents"].append(agent_data)

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ data.json generated with {len(data['agents'])} agents")
for ag in data["agents"]:
    print(f"   {ag['emoji']} {ag['name']}: {len(ag['projects'])} projects, {len(ag['knowledge'])} knowledge, {len(ag['timeline'])} events, {len(ag['tasks'])} tasks")
