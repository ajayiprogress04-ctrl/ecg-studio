# ECG Studio Windows verification report

## Actually performed here

- Five processing tests passed using Python 3.12 and pandas 2.2.3. They execute the unchanged original script and compare output filenames and complete CSV bytes against backend/splitter.py.
- Fixtures cover six-hour boundaries, invalid rows, a 100,007-row recording crossing chunk boundaries, gaps, earlier unsorted timestamps, entirely invalid rows, and rejection of an existing output folder.
- Python source compiled successfully; frontend/desktop.js passed Node syntax checking.
- Desktop assets and the Windows icon were packaged from the established ECG Studio design.

## Included checks not executed here

The Windows workflow runs the five processing tests plus desktop service tests for authentication/host/origin checks, required choices, cancelled picker, direct-file batch success/failure, original preservation, fresh destinations, folder opening, clear/quit, stopping an active batch and insufficient disk space. Native dialogs are mocked in those service tests. It also builds the Windows executable and runs its synthetic --self-test for bundled imports, sample processing, HTML and icon availability.

Flask/Waitress could not be installed from the package index in this workspace, so the desktop service tests and HTTP launcher were not run here. A Windows interpreter/runtime could not be downloaded here, and this Linux workspace has not produced or executed a Windows binary. The automatic Windows workflow has not been run on the user's GitHub account. No compiled executable is included in this source ZIP.

## Remaining Windows acceptance checks

After a successful Actions build: extract the complete app bundle; launch ECG_Studio.exe; verify native file/folder dialogs, all themes, keyboard navigation, open-folder actions, stop and clean shutdown. Test an invalid recording mixed with a valid recording, identical basenames in different folders, paths with spaces/non-ASCII characters, and re-running the same inputs. Confirm existing outputs and original recordings remain intact. Then compare a real representative recording with the original script before using large batches. No actual ECG input was supplied, so real-file compatibility, processing throughput, peak memory and multi-gigabyte reliability remain unverified.

The local workflow preserves the original cleaning/segmentation, replaces cloud uploads with direct local file reads, adds permanent user-chosen output storage, and uses fresh folders to prevent duplicate cross-run appends. No diagnostic interpretation or signal modification was added.
