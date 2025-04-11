import os
import json
import logging

def repair_modpack_manifests():
    """Repair corrupted modpack manifests."""
    modpacks_dir = os.path.join("data", "modpacks")
    
    if not os.path.exists(modpacks_dir):
        print(f"Modpacks directory not found: {modpacks_dir}")
        return
        
    for modpack_id in os.listdir(modpacks_dir):
        modpack_dir = os.path.join(modpacks_dir, modpack_id)
        if not os.path.isdir(modpack_dir):
            continue
            
        manifest_path = os.path.join(modpack_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            print(f"No manifest for modpack {modpack_id}, skipping")
            continue
            
        try:
            # Try to read the manifest
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                print(f"Manifest for {modpack_id} is valid")
        except json.JSONDecodeError:
            print(f"Fixing corrupted manifest for {modpack_id}")
            
            # Create a default manifest
            default_manifest = {
                "id": modpack_id,
                "name": modpack_id.replace("_", " ").title(),
                "version": "1.0.0",
                "mc_versions": ["1.19.4"],
                "author": "Unknown",
                "description": "Recovered modpack",
                "loader_type": "forge",
                "mods": [],
                "config_files": [],
                "resource_packs": []
            }
            
            # Save the default manifest
            with open(manifest_path, 'w') as f:
                json.dump(default_manifest, f, indent=4)
                
            print(f"Created new default manifest for {modpack_id}")

# Create a small script to run this function
if __name__ == "__main__":
    repair_modpack_manifests()