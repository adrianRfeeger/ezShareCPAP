import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import file_ops


class FakeResponse:
    def __init__(self, chunks):
        self.chunks = chunks
        self.headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield from self.chunks


class FakeTempFile:
    def __init__(self, directory):
        self.closed = False
        self._file = tempfile.NamedTemporaryFile(delete=False, dir=directory)
        self.name = self._file.name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def write(self, data):
        return self._file.write(data)

    def flush(self):
        return self._file.flush()

    def fileno(self):
        return self._file.fileno()

    def close(self):
        self.closed = True
        return self._file.close()


def ezshare_for(response, retries=1, running=True):
    return SimpleNamespace(
        retries=retries,
        connection_delay=0,
        _is_running=running,
        session=SimpleNamespace(get=lambda *args, **kwargs: response),
    )


class DownloadFileTests(unittest.TestCase):
    def test_replaces_temp_file_after_temp_handle_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_temp = FakeTempFile(directory)
            target = pathlib.Path(directory) / "STR.EDF"
            ezshare = ezshare_for(FakeResponse([b"edf-data"]))

            def named_temp_file(**kwargs):
                self.assertEqual(pathlib.Path(kwargs["dir"]), target.parent)
                return fake_temp

            def replace_after_close(source, destination):
                self.assertEqual(source, pathlib.Path(fake_temp.name))
                self.assertEqual(destination, target)
                self.assertTrue(fake_temp.closed)

            with patch("file_ops.NamedTemporaryFile", side_effect=named_temp_file), \
                    patch.object(pathlib.Path, "replace", autospec=True, side_effect=replace_after_close) as replace:
                self.assertTrue(file_ops.download_file(ezshare, "http://example.test/STR.EDF", target))

            replace.assert_called_once()
            pathlib.Path(fake_temp.name).unlink(missing_ok=True)

    def test_cancelled_download_removes_temp_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "STR.EDF"
            ezshare = ezshare_for(FakeResponse([b"edf-data"]), running=False)

            self.assertFalse(file_ops.download_file(ezshare, "http://example.test/STR.EDF", target))
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
