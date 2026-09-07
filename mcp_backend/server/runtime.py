"""One JVM thread, non-destructive sessions, and inspectable background jobs.

This runtime is an automation service, not a Python or COMSOL security sandbox.
Only expose it to the trusted user who owns the COMSOL installation.
"""
from __future__ import annotations

import asyncio
import functools
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def inside(root: Path, value: str | Path) -> Path:
    """Resolve a path and reject traversal, including symlink escapes."""
    root = root.resolve()
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path must remain within {root}")
    return resolved


def jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return jsonable(value.tolist())
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class Runtime:
    def __init__(self, root: Path = ROOT, output_root: Path | None = None):
        self.root = root
        self.output_root = Path(output_root or os.getenv("COMSOL_OUTPUT_ROOT", str(root / "runs"))).resolve()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="comsol-jvm")
        self.manager = None
        self.server = None
        self.client_handle = None
        self.last_endpoint = None
        self.tracked_tags = {}
        self.jobs: dict[str, dict] = {}
        self.futures = {}
        self.latest_study_job = None
        self.lock = threading.Lock()
        self.desktop_process = None
        self.desktop_endpoint = None

    async def call(self, function, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, functools.partial(function, *args, **kwargs))

    def installation_root(self, version: str | None = None) -> Path:
        import mph
        selected = version or (self.manager.client.version if self.manager and self.manager.is_connected
                               else os.getenv("COMSOL_VERSION") or None)
        discovered = Path(mph.discovery.backend(selected)["root"]).resolve()
        configured = os.getenv("COMSOL_ROOT")
        if configured:
            path = Path(configured).resolve()
            if not (path / "applications").is_dir():
                raise ValueError("COMSOL_ROOT must be the Multiphysics directory containing applications")
            if path != discovered:
                raise ValueError("COMSOL_ROOT does not match the installation selected by MPh discovery. Set COMSOL_VERSION to the matching installed release or repair COMSOL registration; COMSOL_ROOT alone does not select the JVM/server executable.")
            return path
        return discovered

    def doctor(self) -> dict:
        import importlib.metadata
        info = {"success": True, "python": sys.version.split()[0], "output_root": str(self.output_root),
                "code_execution_enabled": os.getenv("COMSOL_ALLOW_CODE") == "1",
                "transport_warning": "Trusted single-user automation; not a sandbox or multi-tenant service."}
        for name in ("mph", "mcp", "JPype1"):
            try:
                info[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                info[name] = "missing"
                info["success"] = False
        try:
            root = self.installation_root()
            info.update(comsol_root=str(root), application_library=(root / "applications").is_dir())
        except Exception as error:
            info.update(success=False, error=str(error))
        info["license_checked"] = False
        info["license_note"] = "Installation discovery does not prove a COMSOL or add-on license is available."
        return info

    def bind_manager(self, manager):
        self.manager = manager
        # Patch the vendored instance, preserving its model CRUD semantics. Never
        # call Client.clear(): other clients may be viewing their own models.
        manager.start = self.start
        manager.connect = self.connect
        manager.disconnect = self.disconnect
        manager.get_status = self.status

    def prepare_stdio_client(self):
        """Initialize only the JVM before MCP starts its blocking stdin reader.

        On Windows, HotSpot changes CRT stdio modes during startup; doing that
        after another thread starts reading stdin can deadlock. host=None uses
        COMSOL's client API without starting a server or checking out a model
        license. All later API calls still use this same executor thread.
        """
        import mph
        self.installation_root()
        if self.client_handle is None:
            self.client_handle = mph.Client(host=None, version=os.getenv("COMSOL_VERSION") or None)

    def _attach(self, port: int, host: str, version: str | None = None):
        import mph
        if self.client_handle is None:
            self.client_handle = mph.Client(port=port, host=host, version=version)
        else:
            self.client_handle.connect(port=port, host=host)
        if self.last_endpoint is not None and self.last_endpoint != (host, port):
            # Old Java proxies must not be used against a different server. This
            # clears only Python tracking, never COMSOL's model collection.
            self.manager._models = {}
            self.manager._current_model = None
            self.tracked_tags = {}
        elif self.tracked_tags:
            # COMSOL invalidates model proxies when disconnecting. Retrieve fresh
            # wrappers by tag rather than reusing stale Python/Java references.
            refreshed = {}
            current = self.manager.current_model
            for old_name, tag in self.tracked_tags.items():
                try:
                    model = mph.Model(self.client_handle.java.model(tag))
                    refreshed[old_name] = model  # Preserve the public MCP handle even if Desktop changed its label.
                except Exception:
                    continue  # The user may have removed this model in Desktop.
            self.manager._models = refreshed
            self.manager._current_model = current if current in refreshed else next(iter(refreshed), None)
        self.manager._client = self.client_handle
        self.last_endpoint = (host, port)
        try:
            import jpype
            util = jpype.JClass("com.comsol.model.util.ModelUtil")
            util.setServerBusyHandler(jpype.JClass("com.comsol.model.util.ServerBusyHandler")(jpype.JInt(120000)))
        except Exception:
            pass  # Older releases may lack the busy-handler overload.

    def start(self, cores=None, version=None, products=None) -> dict:
        if self.manager.is_connected:
            return dict(self.status(), success=True, message="Reused session; existing models preserved.")
        import mph
        try:
            self.installation_root(version)
            requested_version = version or os.getenv("COMSOL_VERSION")
            if self.client_handle is not None and requested_version and self.client_handle.version != requested_version:
                raise ValueError("This process already initialized COMSOL " + self.client_handle.version +
                                 "; set COMSOL_VERSION and restart MCP to use another JVM version.")
            if self.server is None:
                self.server = mph.Server(cores=cores or int(os.getenv("COMSOL_CORES", "4")),
                                         version=version or os.getenv("COMSOL_VERSION") or None,
                                         port=0, multi=True, timeout=180)
            self._attach(self.server.port, "localhost", self.server.version)
            result = dict(self.status(), success=True)
            if products:
                result["products_note"] = "Licenses are requested by each physics interface; products is not a license bypass."
            return result
        except Exception as error:
            return {"success": False, "error": str(error)}

    def connect(self, port: int, host: str = "localhost") -> dict:
        if self.manager.is_connected:
            if self.last_endpoint == (host, port):
                return dict(self.status(), success=True)
            return {"success": False, "error": "Already connected. Disconnect explicitly before changing server."}
        if not 1 <= port <= 65535:
            return {"success": False, "error": "Invalid TCP port."}
        try:
            self._attach(port, host, os.getenv("COMSOL_VERSION") or None)
            return dict(self.status(), success=True)
        except Exception as error:
            return {"success": False, "error": str(error)}

    def disconnect(self) -> dict:
        if not self.manager.is_connected:
            return {"success": True, "message": "Already disconnected; models preserved."}
        try:
            self.tracked_tags = {name: str(model.java.tag()) for name, model in self.manager.models.items()
                                 if hasattr(model, "java")}
            self.client_handle.disconnect()
            self.manager._client = None
            # Tracked proxies are kept for reconnection to this same server.
            return {"success": True, "message": "Disconnected without deleting models or stopping the multi-client server."}
        except Exception as error:
            return {"success": False, "error": str(error)}

    def status(self) -> dict:
        connected = bool(self.manager and self.manager.is_connected)
        result = {"connected": connected, "models": [], "current_model": None}
        if connected:
            client = self.manager.client
            result.update(version=client.version, cores=client.cores, standalone=bool(client.standalone),
                          host=client.host, port=client.port,
                          models=[{"name": name} for name in self.manager.models],
                          current_model=self.manager.current_model,
                          note="Lists only this MCP session's tracked models; other desktop models are untouched.")
        return result

    def open_desktop(self) -> dict:
        if not self.manager.is_connected:
            started = self.start()
            if not started.get("success"):
                return started
        endpoint = (self.manager.client.host, self.manager.client.port)
        if self.desktop_process is not None and self.desktop_process.poll() is None and self.desktop_endpoint == endpoint:
            return {"success": True, "already_open": True, "port": self.manager.client.port}
        root = self.installation_root()
        executable = root / "bin" / "win64" / "comsolmphclient.exe"
        if not executable.exists():
            return {"success": False, "error": "Automatic desktop launch currently supports Windows.",
                    "host": self.manager.client.host, "port": self.manager.client.port,
                    "hint": "Open your COMSOL Desktop and connect it to this server manually."}
        self.desktop_process = subprocess.Popen([str(executable), "-server", self.manager.client.host,
                                                 "-port", str(self.manager.client.port)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.desktop_endpoint = endpoint
        return {"success": True, "pid": self.desktop_process.pid, "port": self.manager.client.port,
                "next_step": "Complete the simulation through MCP. At the end, the USER manually clicks 文件 → COMSOL Multiphysics Server → 从服务器导入 App (File > COMSOL Multiphysics Server > Import App from Server) and selects the returned model name. The agent must not use screen recognition, OCR, screenshots or UI automation."}

    def catalog(self) -> list[dict]:
        data = json.loads((self.root / "examples" / "catalog.json").read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else data["cases"]

    def list_cases(self, category: str | None = None, case_id: str | None = None, detail: bool = False) -> dict:
        cases = self.catalog()
        if category:
            cases = [case for case in cases if category.casefold() in case.get("category", "").casefold()]
        if case_id:
            cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            return {"success": False, "cases": [], "count": 0, "error": "No matching case. Omit filters to list available ids/categories."}
        try:
            library = self.installation_root() / "applications"
        except Exception:
            library = None
        output = []
        for original in cases:
            case = dict(original)
            relative = case.get("relative_path") or case.get("application_path")
            case["locally_available"] = bool(library and relative and inside(library, relative).is_file()) if relative else (self.root / "examples" / "original" / (case["id"] + ".py")).is_file()
            case["license_verified"] = False
            if not detail:
                compact_keys = {"id", "title_zh", "category", "modules", "dimensions", "status", "locally_available", "license_verified"}
                case = {key: value for key, value in case.items() if key in compact_keys}
            output.append(case)
        return {"success": True, "cases": output, "count": len(output), "detail": detail,
                "hint": "Request case_id plus detail=true for one case's setup, study and validation instructions."}

    def submit_case(self, case_id: str, solve: bool = False, study: str | None = None,
                    show_desktop: bool = True) -> dict:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", case_id):
            return {"success": False, "error": "Invalid case id."}
        entry = next((case for case in self.catalog() if case["id"] == case_id), None)
        if entry is None:
            return {"success": False, "error": "Unknown case; call comsol_list_cases."}
        job_id = uuid4().hex
        directory = inside(self.output_root, job_id + "_" + case_id)
        with self.lock:
            self.jobs[job_id] = {"job_id": job_id, "case_id": case_id, "status": "queued", "events": [],
                                 "output_dir": str(directory), "submitted_at": time.time()}
        self.futures[job_id] = self.executor.submit(self._run_case, job_id, entry, directory, solve, study, show_desktop)
        return {"success": True, "job_id": job_id, "status": "queued", "poll_tool": "comsol_job_status"}

    def _progress(self, job_id: str, message: str):
        with self.lock:
            job = self.jobs[job_id]
            job["events"].append({"time": time.time(), "message": str(message)[:2000]})
            job["events"] = job["events"][-100:]

    def _run_case(self, job_id, entry, directory, solve, study, show_desktop):
        with self.lock:
            self.jobs[job_id]["status"] = "running"
        try:
            directory.mkdir(parents=True, exist_ok=False)
            self._progress(job_id, "Starting a multi-client COMSOL session")
            started = self.start()
            if not started.get("success"):
                raise RuntimeError(started.get("error", "Session failed to start"))
            if show_desktop:
                self._progress(job_id, json.dumps(self.open_desktop(), ensure_ascii=False))
            relative = entry.get("relative_path") or entry.get("application_path")
            if relative:
                source = inside(self.installation_root() / "applications", relative)
                if not source.is_file() or source.suffix.lower() != ".mph":
                    raise FileNotFoundError(f"Installed Application Library model missing: {relative}. Install/download it in COMSOL first.")
                self._progress(job_id, f"Loading licensed local Application Library case: {relative}")
                model = self.manager.client.load(str(source))
                model.rename(f"Teaching_{entry['id']}_{job_id[:8]}")
                self.manager.add_model(model)
                self.manager.set_current_model(model.name())
                studies = list(model.studies())
                if solve:
                    if study:
                        self._progress(job_id, f"Solving selected study: {study}")
                        model.solve(study)
                    else:
                        self._progress(job_id, "Solving all existing study nodes in their stored order")
                        model.solve()
                intended_name = model.name()
                try:
                    model.save(str(directory / (entry["id"] + ".mph")))
                finally:
                    model.rename(intended_name)
                result = {"model_name": model.name(), "model_tag": str(model.java.tag()), "studies": studies,
                          "solved_this_run": solve, "validation": "solver_completed" if solve else "loaded_only",
                          "source": "User's licensed local COMSOL Application Library"}
            else:
                module_path = inside(self.root / "examples" / "original", entry["id"] + ".py")
                spec = importlib.util.spec_from_file_location("comsol_original_" + entry["id"], module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._progress(job_id, "Executing original teaching recipe: geometry, materials, physics, mesh, studies, results")
                result = module.build(self.manager.client, directory, lambda msg: self._progress(job_id, msg))
                name = result.get("model_name")
                # The builder may create several models; track its explicit result only.
                if name:
                    tag = result.get("model_tag")
                    model = next((m for m in self.manager.client.models()
                                  if str(m.java.tag()) == tag), None) if tag else next(
                                      (m for m in self.manager.client.models() if m.name() == name), None)
                    if model is not None:
                        actual_name = self.manager.add_model(model)
                        self.manager.set_current_model(actual_name)
                        result["model_name"] = actual_name
            result = jsonable(result)
            (directory / "job-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.lock:
                self.jobs[job_id].update(status="completed", result=result, completed_at=time.time())
        except Exception as error:
            detail = {"type": type(error).__name__, "message": str(error)[:12000]}
            with self.lock:
                self.jobs[job_id].update(status="failed", error=detail, completed_at=time.time())
            if directory.exists():
                (directory / "job-error.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    def job_status(self, job_id: str) -> dict:
        with self.lock:
            if job_id not in self.jobs:
                return {"success": False, "error": "Unknown job id. Jobs are retained in memory for this MCP process."}
            return json.loads(json.dumps(dict(success=True, **self.jobs[job_id]), default=str))

    def submit_study(self, study_name: str | None, model_name: str | None) -> dict:
        model_name = model_name or (self.manager.current_model if self.manager else None)
        job_id = uuid4().hex
        with self.lock:
            self.jobs[job_id] = {"job_id": job_id, "kind": "study", "status": "queued", "events": [],
                                 "model_name": model_name, "study_name": study_name, "submitted_at": time.time()}
            self.latest_study_job = job_id
        def solve():
            with self.lock:
                self.jobs[job_id]["status"] = "running"
            try:
                if not self.manager.is_connected:
                    raise RuntimeError("No active COMSOL session.")
                model = self.manager.get_model(model_name)
                if model is None:
                    raise ValueError("Model must be explicitly tracked by this MCP session.")
                self._progress(job_id, "Solving " + (study_name or "all existing study nodes"))
                model.solve(study_name)
                with self.lock:
                    self.jobs[job_id].update(status="completed", completed_at=time.time(),
                                             result={"model_name": model.name(), "study": study_name, "solved": True})
            except Exception as error:
                with self.lock:
                    self.jobs[job_id].update(status="failed", completed_at=time.time(),
                                             error={"type": type(error).__name__, "message": str(error)[:12000]})
        self.futures[job_id] = self.executor.submit(solve)
        return {"success": True, "job_id": job_id, "status": "queued", "poll_tool": "comsol_job_status"}

    async def wait_job(self, job_id: str | None, timeout: float | None = None) -> dict:
        if not job_id or job_id not in self.jobs:
            return {"success": False, "error": "No matching job."}
        duration = min(max(timeout if timeout is not None else 30.0, 0.0), 30.0)
        deadline = time.monotonic() + duration
        while True:
            state = self.job_status(job_id)
            if state["status"] in {"completed", "failed", "cancelled"} or time.monotonic() >= deadline:
                return state
            await asyncio.sleep(0.1)

    def cancel_job(self, job_id: str | None) -> dict:
        if not job_id or job_id not in self.futures:
            return {"success": False, "error": "No matching job."}
        if self.futures[job_id].cancel():
            with self.lock:
                self.jobs[job_id].update(status="cancelled", completed_at=time.time())
            return dict(self.job_status(job_id), cancellation="cancelled_before_start")
        return {"success": False, "job_id": job_id,
                "error": "This job is already running or finished. Running Java calls cannot be safely interrupted from another Python thread. If needed, ask the USER to manually press COMSOL Desktop's Stop control; the agent must not use screen recognition or UI automation."}

    def execute_code(self, model_name: str, code: str) -> dict:
        if os.getenv("COMSOL_ALLOW_CODE") != "1":
            return {"success": False, "error": "Disabled. A trusted local operator must set COMSOL_ALLOW_CODE=1 and restart the server. This executes arbitrary Python and is not sandboxed."}
        if not self.manager.is_connected:
            return {"success": False, "error": "No active COMSOL connection. Reconnect before using model proxies."}
        model = self.manager.get_model(model_name)
        if model is None:
            return {"success": False, "error": "Name must refer to a model explicitly created/loaded by this MCP session."}
        if len(code) > 100000:
            return {"success": False, "error": "Code exceeds 100,000 characters."}
        captured = []
        def bounded_print(*values, sep=" ", end="\n", **kwargs):
            if sum(map(len, captured)) < 16000:
                captured.append((sep.join(map(str, values)) + end)[:16000])
        environment = {"model": model, "java": model.java, "output_dir": self.output_root,
                       "print": bounded_print, "result": None}
        try:
            exec(compile(code, "<trusted-comsol-code>", "exec"), environment)
            return {"success": True, "result": jsonable(environment["result"]), "stdout": "".join(captured)[:16000]}
        except Exception as error:
            return {"success": False, "error": str(error)[:12000], "stdout": "".join(captured)[:16000]}


class SerializedRegistrar:
    """Preserve upstream signatures while moving every synchronous Java call to one thread."""
    def __init__(self, mcp, runtime: Runtime):
        self.mcp, self.runtime = mcp, runtime

    def _wrap(self, function):
        signature = inspect.signature(function)
        @functools.wraps(function)
        async def call(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = dict(bound.arguments)
            # Explicit output destinations prevent an export from silently using
            # a file path embedded in a model supplied by somebody else.
            if function.__name__ in {"model_save", "results_export_data", "results_export_image"}:
                value = arguments.get("file_path")
                if not value:
                    return {"success": False, "error": "Provide an explicit file_path inside COMSOL_OUTPUT_ROOT."}
                try:
                    path = inside(self.runtime.output_root, value)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    arguments["file_path"] = str(path)
                except ValueError as error:
                    return {"success": False, "error": str(error)}
            def invoke():
                if function.__name__ in {"model_save", "model_save_version"}:
                    model = self.runtime.manager.get_model(arguments.get("model_name"))
                    if model is not None:
                        label = str(model.java.label())
                        try:
                            result = function(**arguments)
                        finally:
                            model.java.label(label)
                        if isinstance(result, dict) and "model" in result:
                            result["model"] = model.name()
                        return result
                return function(**arguments)
            result = await self.runtime.call(invoke)
            return jsonable(result)
        call.__signature__ = signature
        return call

    def tool(self, *args, **kwargs):
        def decorator(function):
            if function.__name__ in {"study_solve", "study_solve_async", "study_get_progress", "study_wait", "study_cancel", "study_create"}:
                return function  # Replaced by the runtime's single-thread job tools.
            description = kwargs.copy()
            if function.__name__ == "comsol_disconnect":
                description["description"] = "Disconnect this MCP client while preserving every server model. Never clears models."
            if function.__name__ == "comsol_start":
                description["description"] = "Start/reuse a multi-client COMSOL server. Repeated calls preserve models. Use comsol_open_desktop to view the same server."
            self.mcp.tool(*args, **description)(self._wrap(function))
            return function
        return decorator

    def resource(self, *args, **kwargs):
        def decorator(function):
            self.mcp.resource(*args, **kwargs)(self._wrap(function))
            return function
        return decorator
