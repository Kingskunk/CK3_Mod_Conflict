
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

game_file_path : str = input("Game Path = ")
if game_file_path == "":
  game_file_path = "G:/SteamLibrary/steamapps/common/Crusader Kings III/game"
game_file_path = game_file_path.replace('\\','/')
print(game_file_path)

steam_dir_path : str = input("Steam Mod Path = ")
if steam_dir_path == "":
  steam_dir_path = "G:/SteamLibrary/steamapps/workshop/content/1158310"
  
steam_dir_path = steam_dir_path.replace('\\','/')
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
  with open(f'{this_file_path+'/mod_name_dict.txt'}', 'w') as f:
    f.write((json.dumps(mod_name_dict,indent=0,ensure_ascii=False)))

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
  with open(f'{this_file_path+'/mods_conflicts.txt'}', 'w') as f:
    f.write((json.dumps(mods_conflicts,indent=0,ensure_ascii=False)))

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


#print(named_conflicts)

with open(f'{this_file_path+'/final_conflicts.txt'}', 'w') as f:
  f.write((json.dumps(final_conflicts,indent=2,ensure_ascii=False)))
