"""Original teaching case: 3D finned aluminum heat sink, conduction + prescribed convection.

Run through comsol_run_case('heat_sink_3d'). No proprietary model or external asset.
The build function must execute on the MCP runtime's single COMSOL worker thread.
"""
from pathlib import Path
import csv
import json
from uuid import uuid4
import numpy as np
import jpype


def build(client, outdir, progress):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    JI = jpype.JInt
    ints = lambda values: jpype.JArray(JI)([int(v) for v in values])
    model_name = 'Teaching_HeatSink_3D_' + uuid4().hex[:10]
    model = client.create(model_name)
    j = model.java
    j.label(model_name + '.mph')
    def save(filename):
        # MPh/COMSOL save changes the live model label to the output basename.
        # Restore the unique server name so repeated jobs remain distinguishable.
        try:
            model.save(str(out/filename))
        finally:
            j.label(model_name + '.mph')
    progress('model_created: name=' + str(model.name()) + ', tag=' + str(j.tag()) + '; continue through MCP. After completion, the USER manually imports this model using File > COMSOL Multiphysics Server > Import App from Server. No screen recognition or UI automation.')
    params = {
        'Pheat': '10[W]', 'Tamb': '298.15[K]', 'hconv': '10[W/(m^2*K)]',
        'kAl': '205[W/(m*K)]', 'rhoAl': '2700[kg/m^3]', 'CpAl': '900[J/(kg*K)]',
        'hbulk': '3[mm]', 'Lbase': '40[mm]', 'tbase': '5[mm]',
        'tfin': '2[mm]', 'Hfin': '20[mm]', 'Lheat': '10[mm]',
    }
    for key, value in params.items():
        j.param().set(key, value)
    c = j.component().create('comp1', True)
    g = c.geom().create('geom1', 3)
    g.lengthUnit('mm')
    blocks = [('base', ['Lbase','Lbase','tbase'], ['-Lbase/2','-Lbase/2','0']),
              ('heaterpart', ['Lheat','Lheat','tbase'], ['-Lheat/2','-Lheat/2','0'])]
    for i, x in enumerate([-16,-8,0,8,16]):
        blocks.append((f'fin{i}', ['tfin','Lbase','Hfin'], [f'{x}-tfin/2','-Lbase/2','tbase']))
    for tag, size, pos in blocks:
        f = g.create(tag, 'Block')
        f.set('size', size)
        f.set('pos', pos)
        f.set('selresult', True)
    g.run()
    allsolid = c.selection().create('allsolid', 'Explicit')
    allsolid.geom('geom1', 3)
    allsolid.all()
    ext = c.selection().create('exterior', 'Adjacent')
    ext.set('entitydim', JI(3))
    ext.set('outputdim', JI(2))
    ext.set('input', ['allsolid'])
    ext.set('interior', False)
    hot = c.selection().create('heater', 'Box')
    hot.set('entitydim', JI(2))
    hot.set('condition', 'inside')
    for key, value in {'xmin':'-5.001[mm]','xmax':'5.001[mm]',
                       'ymin':'-5.001[mm]','ymax':'5.001[mm]',
                       'zmin':'-0.001[mm]','zmax':'0.001[mm]'}.items():
        hot.set(key, value)
    hot_ids = list(hot.entities(2))
    exterior_ids = list(ext.entities(2))
    if len(hot_ids) != 1 or not set(hot_ids).issubset(exterior_ids):
        raise ValueError('Heater selection must be exactly one external bottom face')
    cool = c.selection().create('cooling', 'Explicit')
    cool.geom('geom1', 2)
    cool.set(ints(sorted(set(exterior_ids)-set(hot_ids))))
    save('01_geometry.mph')
    progress('geometry: aluminum base and five fins, named exterior/heater/cooling selections')
    mat = c.material().create('matAl', 'Common')
    mat.label('Aluminum — constant teaching properties')
    mat.selection().all()
    for key, value in {'thermalconductivity':'kAl','density':'rhoAl','heatcapacity':'CpAl'}.items():
        mat.propertyGroup('def').set(key, value)
    ht = c.physics().create('ht', 'HeatTransfer', 'geom1')
    ht.feature('init1').set('Tinit', 'Tamb')
    hotflux = ht.create('heaterflux', 'HeatFluxBoundary', 2)
    hotflux.selection().named('heater')
    hotflux.set('q0', 'Pheat/Lheat^2')
    conv = ht.create('convection', 'HeatFluxBoundary', 2)
    conv.selection().named('cooling')
    conv.set('HeatFluxType', 'ConvectiveHeatFlux')
    conv.set('h', 'hconv')
    conv.set('Text', 'Tamb')
    # Operators must exist before solving, so the saved solution recognizes them.
    for tag, kind, dim, sel in [('maxtemp','Maximum',3,'allsolid'),('avehot','Average',2,'heater'),
                              ('avebody','Average',3,'allsolid'),('intcool','Integration',2,'cooling'),
                              ('intbody','Integration',3,'allsolid')]:
        op = c.cpl().create(tag, kind)
        op.selection().geom('geom1', dim)
        op.selection().named(sel)
    study = j.study().create('std1')
    study.create('stat', 'Stationary')
    mesh = c.mesh().create('mesh1', 'geom1')
    size = mesh.feature('size')
    size.set('custom', True)
    for key, value in {'hmax':'hbulk','hmin':'hbulk/12','hgrad':'1.3','hcurve':'0.3','hnarrow':'1'}.items():
        size.set(key, value)
    local = mesh.create('sizehot', 'Size')
    local.selection().geom('geom1', 2)
    local.selection().named('heater')
    local.set('custom', True)
    local.set('hmaxactive', True)
    local.set('hmax', 'hbulk/2')
    local.set('hminactive', True)
    local.set('hmin', 'hbulk/12')
    mesh.create('ftet1', 'FreeTet')
    save('02_materials_physics.mph')
    progress('physics: 10 W heat flux; convection h=10 W/(m² K), ambient 25 °C')
    numerical = {}
    numerical_specs = [
        ('Tmax','MaxVolume','allsolid','T','degC'),('Tmin','MinVolume','allsolid','T','degC'),
        ('Theater','AvSurface','heater','T','degC'),('Qout','IntSurface','cooling','hconv*(T-Tamb)','W'),
        ('Qin','IntSurface','heater','Pheat/Lheat^2','W'),('Acool','IntSurface','cooling','1','m^2'),
        ('Aheat','IntSurface','heater','1','m^2'),('Vol','IntVolume','allsolid','1','m^3')]
    history = []
    for h in [3., 2., 1.3]:
        j.param().set('hbulk', f'{h}[mm]')
        mesh.run()
        progress(f'mesh: hmax={h} mm, {mesh.stat().getNumElem()} mesh elements; solving stationary')
        study.run()
        if not numerical:
            # Result selections require a Solution dataset with component context.
            for tag, kind, sel, expr, unit in numerical_specs:
                q = j.result().numerical().create(tag, kind)
                q.set('data', 'dset1')
                q.selection().named(sel)
                q.set('expr', expr)
                q.set('unit', unit)
                numerical[tag] = q
        for q in numerical.values():
            q.set('data', 'dset1')
        values = {tag:float(np.asarray(q.getReal()).ravel()[-1]) for tag,q in numerical.items()}
        values.update(hmax_mm=h, elements=int(mesh.stat().getNumElem()))
        values['relative_heat_balance_error'] = abs(values['Qout']-values['Qin'])/values['Qin']
        values['heater_thermal_resistance_K_per_W'] = (values['Theater']-25)/values['Qin']
        history.append(values)
    with (out/'mesh_convergence.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)

    def export_plot(tag, filename, kind='Image3D'):
        image = j.result().export().create('img'+tag, kind)
        image.set('plotgroup', tag)
        image.set('imagetype', 'png')
        image.set('pngfilename', str(out/filename))
        image.set('background', 'color')
        image.set('size', 'manualweb')
        image.set('unit', 'px')
        image.set('width', JI(1600))
        image.set('height', JI(1000))
        for dim in [1,2,3]:
            image.set(f'options{dim}d', 'on')
        image.run()

    for tag, label, expr, unit, filename in [
        ('pgTemp','Steady temperature (degC)','T','degC','temperature_3d.png'),
        ('pgFlux','Conductive heat flux magnitude','ht.tfluxMag','W/m^2','heat_flux_3d.png')]:
        pg = j.result().create(tag, 'PlotGroup3D')
        pg.label(label)
        pg.set('data', 'dset1')
        surface = pg.create('surf1', 'Surface')
        surface.set('expr', expr)
        surface.set('unit', unit)
        pg.run()
        export_plot(tag, filename)
    save('03_stationary.mph')
    progress('stationary: mesh refinement and energy balance evaluated; temperature and heat flux exported')

    transient = j.study().create('std2')
    ts = transient.create('time', 'Transient')
    ts.set('tlist', '0 1 2 5 10 20 30 60 range(120,60,3600)')
    ts.set('usertol', 'on')
    ts.set('rtol', '1e-5')
    ts.set('useinitsol', 'off')
    ts.set('initmethod', 'init')
    before = set(str(tag) for tag in j.sol().tags())
    # Generate the solver before running to configure consistent initialization.
    transient.createAutoSequences('all')
    added = set(str(tag) for tag in j.sol().tags()) - before
    if len(added) != 1:
        raise RuntimeError(f'Expected one transient solver, got {added}')
    solver_tag = added.pop()
    solver = j.sol(solver_tag)
    time_features = [str(tag) for tag in solver.feature().tags() if str(solver.feature(str(tag)).getType())=='Time']
    if len(time_features) != 1:
        raise RuntimeError('Could not identify generated Time solver')
    time_solver = solver.feature(time_features[0])
    time_solver.set('consistent', 'on')
    time_solver.set('initialstepbdfactive', 'on')
    time_solver.set('initialstepbdf', '0.001[s]')
    solver.runAll()
    data = j.result().dataset().create('warmupData', 'Solution')
    data.set('solution', solver_tag)
    expressions = ['t','comp1.maxtemp((T-273.15[K])/1[K])',
                   'comp1.avehot((T-273.15[K])/1[K])','comp1.avebody((T-273.15[K])/1[K])',
                   'comp1.intcool(hconv*(T-Tamb))','comp1.intbody(rhoAl*CpAl*(T-Tamb))']
    units = ['s','1','1','1','W','J']
    q = j.result().numerical().create('warmupMetrics', 'EvalGlobal')
    q.set('data', 'warmupData')
    q.set('expr', expressions)
    q.set('unit', units)
    values = np.asarray(q.getReal(), dtype=float)
    with (out/'warmup.csv').open('w', newline='', encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['time_s','Tmax_degC','heater_mean_degC','body_mean_degC','heat_out_W','stored_energy_J'])
        writer.writerows(values.T)
    pg = j.result().create('pgWarmup', 'PlotGroup1D')
    pg.label('Warm-up from 25 degC')
    pg.set('data', 'warmupData')
    pg.set('ylabelactive', True)
    pg.set('ylabel', 'Temperature (degC)')
    graph = pg.create('glob1', 'Global')
    graph.set('expr', expressions[1:4])
    graph.set('unit', ['1','1','1'])
    graph.set('descr', ['Maximum','Heater mean','Body mean'])
    pg.run()
    export_plot('pgWarmup', 'warmup.png', 'Image2D')
    final=history[-1]
    checks = {
        'power_balance': final['relative_heat_balance_error'] < 1e-3,
        'heater_area': abs(final['Aheat']-1e-4)<1e-8,
        'cooled_area': abs(final['Acool']-.0123)<1e-6,
        'volume': abs(final['Vol']-1.6e-5)<1e-9,
        'Tmax_mesh_change_under_0p05_K': abs(history[-1]['Tmax']-history[-2]['Tmax']) < .05,
        'initial_Tmax_within_0p1_K': abs(values[1,0]-25)<.1,
        'final_matches_stationary_within_0p1_K': abs(values[1,-1]-final['Tmax'])<.1,
    }
    checks = {key: bool(value) for key, value in checks.items()}
    summary = {'case_id':'heat_sink_3d','model_tag':str(j.tag()), 'model_name':str(model.name()),
               'comsol_version':str(client.version), 'steady':final,'mesh_history':history,
               'transient_initial':values[:,0].tolist(),'transient_final':values[:,-1].tolist(),
               'checks':checks,'validated':all(checks.values()),
               'assumptions':['constant aluminum properties','prescribed convection; no air CFD',
                              'no radiation','heater is a heat flux on aluminum, not a separate chip']}
    (out/'validation.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    j.result('pgTemp').run()
    save('heat_sink_3d.mph')
    save('heat_sink_3d.java')
    progress('complete: stationary and transient results saved; checks=' + str(checks))
    if not summary['validated']:
        raise RuntimeError('A physical validation check failed; inspect validation.json before using the results')
    return summary
