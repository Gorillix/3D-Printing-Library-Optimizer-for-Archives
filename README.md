# 3D-Printing-Library-Optimizer-for-Archives

This utility manages large-scale 3D printing libraries by automating decompression, deduplication, and archival processes. It ensures data integrity through MD5 verification and optimizes physical storage via hardlinking.

This pipeline is designed to take a messy 3D printing library (full of zips, duplicates, and nested folders) and turn it into a clean, deduplicated, and searchable archive.

## ✨ Features

1.  **Unpack & Mirror**: Automatically extracts archives and moves the original zips to a safety redundant folder.
2.  **Flattening**: Detects and removes "Double Nesting" (e.g., `Folder/Folder/file.stl` becomes `Folder/file.stl`).
3.  **DNA Hashing**: Scans every file to identify identical models, even if they have different names.
4.  **Hardlink Dedupe**: Replaces duplicate files with **Hard Links**, saving GBs of space without breaking your existing folder structure.
5.  **Inventory Map**: Generates a categorized text file so you can find models instantly without opening a massive 7z archive.

## 🚀 Setup

1.  **Install Python**: Ensure Python 3.8+ is installed.
2.  **Install 7-Zip**: The script uses the 7-Zip executable for extraction.
3.  **Configure**: Edit `config.json` with your own paths.
    * `SEARCH_ROOT`: Where your files are currently stored.
    * `REDUN_ROOT`: Where the original archives will be moved for safety.
    * `PRIORITY_ROOTS`: Folders you want to keep as the "Originals" (e.g., your cleaned/sorted folders).
4.  **Dry Run**: Keep `DRY_RUN_CLEANUP` and `DRY_RUN_LINKING` as `true` for the first run to verify the output in the log.
5.  **Execute**: Open a terminal as **Administrator** and run:
    ```bash
    python omni_archive_pro.py
    ```

## 📦 Post-Processing
After the script finishes, use 7-Zip to compress your cleaned `SEARCH_ROOT` into a **Solid 7z Archive** with **Ultra** settings for maximum storage efficiency.

### Recommended 7z Settings:
* **Compression Level:** Ultra
* **Dictionary Size:** 512 MB (for 32GB RAM)
* **Solid Block Size:** 4 GB
* **Threads:** Max (e.g., 14)

---

**Note:** Always run as Administrator on Windows to ensure the script has permissions to create hard links.
