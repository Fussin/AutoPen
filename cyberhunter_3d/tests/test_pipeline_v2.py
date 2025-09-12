import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from cyberhunter_3d.core.reconnaissance.merger import merge_and_dedupe, bulk_check_liveness
from cyberhunter_3d.core.reconnaissance.enumerator_runner import run_enumerators

@pytest.fixture
def temp_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_merge_and_dedupe(temp_output_dir):
    # Create some dummy output files
    file1_path = os.path.join(temp_output_dir, "file1.txt")
    with open(file1_path, "w") as f:
        f.write("sub1.example.com\n")
        f.write("sub2.example.com\n")

    file2_path = os.path.join(temp_output_dir, "file2.txt")
    with open(file2_path, "w") as f:
        f.write("sub2.example.com\n")
        f.write("sub3.example.com\n")

    # Test the merge_and_dedupe function
    source_files = [file1_path, file2_path]
    result = merge_and_dedupe(source_files)

    assert result == {"sub1.example.com", "sub2.example.com", "sub3.example.com"}

@pytest.mark.asyncio
async def test_run_enumerators(temp_output_dir):
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        # Mock the subprocess call
        async def mock_communicate():
            return (b'sub1.example.com\n', b'')

        mock_proc = MagicMock()
        mock_proc.communicate = mock_communicate
        mock_proc.returncode = 0
        mock_subprocess.return_value = mock_proc

        # Define some dummy tools
        tools = [
            {"name": "tool1", "cmd": "echo 'sub1.example.com'"},
            {"name": "tool2", "cmd": "echo 'sub2.example.com'"},
        ]

        # Test the run_enumerators function
        output_paths = await run_enumerators("example.com", tools, temp_output_dir)

        # Check that the output files were created
        assert len(output_paths) == 2
        for path in output_paths:
            assert os.path.exists(path)

        # Check that the subprocess was called correctly
        assert mock_subprocess.call_count == 2
