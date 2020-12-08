from   pathlib    import Path
import pytest
from   lineinfile import remove_lines_from_file, remove_lines_from_string

CASES_DIR = Path(__file__).with_name('data') / 'remove_lines'

INPUT = (CASES_DIR / 'input.txt').read_text()

def gentestcases():
    for cfgfile in sorted(CASES_DIR.glob("*.py")):
        cfg = {}
        exec(cfgfile.read_text(), cfg)
        try:
            input_file = cfg["input_file"]
        except KeyError:
            source = INPUT
        else:
            with (CASES_DIR / input_file).open(newline='') as fp:
                source = fp.read()
        with cfgfile.with_suffix('.txt').open(newline='') as fp:
            output = fp.read()
        yield pytest.param(
            source, cfg["regexp"], output,
            id=cfgfile.with_suffix('').name,
        )

def listdir(dirpath):
    return sorted(p.name for p in dirpath.iterdir())

TEST_CASES = list(gentestcases())

@pytest.mark.parametrize('source,regexp,output', TEST_CASES)
def test_remove_lines_from_string(source, regexp, output):
    assert remove_lines_from_string(source, regexp) == output

@pytest.mark.parametrize('source,regexp,output', TEST_CASES)
def test_remove_lines_from_file(source, regexp, output, tmp_path):
    thefile = tmp_path / "file.txt"
    thefile.write_text(source)
    assert remove_lines_from_file(thefile, regexp) == (source != output)
    assert listdir(tmp_path) == ["file.txt"]
    assert thefile.read_text() == output
