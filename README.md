# 3D-Printing-Library-Optimizer-for-Archives
This utility manages large scale 3D printing libraries by automating decompression, deduplication, and archival processes. It ensures data integrity through MD5 verification and optimizes physical storage via hardlinking.

Project Documentation
Managing a growing collection of 3D models can quickly lead to storage exhaustion and organizational chaos. This tool provides a professional pipeline to transition a library from raw archives into a clean, searchable, and storage-efficient state.

System Requirements
Before utilizing the optimizer, ensure the following prerequisites are met:

Python 3.8 or higher installed on the system.

7-Zip installed at the default directory or a known custom path.

Administrative privileges for the terminal to allow for Hard Link creation.

Sufficient storage space on the target volume for the expanded data (the "DNA").

Configuration Procedures
The utility relies on a configuration file to define environment variables without requiring code modifications.

Create a file named config.json in the root directory of the script.

Input the path to the 7-Zip executable in the EXE_7Z field.

Define the SEARCH_ROOT as the directory containing the files to be processed.

Set the REDUN_ROOT to a separate path or drive intended for the safety backup of original archives.

List folders in the PRIORITY_ROOTS array to establish which directories should be treated as the "Master" locations during deduplication.

Verify that DRY_RUN_CLEANUP and DRY_RUN_LINKING are set to true for initial testing.

Save the config.json file.

Execution Sequence
Follow these steps to perform the optimization pipeline:

Open a terminal or PowerShell window as Administrator.

Navigate to the directory containing the script.

Execute the command python omni_archive_pro.py.

Review the omni_final.log to inspect simulated changes and confirm path accuracy.

Modify the config.json to set the dry run variables to false once the log is verified.

Run the script again to finalize the library modifications.
