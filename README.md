# CK3_Mod_Conflict
A python based Crusader Kings 3 (CK3) Mod conflict detector that outputs which file is overwritten by the mods based on load order

## ⚠️ Important Instructions

- **Launch the game launcher once before running this script!**  
  This ensures the `dlc_load.json` file and mod descriptors are up to date.

- **Remove mods from the load order if their files have been deleted!**  
  Stale entries in `dlc_load.json` will cause errors when the script tries to parse missing mods.

- **Avoid mods with the exact same name.**  
  Duplicate names will cause conflicts in the summary output and may lead to incorrect reporting.
