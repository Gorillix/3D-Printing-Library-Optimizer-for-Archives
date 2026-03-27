import os
import json
import subprocess
import hashlib
import sys
import signal
import shutil
import uuid
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

# --- CONFIGURATION LOADER ---
# Loads environment-specific paths from an external JSON file
# to ensure the script remains portable and shareable.
def load_config():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found. Please create it based on the README.")
        sys.exit(1)
    with open(config_path, 'r') as f:
        return json.load(f)

CFG = load_config()

# Initialization of constants and path variables from the config
EXE_7Z = CFG["EXE_7Z"]
MANIFEST_PATH = CFG["MANIFEST_PATH"]
SEARCH_ROOT = CFG["SEARCH_ROOT"]
REDUN_ROOT = CFG["REDUN_ROOT"]
INVENTORY_PATH = CFG["INVENTORY_PATH"]
PRIORITY_ROOTS = [os.path.normpath(p).lower() for p in CFG["PRIORITY_ROOTS"]]

# Defined extensions for 3D printing files and common archive types
WHITELIST = ('.stl', '.3mf', '.obj', '.lys', '.ctb', '.chitubox', '.slc', '.jpg', '.jpeg', '.png', '.webp', '.pdf', '.txt', '.md')
ARCHIVE_EXTS = ('.zip', '.7z', '.rar')

# Processing settings
MAX_WORKERS = CFG.get("MAX_WORKERS", 4)
BUFFER_SIZE = 1048576 
DRY_RUN_CLEANUP = CFG.get("DRY_RUN_CLEANUP", True)
DRY_RUN_LINKING = CFG.get("DRY_RUN_LINKING", True)
INTERRUPTED = False

# Global statistics tracker
stats = {"archives_moved": 0, "archive_bytes_shifted": 0, "links_created": 0, "link_bytes_saved": 0, "unique_dna": 0}

def log(msg):
    t = datetime.now().strftime('%H:%M:%S')
    print(f"[{t}] {msg}")

def signal_handler(sig, frame):
    global INTERRUPTED
    log("!!! Interrupt received. Graceful exit initiated...")
    INTERRUPTED = True

signal.signal(signal.SIGINT, signal_handler)

def long_p(path):
    # Appends the Windows long path prefix to bypass the 260 character limit.
    if os.name == 'nt' and not path.startswith("\\\\?\\"):
        return f"\\\\?\\{os.path.normpath(path)}"
    return path

def get_hash(fname):
    # Generates an MD5 hash of the file content for bit-for-bit comparison.
    h = hashlib.md5()
    try:
        with open(long_p(fname), "rb") as f:
            for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
                h.update(chunk)
        return h.hexdigest()
    except: return None

def flatten_nested(path):
    # Removes redundant subfolders created by some archive tools 
    # (e.g., Folder.zip/Folder/file.stl -> Folder/file.stl).
    try:
        items = os.listdir(long_p(path))
        if len(items) == 1:
            sub = os.path.join(path, items[0])
            if os.path.isdir(long_p(sub)):
                log(f"Flattening nested folder: {items[0]}")
                if not DRY_RUN_CLEANUP:
                    for item in os.listdir(long_p(sub)):
                        shutil.move(long_p(os.path.join(sub, item)), long_p(path))
                    os.rmdir(long_p(sub))
                return True
    except: pass
    return False

def calculate_md5_worker(fname):
    # Worker function for parallel processing of file hashes.
    h = get_hash(fname)
    size = os.path.getsize(long_p(fname)) if h else 0
    return fname, h, size

def run_pipeline():
    global INTERRUPTED
    log("--- OMNI ARCHIVE PIPELINE STARTING ---")

    # PHASE 1: UNPACK & MIRROR
    # Extracts compressed archives and moves the originals to the safety redundant path.
    log("PHASE 1: UNPACKING & SAFETY MIRRORING")
    archives = [os.path.join(r, f) for r, _, files in os.walk(SEARCH_ROOT) for f in files if f.lower().endswith(ARCHIVE_EXTS)]
    
    for arc in archives:
        if INTERRUPTED: break
        pkg_folder = os.path.join(os.path.dirname(arc), f"pkg_{os.path.basename(arc)}")
        
        if not os.path.exists(long_p(pkg_folder)):
            if not DRY_RUN_CLEANUP:
                try:
                    subprocess.run([EXE_7Z, "x", arc, f"-o{pkg_folder}", "-y"], stdout=subprocess.DEVNULL, check=True)
                    flatten_nested(pkg_folder)
                except: continue
            else: log(f"[DRY RUN] Would unpack: {os.path.basename(arc)}")

        if not DRY_RUN_CLEANUP:
            rel_path = os.path.relpath(os.path.dirname(arc), SEARCH_ROOT)
            target_dir = os.path.join(REDUN_ROOT, rel_path)
            os.makedirs(long_p(target_dir), exist_ok=True)
            target_file = os.path.join(target_dir, os.path.basename(arc))
            
            s_hash = get_hash(arc)
            if os.path.exists(long_p(target_file)) and s_hash == get_hash(target_file):
                os.remove(long_p(arc))
            else:
                if os.path.exists(long_p(target_file)):
                    target_file = target_file.replace(".", f"_{uuid.uuid4().hex[:4]}.")
                shutil.move(long_p(arc), long_p(target_file))
            stats["archives_moved"] += 1

# PHASE 2: FOLDER NORMALIZATION
    log("\nPHASE 2: FOLDER NORMALIZATION")
    for root, dirs, _ in os.walk(SEARCH_ROOT):
        # We process folders starting with the 'pkg_' prefix
        for d in [d for d in dirs if d.startswith("pkg_")]:
            pkg_path = os.path.join(root, d)
            clean_name = d.replace("pkg_", "")
            for ext in ARCHIVE_EXTS: 
                clean_name = clean_name.replace(ext, "").replace(ext.upper(), "")
            
            clean_path = os.path.join(root, clean_name)
            
            if not DRY_RUN_CLEANUP:
                if not os.path.exists(long_p(clean_path)):
                    try: 
                        os.rename(long_p(pkg_path), long_p(clean_path))
                        log(f"[LIVE] Renamed: {d} -> {clean_name}")
                    except Exception as e:
                        log(f"[ERROR] Renaming {d}: {e}")
                else:
                    log(f"[NOTICE] Clean folder already exists for {d}. Skipping.")
            else:
                # This only prints if DRY_RUN_CLEANUP is actually True
                log(f"[SIMULATED] Rename: {d} -> {clean_name}")

    # PHASE 3: HASHING
    # Creates a global manifest mapping MD5 hashes to file paths for deduplication.
    log("PHASE 3: GENERATING DNA MANIFEST")
    manifest = {}
    to_hash = [os.path.join(r, f) for r, _, files in os.walk(SEARCH_ROOT) if REDUN_ROOT not in r for f in files if f.lower().endswith(WHITELIST)]
    
    if to_hash:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for path, f_hash, f_size in executor.map(calculate_md5_worker, to_hash):
                if INTERRUPTED: break
                if f_hash:
                    if f_hash not in manifest: manifest[f_hash] = []
                    manifest[f_hash].append(path)
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f: json.dump(manifest, f, indent=4)
        stats["unique_dna"] = len(manifest)

    # PHASE 4: DEDUPLICATION
    # Replaces duplicate files with hard links to reclaim storage while preserving paths.
    log("PHASE 4: HARDLINK DEDUPLICATION")
    for paths in [p for p in manifest.values() if len(p) > 1]:
        prioritized = []
        others = []
        for p in paths:
            np = os.path.normpath(p).lower()
            if any(np.startswith(root) for root in PRIORITY_ROOTS): prioritized.append(p)
            else: others.append(p)
        
        anchor = prioritized[0] if prioritized else others[0]
        for p in paths:
            if p == anchor: continue
            try:
                # Verifies if the file is already a hard link to the same data block.
                if os.stat(long_p(p)).st_ino == os.stat(long_p(anchor)).st_ino: continue
                if not DRY_RUN_LINKING:
                    os.remove(long_p(p))
                    os.link(long_p(anchor), long_p(p))
                stats["links_created"] += 1
                stats["link_bytes_saved"] += os.path.getsize(long_p(anchor))
            except: pass

    # PHASE 5: INVENTORY
    # Generates a categorized text document to allow for searching without archive access.
    log("PHASE 5: WRITING INVENTORY")
    with open(INVENTORY_PATH, 'w', encoding='utf-8') as f:
        f.write(f"LIBRARY INVENTORY - {datetime.now().strftime('%Y-%m-%d')}\n\n")
        for h, paths in manifest.items():
            f.write(f"ID: {h}\n")
            for p in paths: f.write(f"  > {p}\n")
            f.write("\n")

    log("--- FINISHED ---")
    log(f"DNA Signatures: {stats['unique_dna']}")
    log(f"Space Reclaimed: {stats['link_bytes_saved'] / (1024**3):.2f} GB")

if __name__ == "__main__":
    run_pipeline()
