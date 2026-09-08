"""Original fast GUI demo: steady 3D heat conduction through a cube.

Run through comsol_run_case('gui_quickstart_3d'). The model is created from
scratch, solved once, given an inspectable Results tree, exported, and saved.
"""
from pathlib import Path
import json
from uuid import uuid4

import jpype
import numpy as np


def build(client, outdir, progress):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    JI = jpype.JInt
    model_name = "Teaching_GUI_Quickstart_" + uuid4().hex[:10]
    model = client.create(model_name)
    j = model.java
    j.label(model_name + ".mph")

    for key, value in {
        "L": "10[mm]", "Tcold": "293.15[K]", "Thot": "303.15[K]",
        "kmat": "1[W/(m*K)]", "rho": "1000[kg/m^3]", "Cp": "1000[J/(kg*K)]",
    }.items():
        j.param().set(key, value)

    comp = j.component().create("comp1", True)
    geom = comp.geom().create("geom1", 3)
    geom.lengthUnit("mm")
    block = geom.create("blk1", "Block")
    block.set("size", ["L", "L", "L"])
    block.set("selresult", True)
    geom.run()

    allsolid = comp.selection().create("allsolid", "Explicit")
    allsolid.geom("geom1", 3)
    allsolid.all()
    cold = comp.selection().create("cold", "Box")
    cold.set("entitydim", JI(2))
    cold.set("condition", "inside")
    cold.set("xmin", "-0.001[mm]")
    cold.set("xmax", "0.001[mm]")
    hot = comp.selection().create("hot", "Box")
    hot.set("entitydim", JI(2))
    hot.set("condition", "inside")
    hot.set("xmin", "L-0.001[mm]")
    hot.set("xmax", "L+0.001[mm]")
    if len(cold.entities(2)) != 1 or len(hot.entities(2)) != 1:
        raise RuntimeError("Expected one cold face and one hot face")

    mat = comp.material().create("mat1", "Common")
    mat.label("Demo solid — constant properties")
    mat.selection().all()
    mat.propertyGroup("def").set("thermalconductivity", "kmat")
    mat.propertyGroup("def").set("density", "rho")
    mat.propertyGroup("def").set("heatcapacity", "Cp")

    ht = comp.physics().create("ht", "HeatTransfer", "geom1")
    t1 = ht.create("coldT", "TemperatureBoundary", 2)
    t1.label("Cold face 20 °C")
    t1.selection().named("cold")
    t1.set("T0", "Tcold")
    t2 = ht.create("hotT", "TemperatureBoundary", 2)
    t2.label("Hot face 30 °C")
    t2.selection().named("hot")
    t2.set("T0", "Thot")

    ave = comp.cpl().create("avevol", "Average")
    ave.selection().geom("geom1", 3)
    ave.selection().named("allsolid")

    mesh = comp.mesh().create("mesh1", "geom1")
    mesh.autoMeshSize(4)
    mesh.run()
    study = j.study().create("std1")
    study.label("Stationary conduction")
    study.create("stat", "Stationary")
    progress("model ready: 3D cube, material, two temperature boundaries, mesh and stationary study")
    study.run()
    progress("stationary solve completed; building visible Results tree")

    pg = j.result().create("pgTemp", "PlotGroup3D")
    pg.label("Temperature field — MCP GUI quickstart")
    pg.set("data", "dset1")
    surf = pg.create("surf1", "Surface")
    surf.label("Temperature")
    surf.set("expr", "T")
    surf.set("unit", "degC")
    pg.run()

    table = j.result().table().create("tblSummary", "Table")
    table.label("Summary values")
    mean = j.result().numerical().create("Tmean", "EvalGlobal")
    mean.label("Domain mean temperature")
    mean.set("data", "dset1")
    mean.set("expr", ["comp1.avevol(T)"])
    mean.set("unit", ["degC"])
    mean.set("table", "tblSummary")
    mean.setResult()
    value = float(np.asarray(mean.getReal()).ravel()[-1])

    image = j.result().export().create("imgTemp", "Image3D")
    image.label("GitHub GUI preview")
    image.set("plotgroup", "pgTemp")
    image.set("imagetype", "png")
    image.set("pngfilename", str(out / "mcp_gui_quickstart_3d.png"))
    image.set("background", "color")
    image.set("size", "manualweb")
    image.set("unit", "px")
    image.set("width", JI(1600))
    image.set("height", JI(1000))
    image.set("options3d", "on")
    image.run()

    mph_path = out / "mcp_gui_quickstart_3d.mph"
    try:
        model.save(str(mph_path))
    finally:
        j.label(model_name + ".mph")

    result = {
        "case_id": "gui_quickstart_3d",
        "model_name": str(model.name()),
        "model_tag": str(j.tag()),
        "comsol_version": str(client.version),
        "mean_temperature_degC": value,
        "analytic_mean_degC": 25.0,
        "check_passed": abs(value - 25.0) < 1e-6,
        "model_file": str(mph_path),
        "image_file": str(out / "mcp_gui_quickstart_3d.png"),
        "results_tree": ["pgTemp/surf1", "Tmean", "tblSummary", "imgTemp"],
    }
    (out / "gui-demo-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not result["check_passed"]:
        raise RuntimeError("Mean temperature check failed")
    progress("complete: viewable MPH, Results tree, scalar check and PNG exported")
    return result
