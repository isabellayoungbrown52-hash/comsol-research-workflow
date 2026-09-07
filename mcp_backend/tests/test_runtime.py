"""Runtime protection and MCP protocol tests; no COMSOL license/JVM required."""
import asyncio
import json
from pathlib import Path
import sys
import threading
import time
import socket
import subprocess
from types import SimpleNamespace

import unittest
import tempfile
import os
from unittest.mock import patch

from server.main import BearerAuth, validate_token
from server.runtime import ROOT, Runtime, SerializedRegistrar, inside


TOKEN = "test-4LveZoVkRM79YS8dKaPWmDuT02QCAB"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_token_required_and_paths_confined(self):
        tmp_path = self.tmp_path
        for value in (None, "", "short", "a" * 40):
            with self.assertRaises(ValueError):
                validate_token(value)
        assert validate_token(TOKEN) == TOKEN
        assert inside(tmp_path, "result/output.mph") == tmp_path / "result" / "output.mph"
        with self.assertRaises(ValueError):
            inside(tmp_path, "../escape.mph")
        with self.assertRaises(ValueError):
            inside(tmp_path, tmp_path.parent / "outside.mph")


    def test_auth_covers_sse_post_and_streamable_http(self):
        async def run():
            calls = []
            async def app(scope, receive, send):
                calls.append(scope["path"])
                await send({"type": "http.response.start", "status": 204, "headers": []})
                await send({"type": "http.response.body", "body": b""})
            auth = BearerAuth(app, TOKEN)
            for endpoint in ("/sse", "/messages/", "/mcp"):
                for header, status in ((None, 401), ("Bearer wrong", 401), ("Bearer " + TOKEN, 204)):
                    output = []
                    headers = [] if header is None else [(b"authorization", header.encode())]
                    async def send(message):
                        output.append(message)
                    await auth({"type": "http", "path": endpoint, "headers": headers,
                                "query_string": ("token=" + TOKEN).encode()}, None, send)
                    assert output[0]["status"] == status
            assert calls == ["/sse", "/messages/", "/mcp"]
        asyncio.run(run())


    def test_all_java_work_uses_one_thread_and_keeps_order(self):
        tmp_path = self.tmp_path
        runtime = Runtime(output_root=tmp_path)
        observed = []
        async def run():
            def work(number):
                observed.append((number, threading.get_ident()))
                return number
            assert await asyncio.gather(*(runtime.call(work, i) for i in range(8))) == list(range(8))
        try:
            asyncio.run(run())
            assert [item[0] for item in observed] == list(range(8))
            assert len({item[1] for item in observed}) == 1
            assert observed[0][1] != threading.get_ident()
        finally:
            runtime.executor.shutdown()


    def test_start_idempotent_disconnect_never_clears_models(self):
        tmp_path = self.tmp_path
        class FakeClient:
            version = "6.2"
            cores = 2
            standalone = False
            host = "localhost"
            port = 12345
            disconnected = False
            def clear(self):
                raise AssertionError("MUST NEVER CLEAR USER MODELS")
            def disconnect(self):
                self.disconnected = True
        client = FakeClient()
        class Manager:
            _client = None
            _models = {"existing": object()}
            current_model = "existing"
            @property
            def is_connected(self): return self._client is not None
            @property
            def client(self): return self._client
            @property
            def models(self): return self._models.copy()
        runtime = Runtime(output_root=tmp_path)
        manager = Manager()
        manager._client = client
        runtime.bind_manager(manager)
        runtime.client_handle = client
        assert runtime.start()["success"]
        assert "existing" in manager.models
        assert runtime.disconnect()["success"]
        assert client.disconnected
        assert "existing" in manager.models
        assert runtime.disconnect()["success"]
        runtime.executor.shutdown()


    def test_code_execution_disabled_without_explicit_opt_in(self):
        tmp_path = self.tmp_path
        env = patch.dict(os.environ, {"COMSOL_ALLOW_CODE": "0"})
        env.start()
        self.addCleanup(env.stop)
        runtime = Runtime(output_root=tmp_path)
        result = runtime.execute_code("missing", "raise RuntimeError('must not run')")
        assert not result["success"]
        assert "Disabled" in result["error"]
        runtime.executor.shutdown()


    def test_case_job_reports_build_failure_without_false_success(self):
        tmp_path = self.tmp_path
        examples = tmp_path / "examples"
        (examples / "original").mkdir(parents=True)
        (examples / "catalog.json").write_text(json.dumps({"cases": [{"id": "broken_example"}]}))
        (examples / "original" / "broken_example.py").write_text(
            "def build(client, outdir, progress):\n    progress('geometry')\n    raise RuntimeError('license unavailable')\n")
        runtime = Runtime(root=tmp_path, output_root=tmp_path / "runs")
        runtime.manager = SimpleNamespace(client=object())
        runtime.start = lambda: {"success": True}
        submitted = runtime.submit_case("broken_example", show_desktop=False)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = runtime.job_status(submitted["job_id"])
            if result["status"] == "failed":
                break
            time.sleep(0.01)
        assert result["status"] == "failed"
        assert "license unavailable" in result["error"]["message"]
        assert any(event["message"] == "geometry" for event in result["events"])
        assert (Path(result["output_dir"]) / "job-error.json").is_file()
        assert not runtime.submit_case("../private")["success"]
        runtime.executor.shutdown()

    def test_study_queue_cancel_and_nonblocking_status(self):
        runtime = Runtime(output_root=self.tmp_path)
        started = threading.Event()
        release = threading.Event()
        threads = []
        class Model:
            def solve(self, name):
                threads.append(threading.get_ident())
                started.set()
                release.wait(timeout=5)
            def name(self): return "example"
        runtime.manager = SimpleNamespace(is_connected=True, current_model="example", get_model=lambda name: Model())
        try:
            first = runtime.submit_study(None, "example")["job_id"]
            assert started.wait(timeout=2)
            assert runtime.job_status(first)["status"] == "running"
            assert not runtime.cancel_job(first)["success"]
            second = runtime.submit_study(None, "example")["job_id"]
            assert runtime.cancel_job(second)["status"] == "cancelled"
            release.set()
            done = asyncio.run(runtime.wait_job(first, timeout=2))
            assert done["status"] == "completed"
            assert threads and threads[0] != threading.get_ident()
            assert len(threads) == 1
        finally:
            release.set()
            runtime.executor.shutdown()

    def test_save_wrapper_preserves_public_model_name(self):
        runtime = Runtime(output_root=self.tmp_path)
        class Java:
            value = "Original.mph"
            def label(self, value=None):
                if value is not None: self.value = value
                return self.value
        model = SimpleNamespace(java=Java())
        model.name = lambda: Path(model.java.label()).stem
        runtime.manager = SimpleNamespace(get_model=lambda name: model)
        def model_save(model_name=None, file_path=None, format=None):
            model.java.label(Path(file_path).name)
            return {"success": True, "model": model.name()}
        wrapper = SerializedRegistrar(None, runtime)._wrap(model_save)
        try:
            result = asyncio.run(wrapper(file_path="changed.mph"))
            assert result["success"]
            assert result["model"] == "Original"
            assert model.java.label() == "Original.mph"
        finally:
            runtime.executor.shutdown()

    def test_case_catalog_compact_filter_and_details(self):
        (self.tmp_path / "examples").mkdir()
        cases = {"cases": [{"id": "sample", "category": "Heat", "title_zh": "Example", "learning_goals": ["long detail"]}]}
        (self.tmp_path / "examples" / "catalog.json").write_text(json.dumps(cases))
        runtime = Runtime(root=self.tmp_path, output_root=self.tmp_path / "runs")
        runtime.installation_root = lambda: self.tmp_path
        try:
            compact = runtime.list_cases(category="heat")
            assert compact["count"] == 1
            assert "learning_goals" not in compact["cases"][0]
            full = runtime.list_cases(case_id="sample", detail=True)
            assert full["cases"][0]["learning_goals"] == ["long detail"]
            assert not runtime.list_cases(case_id="missing")["success"]
        finally:
            runtime.executor.shutdown()


    def test_mcp_stdio_initialization_tools_and_status(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def run():
            params = StdioServerParameters(command=sys.executable, args=["-m", "server.main"], cwd=str(ROOT))
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    assert {"comsol_start", "model_create", "comsol_run_case", "comsol_job_status", "comsol_model_code"} <= names
                    status = await session.call_tool("comsol_status", {})
                    assert not status.isError
                    payload = json.loads(status.content[0].text)
                    assert payload["connected"] is False
                    denied = await session.call_tool("comsol_model_code", {"model_name": "none", "code": "result=1"})
                    assert "Disabled" in denied.content[0].text
        asyncio.run(run())

    def test_http_and_sse_real_protocol_with_bearer_auth(self):
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.sse import sse_client
        for transport, endpoint in (("streamable-http", "/mcp"), ("sse", "/sse")):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            env = dict(os.environ, COMSOL_MCP_TOKEN=TOKEN, COMSOL_ALLOW_CODE="0")
            process = subprocess.Popen([sys.executable, "-m", "server.main", "--transport", transport, "--port", str(port)],
                                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            url = f"http://127.0.0.1:{port}{endpoint}"
            try:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        response = httpx.get(url, timeout=0.5)
                        assert response.status_code == 401
                        break
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        if time.monotonic() > deadline or process.poll() is not None:
                            raise AssertionError(f"{transport} server did not start")
                        time.sleep(0.05)
                async def run():
                    factory = streamablehttp_client if transport == "streamable-http" else sse_client
                    async with factory(url, headers={"Authorization": "Bearer " + TOKEN}) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            assert "comsol_doctor" in {item.name for item in tools.tools}
                            status = await session.call_tool("comsol_status", {})
                            assert not status.isError
                            assert not json.loads(status.content[0].text)["connected"]
                asyncio.run(run())
            finally:
                process.terminate()
                process.wait(timeout=10)

if __name__ == "__main__":
    unittest.main()
