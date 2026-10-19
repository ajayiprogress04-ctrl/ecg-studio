"""Useful failures without exposing raw recording rows or parser exception text."""
class InsufficientSpace(OSError):
    def __init__(self, required, available, phase):
        super().__init__('insufficient output disk space')
        self.required=required
        self.available=available
        self.phase=phase

class NoValidRows(ValueError):pass

def describe_failure(error):
    kind=type(error).__name__
    info={'error_type':kind}
    if isinstance(error,InsufficientSpace):
        info.update(error_code='insufficient_disk_space',required_free_bytes=error.required,
                    available_free_bytes=error.available,
                    message=f'Not enough free space on the output drive {error.phase}. Available: {error.available/1024**3:.2f} GiB; required by the app\'s safety check: {error.required/1024**3:.2f} GiB. Choose an output folder on a drive with more free space, or free space and retry. Originals were not changed.')
    elif isinstance(error,NoValidRows):
        info.update(error_code='no_valid_rows',message='No valid ECG rows remained after the original cleaning rules. Check for comma-separated columns, full date-and-time timestamps, and numeric ECG raw/mV values. Expected timestamp example: 2026-06-18 08:52:24.000. No signal values were changed.')
    elif isinstance(error,PermissionError):
        info.update(error_code='file_permission',message='Windows denied file access. Check read access to the recording and write access to the output folder. If another program locks the file, close it and retry.')
    elif isinstance(error,FileNotFoundError):
        info.update(error_code='file_missing',message='The recording or destination is no longer available. Reconnect the drive if necessary, choose the files and output folder again, then retry.')
    elif isinstance(error,UnicodeDecodeError):
        info.update(error_code='text_encoding',message='The CSV could not be decoded with the original reader\'s default UTF-8 encoding. Export a UTF-8 CSV or provide a small de-identified text sample so the encoding can be checked. The app has not silently changed the encoding.')
    elif isinstance(error,MemoryError):
        info.update(error_code='memory',message='The process ran out of memory. Close other memory-intensive applications and retry. The app reads in chunks; unusually large rows or limited available RAM can still cause this failure.')
    elif kind in ('ParserError','EmptyDataError'):
        info.update(error_code='csv_structure',message='The original CSV reader could not parse the file structure. Check for a comma-separated export with the expected three columns. Parser details containing recording values have been omitted.')
    elif isinstance(error,OSError) and (getattr(error,'errno',None)==28 or getattr(error,'winerror',None)==112):
        info.update(error_code='disk_full',message='The output drive became full while saving. Free disk space or choose another drive, then retry. The current incomplete output was removed where possible.')
    elif isinstance(error,OSError):
        info.update(error_code='file_io',message='A file read/write operation failed. Check that the drive is connected, paths are accessible, and sufficient output space remains. Try a short local output path if needed.')
    else:
        info.update(error_code='processing_error',message=f'Processing failed ({kind}). Share this error type and whether any chunks were processed; do not share patient data. No complete output was saved for this recording.')
    return info
