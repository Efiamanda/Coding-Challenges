import subprocess
import sys
import unittest
from pathlib import Path
 
HERE = Path(__file__).parent
PARSER = HERE / "json_parser.py"
TESTS_DIR = HERE / "tests"
 
 
def expected_code(path):
    name = path.name.lower()
    if name.startswith(("valid", "pass")):
        return 0
    if name.startswith(("invalid", "fail")):
        return 1
    return None
 
 
class TestFiles(unittest.TestCase):
    def test_all_files(self):
        self.assertTrue(TESTS_DIR.is_dir(), f"Folder tidak ditemukan: {TESTS_DIR}")
        files = [p for p in sorted(TESTS_DIR.rglob("*.json")) if expected_code(p) is not None]
        self.assertTrue(files, "Tidak ada file valid*/invalid*/pass*/fail* di tests/")
 
        for path in files:
            with self.subTest(file=str(path.relative_to(TESTS_DIR))):
                result = subprocess.run([sys.executable, str(PARSER), str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, expected_code(path),
                                 f"Output program: {result.stdout.strip()}")
 
 
if __name__ == "__main__":
    unittest.main(verbosity=2)