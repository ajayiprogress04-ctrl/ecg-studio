# ECG Studio — Standalone Windows application

A local Windows version of ECG Studio. Double-click the built executable, choose CSV recordings and an output folder, and split files using the original pandas algorithm. No Render, Vercel, Python installation, JupyterLab, cloud uploads or internet connection is required when using the built application.

**This ZIP contains the complete source and automated Windows build workflow. It does not contain a compiled executable.** The Windows build has not been run from this Linux workspace. The processing checks listed in TEST_REPORT.md passed here; Windows dialogs, the full local service and the packaged app still need the included Windows tests and a real Windows trial.

## Build the installer in your existing GitHub repository

1. Extract this complete source ZIP. It contains two top-level folders: `.github` and `ECG_Studio_Windows`.
2. Open https://github.com/ajayiprogress04-ctrl/ecg-studio . Upload/replace the `ECG_Studio_Windows` folder at repository root, preserving that folder name.
3. Replace the repository's TOP-LEVEL `.github/workflows/build-windows.yml` with the supplied top-level workflow. If GitHub's upload interface omits dotfolders, open the existing workflow, click Edit and paste the complete contents of the supplied file. Do not put the workflow only inside ECG_Studio_Windows.
4. Commit changes, open Actions, select Build ECG Studio for Windows and run the workflow if a run has not already started.
5. A successful Windows run tests the code, builds and smoke-tests the app, compiles the installer and publishes two artifacts. The Windows run has not been performed from this workspace.
6. Under Artifacts, download **ECG-Studio-Windows-Installer**. Extract the artifact ZIP to obtain **ECG_Studio_Setup_1.1.0.exe**.
7. Double-click that setup file. Follow the installation wizard and optionally select Create a desktop shortcut. Python/packages are included; no separate installation is required for the recipient.
8. Launch ECG Studio from the Start menu. Test a small recording and About the Developer. Your earlier output folders stay separate from the installation.
9. Share **ECG_Studio_Setup_1.1.0.exe** directly with other users. It is the single installer file; recipients do not need to assemble `_internal` folders. A configured public download link can be added after real publication.
10. To uninstall, close the running app and use Windows Settings → Apps → Installed apps → ECG Studio → Uninstall.

The portable alternative is still built as **ECG-Studio-Windows-Portable**. For that edition, extract the complete ZIP and keep ECG_Studio.exe beside its `_internal` folder. Do not confuse the portable ZIP with the new installer artifact.

The setup file is unsigned. A verified publisher signature requires a separate code-signing certificate and signing process. Follow your institution's software approval process; do not disable security protections. No repository visibility, public release, signing or deployment has been changed here.

GitHub's runner allowance and Actions policy apply to your account. See https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow and https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts .

## Use the app

1. **Choose CSV files** opens the Windows file picker; Ctrl/Shift select multiple files.
2. **Choose output folder** opens the Windows folder picker. Choose a location with enough free disk space.
3. **Split recordings** processes one recording at a time.
4. **Open output folder** reveals CSV segments saved directly on disk. No download or upload step is needed.
5. **Stop batch** stops at the next chunk callback; incomplete output for the current recording is removed, earlier completed outputs remain, and queued inputs are skipped.
6. **Close application** becomes available when processing has stopped. Closing just the browser tab does not stop the background local app. Keep the launcher window available so you can reopen its displayed local address if needed.

Each batch creates `ECG_Studio_<date>_<time>_<random>` inside your selected folder. Numbered recording folders keep identical input basenames separate. Completed files persist until you delete them yourself. `ECG_Studio_summary.json` records filenames, paths, row counts and states, without sample values. If a crash/power loss interrupts processing, `INCOMPLETE.txt` can remain; do not assume those files are complete. Rerun the original input into a fresh batch.

The theme preference is saved in `%LOCALAPPDATA%\ECG Studio\preferences.json` on Windows. Input selections and active batch state are session-only. This avoids storing private recording paths as persistent app preferences. The summary in your chosen output folder does contain local filenames/paths.

## Preserved processing behaviour

`backend/splitter.py` is copied unchanged from the previously tested ECG splitter. The supplied original remains in `reference/original_splitter.py`, and tests execute it as the oracle.

- Reads comma-separated CSV using pandas, with `comment='#'`, `skiprows=1`, `header=None`, three assigned columns and 100,000 rows per chunk.
- Strips timestamp whitespace, converts ECG raw/mV to numeric, parses `%Y-%m-%d %H:%M:%S.%f`, and drops rows with invalid/missing required values.
- Anchors six-hour windows to the first valid timestamp. Exact six-hour boundaries enter the next block. Keeps the final partial window, omits empty windows, and preserves negative block behaviour for earlier unsorted timestamps.
- No filtering, interpolation, resampling, timezone conversion or sorting.
- Output files `ECG_00h_to_06h.csv`, `ECG_06h_to_12h.csv`, etc. retain `timestamp`, `ecg_raw`, `ecg_mv`, `continuous_time`, `elapsed_time`, `block_number`.
- Original comment metadata is not retained. The header may count as a discarded row. The screenshot's abbreviated timestamp display is not used to reconstruct dates.
- Fresh output directories prevent duplicate cross-run appends and overwrites. Within one recording, the original chunk-append behaviour is preserved.

Recordings are read directly from disk. They are not copied into temporary upload storage. Outputs can be larger than inputs because the original script adds columns and serializes timestamps/timedeltas. The desktop admission estimate is six times the current input size plus 256 MiB reserve, followed by free-space checks during processing; it is conservative, not a guarantee. There is no arbitrary server upload cap, but disk, RAM, path limits and runtime determine practical capacity. Test a small representative recording before a multi-gigabyte batch.

## Project contents

| Path | Purpose |
| --- | --- |
| desktop/launcher.py | Starts a local-only server, opens the browser and manages shutdown |
| desktop/service.py | Windows file/folder pickers, batch worker, saved outputs, stop and open-folder actions |
| backend/splitter.py | Preserved pandas splitting implementation |
| frontend/ | Deep Light/OLED/Colour themes, local fonts, ECG branding and desktop controls |
| tests/test_processing.py | Byte-exact comparisons to the original script |
| tests/test_desktop.py | Desktop service/batch checks with mocked native dialogs |
| .github/workflows/build-windows.yml | Windows test/build/package workflow |
| requirements-windows.txt | Pinned runtime dependencies |
| WINDOWS_START_HERE.txt | Instructions included with the built executable |

The application uses a random loopback port and accepts API calls only from the local app using an in-memory token; host/origin checks prevent ordinary external pages from directing file operations. It makes no third-party requests. Native Windows dialogs run through Windows PowerShell using a fixed script; selected paths are returned as encoded JSON and never interpolated as shell commands. Powershell scripts and executable policies managed by your institution may block the native picker; report the error rather than weakening system policy.

## Developer local build (not required for ordinary users)

On Windows with Python 3.12 installed in a development environment:

```powershell
python -m pip install -r requirements-windows.txt pyinstaller==6.11.1
python -W ignore::ResourceWarning -m unittest discover -s tests -v
python -m desktop.launcher
```

To build:

```powershell
python -m PyInstaller --clean --noconfirm --onedir --paths . --name ECG_Studio --icon frontend/assets/icon.ico --add-data "frontend;frontend" desktop/launcher.py
```

Output is `dist/ECG_Studio/ECG_Studio.exe` plus its `_internal` folder. The Windows workflow runs `--self-test` against this bundle before publishing an artifact. Distribution includes Python/package components; retain their licence files and the bundled font licences. No code signing is included.

## A recording fails after the app opens

Check free space on the output drive first. The admission check is six times the selected input size plus 256 MiB; a 1,580 MiB recording needs about 9.5 GiB free under this conservative check. Choosing another folder on the same drive does not increase free space. Choose a different drive or free space, then retry. The check estimates capacity; it does not mean every recording produces that much output.

The updated desktop service reports a specific safe error category and, for capacity failures, actual available/required space. If you still see only the old “No output saved. Check the CSV/timestamp format, file access, or free disk space” message, replace the source with this update, run the Windows workflow and use the newly downloaded executable. Existing installed copies do not update automatically.

## About the Developer and installable distribution (v1.1.0)

About the Developer now uses Progress Ajayi's approved public profile from the reference app's about.js: physiologist/bioinformatician, First Class undergraduate Physiology qualification, Human Physiology master's with Distinction, and PhD in Molecular Biology and Genomics in progress. Relevant interests, portrait and published contact links are retained. The appendicitis-specific dedication and claims about statistical functions are not copied into ECG Studio. Source checked: https://appendicitis-learning-hub.vercel.app/about.js . Profile data is in frontend/developer.json and portrait assets are bundled locally. No live profile lookup occurs when the installed app runs.

The new top-level workflow in this source ZIP is intended for the existing `ajayiprogress04-ctrl/ecg-studio` repository with ECG_Studio_Windows at the root. Upload BOTH top-level folders: `.github` and `ECG_Studio_Windows`. The root `.github/workflows/build-windows.yml` replaces the earlier Windows workflow. Do not put this workflow only inside the application subfolder. The old standalone-repository workflow is omitted from this handover to avoid conflicting instructions.

The workflow builds two artifacts:

- ECG-Studio-Windows-Installer: contains ECG_Studio_Setup_1.1.0.exe, a single setup executable to share.
- ECG-Studio-Windows-Portable: optional ZIP retaining the earlier no-installation distribution.

The installer uses Inno Setup. It installs for the current user under LocalAppData/Programs/ECG Studio, adds Start-menu access, offers a desktop shortcut and registers an uninstaller. Python and packages are included. No administrator prompt is requested by the installer itself; institutional endpoint policy may still require software approval. Windows 10/11 64-bit is the intended target. Close ECG Studio before installing/upgrading/uninstalling; Setup checks a named application mutex rather than forcibly terminating processing. Its stable AppId supports installing later versions over the same application.

Uninstall removes installed application files; it does not intentionally remove user-selected recording/output folders or saved theme preferences. Never choose the installation folder as a research-data destination. Existing selected-output files remain on disk. Changes to code, profile or images require rebuilding and reinstalling. There is no automatic updater.

The executable and installer include ECG Studio branding, app version and Progress Ajayi as publisher metadata. They are unsigned: publisher metadata does not create a verified digital signature or Microsoft reputation. A trusted code-signing certificate and a signing step would be separate work. Neither a signed binary nor SmartScreen acceptance has been verified.

To share, distribute the generated setup .exe through your chosen file-sharing channel; never share the local 127.0.0.1 address. The new Share app dialog explains this. If you publish a real HTTPS installer download page, set download_url in frontend/developer.json and rebuild: Copy download link and Share download link then become available with a visible-copy fallback. No download address is invented, no repository visibility is changed, and nothing is published automatically. GitHub artifacts in a private repository require authorized access, so they are not universal public download links.

This workspace prepared the installer source/workflow; it did not build or install the Windows setup executable. After the Actions build passes, install it on Windows, verify its shortcuts and About panel, test a small recording, and verify uninstall leaves external output folders intact.
