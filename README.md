# CK3_Mod_Conflict
A python based Crusader Kings 3 (CK3) Mod conflict detector that outputs which file is overwritten by the mods based on load order

## ⚠️ Important Instructions

- **Launch the game launcher once before running this script!**  
  This ensures the `dlc_load.json` file and mod descriptors are up to date.

- **Remove mods from the load order if their files have been deleted!**  
  Stale entries in `dlc_load.json` will cause errors when the script tries to parse missing mods.

- **Avoid mods with the exact same name.**  
  Duplicate names will cause conflicts in the summary output and may lead to incorrect reporting.

  ## ⚙️ Config File Instructions

This project includes a `config.json` file.  
You **must edit this file** to add your own installation details before running the script.

### Steps
1. Open the `config.json` file in a text editor.
2. Replace the example paths with the correct ones for your system:
   - **`game_path`** → Path to your Crusader Kings III **game folder**.  
     Example: `C:/Program Files (x86)/Steam/steamapps/common/Crusader Kings III/game`
   - **`steam_mod_path`** → Path to your CK3 **Steam Workshop mods folder**.  
     Example: `C:/Program Files (x86)/Steam/steamapps/workshop/content/1158310`
3. Save the file.
