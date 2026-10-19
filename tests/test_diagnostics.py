import unittest
from desktop.diagnostics import describe_failure,InsufficientSpace,NoValidRows
class Diagnostics(unittest.TestCase):
 def test_disk_shortage_reports_real_sizes(self):
  result=describe_failure(InsufficientSpace(10*1024**3,2*1024**3,'before processing'))
  self.assertEqual(result['error_code'],'insufficient_disk_space')
  self.assertIn('2.00 GiB',result['message']);self.assertIn('10.00 GiB',result['message'])
 def test_no_valid_rows(self):self.assertEqual(describe_failure(NoValidRows())['error_code'],'no_valid_rows')
 def test_file_errors(self):
  self.assertEqual(describe_failure(PermissionError('private'))['error_code'],'file_permission')
  self.assertEqual(describe_failure(FileNotFoundError('private'))['error_code'],'file_missing')
 def test_encoding(self):
  self.assertEqual(describe_failure(UnicodeDecodeError('utf8',b'\xff',0,1,'invalid'))['error_code'],'text_encoding')
 def test_raw_exception_never_exposed(self):
  for error in (ValueError('PRIVATE_ECG_VALUE'),type('ParserError',(ValueError,),{})('PRIVATE_ECG_VALUE')):
   self.assertNotIn('PRIVATE_ECG_VALUE',str(describe_failure(error)))
 def test_full_disk_and_memory(self):
  self.assertEqual(describe_failure(OSError(28,'private'))['error_code'],'disk_full')
  self.assertEqual(describe_failure(MemoryError())['error_code'],'memory')
