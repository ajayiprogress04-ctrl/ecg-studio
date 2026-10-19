import json
from pathlib import Path
import tempfile
import time
import unittest
from desktop.service import create_app


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.inputs = []
        self.opened = []

        def dialog(kind):
            if kind == "files":
                return [str(p) for p in self.inputs]
            return str(self.root)

        self.app = create_app(
            dialog=dialog,
            opener=lambda p: self.opened.append(p),
        )
        self.app.config.update(
            TESTING=True,
            DESKTOP_HOST="localhost",
        )
        self.client = self.app.test_client()
        self.headers = {
            "X-Desktop-Token": self.app.desktop_token,
        }

    def tearDown(self):
        self.app.desktop_executor.shutdown(wait=True)
        self.temp.cleanup()

    def post(self, url, body=None):
        return self.client.post(
            "/api/" + url,
            json=body or {},
            headers=self.headers,
        )

    def wait(self):
        for _ in range(500):
            state = self.client.get(
                "/api/state",
                headers=self.headers,
            ).json

            if not state["busy"]:
                return state

            time.sleep(0.01)

        self.fail("Worker did not finish")

    def recording(self, name, body):
        path = self.root / name
        path.write_text(body)
        self.inputs.append(path)
        return path

    def test_auth_and_host(self):
        self.assertEqual(
            self.client.get("/api/state").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/",
                headers={"Host": "evil.example"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/",
                headers={"Origin": "https://evil.example"},
            ).status_code,
            403,
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.app.desktop_token.encode(),
            response.data,
        )

    def test_required_choices_and_dialog_cancel(self):
        self.assertEqual(
            self.post("start").status_code,
            400,
        )
        self.assertEqual(
            self.post("choose-files").json["files"],
            [],
        )

        self.post("choose-folder")

        # Windows can represent the same directory using
        # either its long name or its short 8.3 alias.
        self.assertTrue(
            Path(
                self.app.desktop_state["output_root"]
            ).samefile(self.root)
        )

    def test_batch_success_failure_and_preservation(self):
        original = (
            "local_time,ecg,ecg_mV\n"
            "2026-06-18 08:52:24.000,10,0.1\n"
            "2026-06-18 14:52:24.000,20,0.2\n"
        )
        source = self.recording("test.csv", original)
        self.recording(
            "bad.csv",
            "header\ninvalid,1,2\n",
        )

        self.post("choose-files")
        self.post("choose-folder")

        self.assertEqual(
            self.post("start").status_code,
            202,
        )

        state = self.wait()

        self.assertEqual(
            [job["status"] for job in state["jobs"]],
            ["complete", "failed"],
        )
        self.assertEqual(source.read_text(), original)

        output = Path(state["jobs"][0]["folder"])

        self.assertEqual(
            len(list(output.glob("*.csv"))),
            2,
        )
        self.assertFalse(
            (
                Path(state["batch_folder"]) / "002_bad"
            ).exists()
        )
        self.assertTrue(
            (
                Path(state["batch_folder"])
                / "ECG_Studio_summary.json"
            ).exists()
        )

        self.assertEqual(
            self.post(
                "open-folder",
                {"index": 0},
            ).status_code,
            200,
        )
        self.assertEqual(self.opened, [output])

        previous = state["batch_folder"]
        self.post("start")
        state = self.wait()

        self.assertNotEqual(
            previous,
            state["batch_folder"],
        )
        self.assertTrue(output.exists())

    def test_clear_and_quit(self):
        self.recording(
            "x.csv",
            "header\ninvalid,1,2\n",
        )
        self.post("choose-files")
        self.post("clear")

        self.assertEqual(
            self.app.desktop_state["files"],
            [],
        )
        self.assertEqual(
            self.post("quit").status_code,
            200,
        )
        self.assertTrue(
            self.app.desktop_stop.is_set()
        )

    def test_cancel_busy_and_disk_failure(self):
        from unittest.mock import patch
        import threading

        entered = threading.Event()
        release = threading.Event()

        def process(path, destination, report):
            Path(destination).mkdir()
            entered.set()
            release.wait(2)
            report(chunks=1, valid_rows=1)

            return {
                "outputs": [
                    {
                        "name": "one.csv",
                        "rows": 1,
                        "bytes": 1,
                    }
                ],
                "valid_rows": 1,
            }

        self.recording(
            "x.csv",
            (
                "header\n"
                "2026-06-18 08:52:24.000,1,0.1\n"
            ),
        )
        self.post("choose-files")
        self.post("choose-folder")

        with patch(
            "desktop.service.split_ecg",
            process,
        ):
            self.post("start")
            self.assertTrue(entered.wait(2))

            self.assertEqual(
                self.post("start").status_code,
                409,
            )
            self.assertEqual(
                self.post("quit").status_code,
                409,
            )

            self.post("cancel")
            release.set()
            state = self.wait()

            self.assertEqual(
                state["jobs"][0]["status"],
                "cancelled",
            )

        with patch(
            "desktop.service.shutil.disk_usage",
            return_value=type(
                "Disk",
                (),
                {"free": 1},
            )(),
        ):
            self.post("start")
            state = self.wait()

            self.assertEqual(
                state["jobs"][0]["status"],
                "failed",
            )


if __name__ == "__main__":
    unittest.main()
