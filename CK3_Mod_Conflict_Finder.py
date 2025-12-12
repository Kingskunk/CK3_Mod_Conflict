import os, json, ctypes, ctypes.wintypes
from typing import Dict, List

def norm(p: str) -> str:
    return p.replace("\\", "/").lower()

def open_file(path: str):
    path = str(path)
    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()

# --- config & paths ---
this_file_path = norm(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(this_file_path, "config.json"), "r", encoding="utf-8") as cfg:
    cfgj = json.load(cfg)
    game_file_path = cfgj["game_path"]
    steam_dir_path = cfgj["steam_mod_path"]

# Documents path (Windows)
buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
ctypes.windll.shell32.SHGetFolderPathW(None, 0x0005, None, None, buf)
documents_ck3_path = norm(buf.value + "/Paradox Interactive/Crusader Kings III")

# --- settings ---
WRITE_OUT = True
FILE_EXTS = (".txt", ".gui", ".asset", ".py")

# --- exclusions ---
try:
    exclusions = open_file(f"{this_file_path}/resolved_conflicts.txt")
except FileNotFoundError:
    exclusions = []
EXCLUSIONS = {e.strip().lower() for e in exclusions if e.strip()}

# --- load order / mod name lookup (1-based for mods, Game=0) ---
load_order = open_file(f"{documents_ck3_path}/dlc_load.json")["enabled_mods"]

mod_name_dict: Dict[str, str] = {}
name_order_lookup: Dict[str, int] = {}

for idx, local_mod_file in enumerate(load_order, start=1):
    mod_path_full = f"{documents_ck3_path}/{local_mod_file}"
    try:
        descriptor = open_file(mod_path_full)
    except FileNotFoundError:
        continue
    human_name = None
    mod_path = None
    for line in descriptor:
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().lower()
        v = v.strip().strip('"').strip()
        if k == "name":
            human_name = v
        elif k == "path":
            mod_path = norm(v)
    if human_name and mod_path:
        mod_name_dict[mod_path] = human_name
        name_order_lookup[human_name] = idx

# Ensure Game has order 0 and is present in mod_name_dict
mod_name_dict[norm(game_file_path)] = "Game"
name_order_lookup["Game"] = 0

# --- helper to list files with given extensions ---
def make_files_list(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not os.path.isdir(path):
        return out
    for root, _, files in os.walk(path):
        for fn in files:
            if not fn.lower().endswith(FILE_EXTS):
                continue
            if any(ex in fn.lower() for ex in EXCLUSIONS):
                continue
            full = norm(os.path.join(root, fn))
            out[full] = fn
    return out

# --- gather files from mods, game, steam ---
mods_conflicts: Dict[str, List[str]] = {}
for path_list in (
    make_files_list(f"{documents_ck3_path}/mod"),
    make_files_list(game_file_path),
    make_files_list(steam_dir_path),
):
    for full_path, filename in path_list.items():
        mods_conflicts.setdefault(filename, []).append(full_path)

# keep only duplicates
mods_conflicts = {k: v for k, v in mods_conflicts.items() if len(v) > 1}

if WRITE_OUT:
    with open(f"{this_file_path}/mods_conflicts.txt", "w", encoding="utf-8") as f:
        json.dump(mods_conflicts, f, ensure_ascii=False, indent=0)

# --- map each file occurrence to the mod/game that owns that path ---
named_conflicts: Dict[str, List[tuple]] = {}
for fname, locations in mods_conflicts.items():
    for loc in locations:
        # find best matching mod path (longest prefix)
        matches = [(mp, mn) for mp, mn in mod_name_dict.items() if loc.startswith(mp)]
        if not matches:
            continue
        mod_location, mod_name = max(matches, key=lambda t: len(t[0]))
        order = 0 if mod_name == "Game" else name_order_lookup.get(mod_name, list(mod_name_dict.keys()).index(mod_location) + 1)
        named_conflicts.setdefault(fname, []).append((order, mod_name, loc))

# sort entries per file by order then path
for fname in list(named_conflicts.keys()):
    named_conflicts[fname] = sorted(named_conflicts[fname], key=lambda v: (v[0], v[2]))

# keep only files that involve >=2 distinct mods (Game counts)
final_conflicts = {k: v for k, v in named_conflicts.items() if len({m for _, m, _ in v}) >= 2}

# --- build summary counts ---
conflict_counts: Dict[str, int] = {}
conflict_partners: Dict[str, set] = {}
game_conflicts: Dict[str, int] = {}
mod_order_index: Dict[str, int] = {}

for fname, entries in final_conflicts.items():
    distinct = {m for _, m, _ in entries}
    if len(distinct) <= 1:
        continue
    for order, mod_name, _ in entries:
        if mod_name == "Game":
            continue
        conflict_counts[mod_name] = conflict_counts.get(mod_name, 0) + 1
        normalized = 0 if mod_name == "Game" else name_order_lookup.get(mod_name, order)
        if mod_name not in mod_order_index or normalized < mod_order_index[mod_name]:
            mod_order_index[mod_name] = normalized
        if "Game" in distinct:
            game_conflicts[mod_name] = game_conflicts.get(mod_name, 0) + 1
        partners = {m for m in distinct if m != mod_name and m != "Game"}
        if partners:
            conflict_partners.setdefault(mod_name, set()).update(partners)

# --- render output ---
output_lines: List[str] = []
output_lines.append("=== Combined Conflict Summary ===")
for mod_name in sorted(conflict_counts.keys(), key=lambda m: mod_order_index.get(m, 9999)):
    partners = conflict_partners.get(mod_name, set())
    partners_list = ", ".join(sorted(partners)) if partners else "None"
    game_count = game_conflicts.get(mod_name, 0)
    if not partners and game_count == 0:
        continue
    order_display = mod_order_index.get(mod_name, "?")
    output_lines.append(f"[{order_display}] {mod_name}: {conflict_counts[mod_name]} total conflicts (Mod-to-Mod: {len(partners)} partners → {partners_list}; With Game: {game_count})")

output_lines.append("\n=== Detailed Conflicts ===\n")
for fname, entries in final_conflicts.items():
    distinct = {m for _, m, _ in entries}
    if len(distinct) <= 1:
        continue
    output_lines.append(f"\nFile: {fname}")
    for order, mod_name, loc in sorted(entries, key=lambda v: v[0]):
        display_order = 0 if mod_name == "Game" else order
        output_lines.append(f"  - [{display_order}] {mod_name} ({loc})")

# write summary
summary_path = f"{this_file_path}/mod_conflict_summary.txt"
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))
