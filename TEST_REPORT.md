# Verification report

## Automated checks actually performed

Python 3.12; pandas 2.2.3; Flask 3.1.2. Synthetic input is generated during tests; no real ECG data is included.

Processing comparisons execute the unchanged supplied script in an isolated temporary working directory, then execute `backend/splitter.py` on the same bytes. Output filenames and complete CSV bytes are compared exactly, covering serialized signal values, column ordering, timestamps, elapsed time and block numbers.

| Case | Check |
| --- | --- |
| Six-hour boundaries | Samples immediately before, exactly at six hours, and exactly at twelve hours; final partial window |
| Invalid rows | Invalid timestamp and nonnumeric signal discarded; header/comment behaviour preserved |
| Multiple chunks | 100,007 valid rows cross the 100,000-row reader boundary without duplication or loss |
| Gaps and unsorted times | Empty windows omitted; earlier timestamps retain original negative-block behaviour |
| Entirely invalid input | Reference and new processor both produce no CSVs; API reports failure |
| Fresh output folder | Existing destination rejected instead of appending old results |
| Job API | Chunk upload, offset mismatch, premature start, background completion, ZIP content, invalid download, deletion |
| Same input filename | Separate job IDs and isolation between job tokens |
| Validation | Empty input, unsupported extension and over-limit file rejected |
| Expiry and access | Abandoned upload expiry; invalid job token blocked; allowed CORS origin only |
| Failure cleanup | Failed recording input removed |

Result: **10 automated tests passed**. JavaScript syntax checked with `node --check frontend/app.js`.

The original script produces ResourceWarnings because its summary opens files without explicit closing. The comparison tests can suppress these warnings; the reference source remains unchanged.

## Differences deliberately introduced

Fresh per-recording jobs prevent duplicate output appends across runs, as approved. The web layer adds bounded uploads, queue/status, ZIP creation, failure reporting, input cleanup and output expiry. All-invalid input is a visible failed job. These operational changes do not replace segmentation or signal transformations.

## Not verified

No representative actual CSV/output file was provided. Exact real-export timestamp bytes and delimiters remain inferred from the working code and screenshot. No claim is made that spreadsheet-displayed `52:24.0` itself is a parseable full timestamp. No real-recording, multi-gigabyte, throughput, peak-memory, browser automation, visual QA, mobile, deployed-host, proxy or HTTPS transfer tests were performed. Synthetic byte equality only establishes equivalence for the tested fixtures with the pinned runtime.

No GitHub or hosting deployment has been performed. Follow README.md to deploy and complete the listed acceptance checks.

## Branding and sharing update

Applied the attached App_Preferences(3).md to the ECG processing interface. Inspected the live reference app HTML and CSS for its locally loaded Source Sans 3/Cormorant Garamond typography and ruby/bronze/navy/green roles. Added richer palettes in all themes, visible Quick guide/Share app/Copy link controls, native dialogs, an ECG emblem, PNG favicons/touch icon and a 1200 × 630 PNG sharing card. Processing code is unchanged.

JavaScript syntax checks and six simulated sharing/guide checks passed: direct copy, denied/unavailable clipboard fallback, native sharing, cancellation, clean local fallback and opening the quick guide. Palette text/button contrast pairs were calculated against the token surfaces. Production build was exercised with a reserved example origin; this is a test input, not a claimed deployed domain. Static output contains absolute canonical/Open Graph/card URLs and local branding/font assets. Actual Vercel deployment, mobile layout, native share dialogs, clipboard permission prompts and social-platform previews remain untested.

## Deeper themes and connection correction

Deepened backgrounds, surfaces and actions in all themes. Minimum tested text-token contrast ratios: Light 4.65:1, OLED 7.44:1, Colour 8.51:1. These calculations exclude antialiasing, disabled controls and the darker ends of action gradients; they are not a full accessibility audit.

Six new simulated connection checks passed: missing hosted configuration, rejection of localhost on a hosted page, rejection of insecure remote HTTP, HTTPS origin normalization, valid synthetic health response, and localhost fallback only in local preview. The six existing simulated sharing/guide checks also passed. JavaScript syntax and a production build without ECG_API_URL passed; the built config correctly remains null instead of leaking localhost.

The Python processing and API source were unchanged in this update; their ten passing tests from the prior update remain applicable. A real Python backend has not been deployed or connected by this work. Screenshot confirms a connection failure before upload but cannot establish whether the deployed URL, network, CORS or an absent service caused it. No claim is made that the user's live failure has been resolved before configuring and testing the actual backend.
