# ECG Studio — Standalone Windows application

A local Windows version of ECG Studio. Double-click the built executable, choose CSV recordings and an output folder, and split files using the original pandas algorithm. No Render, Vercel, Python installation, JupyterLab, cloud uploads or internet connection is required when using the built application.

**This ZIP contains the complete source and automated Windows build workflow. It does not contain a compiled executable.** The Windows build has not been run from this Linux workspace. The processing checks listed in TEST_REPORT.md passed here; Windows dialogs, the full local service and the packaged app still need the included Windows tests and a real Windows trial.

## Get the Windows application without installing Python

1. Extract this source ZIP.
2. Create a new **private** GitHub repository named `ecg-studio-windows`. Keep the current web project separate; do not overwrite its repository or hosting configuration.
3. Upload the **contents inside ECG_Studio_Windows** into that new repository, not the parent folder and not the ZIP itself. At repository root, you should see `desktop`, `backend`, `frontend`, `tests`, `reference`, `requirements-windows.txt`, `WINDOWS_START_HERE.txt`, `README.md`, `TEST_REPORT.md`, and `App_Preferences.md`.
4. Include `.github/workflows/build-windows.yml`. If the upload interface skips `.github`, use **Add file → Create new file**, enter `.github/workflows/build-windows.yml` as the filename, paste the full contents of the supplied file, and commit. The complete workflow is included; no programming edits are necessary.
5. Open the repository's **Actions** tab. Select **Build ECG Studio for Windows**. If GitHub asks you to enable Actions for your repository, enable the included workflow. Click **Run workflow**, select your main branch, then **Run workflow** again. The workflow also runs automatically for relevant changes pushed to `main`.
6. Wait for a green successful run. It installs Python/packages on GitHub's Windows build machine, tests the source, builds ECG_Studio.exe, smoke-tests the bundled app, and creates the download. This does not install Python on your own computer.
7. Open the successful run. Under **Artifacts**, download **ECG-Studio-Windows-x64**. GitHub wraps this artifact in a ZIP; extract it to find `ECG_Studio_Windows.zip`. Extract that ZIP too.
8. Open the extracted `ECG_Studio` folder and double-click **ECG_Studio.exe**. Keep it together with the `_internal` folder. Create a shortcut if desired; do not move the executable out by itself.
9. Keep the launcher window open while processing. The interface opens in your default browser at a local 127.0.0.1 address. This is a local desktop application, not a hosted website. Use **Close application** to finish.

GitHub's standard runner allowance and Actions policy apply to your account; no cloud compute plan or ongoing hosting subscription is required by this app. No repository, workflow run, release, executable or deployment has been created on your account here. You can download artifacts only while signed in with repository read access. See https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow and https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts .

If the build fails, open the red run, open the failing step and share its error. Do not upload recordings as part of troubleshooting. If Windows blocks the unsigned build, follow your institution's software approval process; do not disable security protections.

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
