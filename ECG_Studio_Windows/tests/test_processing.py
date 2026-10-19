import contextlib
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
import pandas as pd
from backend.splitter import split_ecg
REFERENCE = Path(__file__).resolve().parents[1]/'reference/original_splitter.py'
class Equivalence(unittest.TestCase):
    def compare(self, text):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'example.csv').write_text(text);old=Path.cwd()
            try:
                os.chdir(root)
                with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(REFERENCE))
            finally:os.chdir(old)
            result=split_ecg(root/'example.csv',root/'actual')
            expected={f.name:f.read_bytes() for f in (root/'ecg_subsets').glob('*.csv')}
            actual={f.name:f.read_bytes() for f in (root/'actual').glob('*.csv')}
            self.assertEqual(expected,actual)
            return result,actual
    def test_boundaries_and_cleaning(self):
        r,o=self.compare('# exported\n# sampling 256Hz\nlocal_time,ecg,ecg_mV\n2026-06-18 08:52:24.000,10,0.1\n2026-06-18 14:52:23.999,11,0.2\n2026-06-18 14:52:24.000,12,0.3\n2026-06-18 20:52:24.000,13,0.4\nbad,14,0.5\n2026-06-18 21:52:24.000,not-a-number,0.5\n')
        self.assertEqual(r['valid_rows'],4);self.assertEqual([x['rows'] for x in r['outputs']],[2,1,1]);self.assertEqual(len(o),3)
    def test_multiple_chunks(self):
        times=pd.date_range('2026-01-01',periods=100_007,freq='s')
        text='local_time,ecg,ecg_mV\n'+''.join(f'{t:%Y-%m-%d %H:%M:%S}.000,{i%123},{(i%10)/10}\n' for i,t in enumerate(times))
        r,_=self.compare(text);self.assertEqual(r['valid_rows'],100_007)
    def test_unsorted_and_gap(self):
        r,_=self.compare('local_time,ecg,ecg_mV\n2026-01-02 00:00:00.000,1,0.1\n2026-01-01 23:00:00.000,2,0.2\n2026-01-03 01:00:00.000,3,0.3\n');self.assertEqual(len(r['outputs']),3)
    def test_all_invalid(self):
        r,o=self.compare('local_time,ecg,ecg_mV\n52:24.0,1,0.1\ninvalid,2,0.2\n');self.assertEqual(r['valid_rows'],0);self.assertEqual(o,{})
    def test_fresh_output_only(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError):split_ecg('unused.csv',temp)
