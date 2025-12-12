
import os	# OS file operations
import json		# for Mod load order
import ctypes # for Documents path
import ctypes.wintypes # for Documents path

write_2_file:bool = True
file_extensions:tuple[str, ...] = (".txt", ".gui", ".asset", ".py")

print("\
Launch the game launcher once before running this script!\n\
Remove the mods from load order if the files have been deleted!\n\
Will cause issues if mod with exact same name are present!\n\
")

## --------------------------------------
## Setup Paths
## --------------------------------------
this_file_path : str = os.path.dirname(os.path.abspath(__file__)).replace('\\','/')
print("This file path =\n" + this_file_path)

try:
    with open(os.path.join(this_file_path, "config.json"), "r") as cfg:
        config = json.load(cfg)
        game_file_path = config["game_path"].replace('\\','/')
        steam_dir_path = config["steam_mod_path"].replace('\\','/')
except FileNotFoundError:
    raise RuntimeError("Missing config.json. Please create one with 'game_path' and 'steam_mod_path'.")

print(steam_dir_path)

# Get Documents Path from Windows
buffer = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH) #create buffer for path
ctypes.windll.shell32.SHGetFolderPathW(None, 0x0005 , None, None, buffer) # get path to buffer (CSIDL value = 0x0005)
documents_ck3_path :str = buffer.value.replace('\\','/') + '/Paradox Interactive/Crusader Kings III'

print(documents_ck3_path)

def open_file(path:str) -> any:
  with open(path, "r") as f:
    if(path.endswith(".json")):
      var = json.load(f)  # .json file as dictionary
    else:
      var = f.readlines() # Other file as list of lines
  f.close()
  return var

## --------------------------------------
## Add any additional exclusions from resolved_conflicts file
try:
  filename_exclusions:list[str] = open_file(f'{this_file_path+'/resolved_conflicts.txt'}')
except FileNotFoundError:
  filename_exclusions:list[str] = []
filename_exclusions = [exclusion.strip('\n') for exclusion in filename_exclusions]
print("Exclusions:", filename_exclusions)

## --------------------------------------
## Get Load Order and create Dictionary out of it to get names for conflicts
## --------------------------------------

load_order : dict[str, str] = open_file(f'{documents_ck3_path+'/dlc_load.json'}')["enabled_mods"]

mod_name_dict:dict[str, str] = {}  #mod_name_dict.keys() = .mod file should be unique, mod_name_dict.values() = Name

for local_mod_file in load_order:
  mod_descriptor = open_file((f'{documents_ck3_path+'/'+local_mod_file}'))

  for line in mod_descriptor:
    l = line.strip("\"\n")
    if line.startswith("name="):
      mod_name_dict[l[6:]] = (local_mod_file[:-4])
    if line.startswith("path="):
      mod_name_dict[l[6:]] = (local_mod_file[:-4])

#print(list(mod_name_dict.keys())[1])
#print(list(mod_name_dict.values())[1])

def flip_this_dict(dict_2_flip : dict) -> dict:
  flipped_dict = {}
  for key, value in dict_2_flip.items():
    if value in flipped_dict:
      flipped_dict[value].append(key) #Add to previous entry
    else:
      flipped_dict[value] = [key] #Create the entry if it doesn't exist
  return flipped_dict

mod_name_dict_flipped = flip_this_dict(mod_name_dict)
mod_name_dict.clear()
mod_name_dict[game_file_path] = 'Game'
for i in mod_name_dict_flipped.items():
  mod_name_dict[i[1][1]] = i[1][0]
mod_name_dict_flipped.clear()

if write_2_file:
    with open(f'{this_file_path+"/mod_name_dict.txt"}', 'w', encoding="utf-8") as f:
        f.write(json.dumps(mod_name_dict, indent=0, ensure_ascii=False))

## --------------------------------------
## Search all files from Setup Paths with the following extensions
## --------------------------------------

def make_files_list(path : str) -> dict[str,str]:
  file_list:dict[str,str] = {}
  for dirpath, _, files in os.walk(path):
    for file in files:
      if file.lower().endswith(file_extensions) : # only specified extensions
        if any(exclusions in file.lower() for exclusions in filename_exclusions) == False: # exclude specified filenames
          file_list[f'{(dirpath+'/'+file).replace('\\','/')}'] = file
  return(file_list)

## --------------------------------------
## add all files to dict, flip dict to extract duplicates
## --------------------------------------
all_files:dict[str, str] = {}
all_files.update(make_files_list(f'{documents_ck3_path+'/mod'}'))
all_files.update(make_files_list(game_file_path))
all_files.update(make_files_list(steam_dir_path))

flipped_files = flip_this_dict(all_files)
all_files.clear()

## Remove dupes
mods_conflicts:dict = {}
for key, value in flipped_files.items():
  if len(value)>1:
    mods_conflicts[key] = value
flipped_files.clear()

if write_2_file:
    with open(f'{this_file_path+"/mods_conflicts.txt"}', 'w', encoding="utf-8") as f:
        f.write(json.dumps(mods_conflicts, indent=0, ensure_ascii=False))

## --------------------------------------
## Add the Load order of the file to dict
## --------------------------------------

named_conflicts:dict = {}
for file_name,locations in mods_conflicts.items():
  for location in locations:
    for mod_location,mod_name in mod_name_dict.items():
      if location.startswith(mod_location):
        order = list(mod_name_dict.keys()).index(mod_location)
        
        if file_name in named_conflicts:
          named_conflicts[file_name].append((order,mod_name,location)) #Add to previous entry
        else:
          named_conflicts[file_name] = [(order,mod_name,location)] #Create the entry if it doesn't exist

for file_name,_ in named_conflicts.items():
  named_conflicts[file_name] = sorted(named_conflicts[file_name], key = lambda val: (val[0],val[2]))


## Extract only real conflicts (more than 1 mod involved)
final_conflicts:dict = {}
for key, value in named_conflicts.items():
  if len(value)>1 : # and key not in resolved_conflicts:
    final_conflicts[key] = value
named_conflicts.clear()



# --------------------------------------
# Print and save combined conflicts summary (mods vs mods + mods vs game)
# --------------------------------------

conflict_counts = {}          # track how many conflicts each mod has
conflict_partners = {}        # track which mods each one conflicts with
game_conflicts = {}           # track how many times each mod conflicts with Game
mod_order_index = {}         # track load order index for each mod
output_lines = []

# Build counts, partners, and game conflicts
for file_name, conflicts in final_conflicts.items():
    distinct_mods = set(mod_name for _, mod_name, _ in conflicts)

    # Skip if only one mod is involved (self-conflict)
    if len(distinct_mods) <= 1:
        continue

    for order, mod_name, location in conflicts:
        if mod_name == "Game":
            continue

        # Increment total conflict count once per file (not per entry)
        conflict_counts[mod_name] = conflict_counts.get(mod_name, 0) + 1

        # Track the lowest load order index for this mod
        if mod_name not in mod_order_index or order < mod_order_index[mod_name]:
            mod_order_index[mod_name] = order

        # If conflict includes Game, increment once per file
        if "Game" in distinct_mods:
            game_conflicts[mod_name] = game_conflicts.get(mod_name, 0) + 1

        # Track mod-to-mod partners (ignore Game)
        partners = [m for m in distinct_mods if m != mod_name and m != "Game"]
        if partners:
            if mod_name in conflict_partners:
                conflict_partners[mod_name].update(partners)
            else:
                conflict_partners[mod_name] = set(partners)

# Add combined summary section at the top
output_lines.append("=== Combined Conflict Summary ===")
for mod_name in sorted(conflict_counts.keys(), key=lambda m: mod_order_index.get(m, 9999)):
    partners = conflict_partners.get(mod_name, set())
    partners_list = ", ".join(sorted(partners)) if partners else "None"
    game_count = game_conflicts.get(mod_name, 0)

    # Skip mods that have no partners AND no game conflicts
    if len(partners) == 0 and game_count == 0:
        continue

    order_display = mod_order_index.get(mod_name, "?")
    output_lines.append(
        f"[{order_display}] {mod_name}: {conflict_counts[mod_name]} total conflicts "
        f"(Mod-to-Mod: {len(partners)} partners → {partners_list}; "
        f"With Game: {game_count})"
    )

# Then add detailed conflicts
output_lines.append("\n=== Detailed Conflicts ===\n")
for file_name, conflicts in final_conflicts.items():
    distinct_mods = set(mod_name for _, mod_name, _ in conflicts)

    # Skip if only one mod is involved (self-conflict)
    if len(distinct_mods) <= 1:
        continue

    output_lines.append(f"\nFile: {file_name}")
    # Sort entries by load order index (order)
    for order, mod_name, location in sorted(conflicts, key=lambda val: val[0]):
        output_lines.append(f"  - [{order}] {mod_name} ({location})")


# Print to console
print("\n".join(output_lines))

# Save to text file
summary_path = f"{this_file_path}/mod_conflict_summary.txt"
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"\nSummary saved to {summary_path}")