"""Post processing API."""

import atooms.postprocessing as postprocessing
from atooms.postprocessing.partial import Partial
from atooms.trajectory import Trajectory
from atooms.trajectory.decorators import filter_species, change_species
from atooms.trajectory.utils import time_when_msd_is
from atooms.system.particle import distinct_species
from .helpers import linear_grid, logx_grid


def test_sk():
    import numpy
    import postprocessing.fourierspace_wrap
    #from postprocessing.fourierspace_wrap import fourierspace_module import sk_one
    from postprocessing.fourierspace_wrap import fourierspace_module
    nk = 10
    ndim, N = 3, 10
    pos = numpy.zeros((ndim, N))
    k0 = 1.0
    ikvec = numpy.ones((ndim, nk), dtype=numpy.int32)
    ikbin = numpy.ones(nk, dtype=numpy.int32)
    #sk = numpy.zeros(max(ikbin), dtype=numpy.complex64)
    sk = numpy.zeros(10)  #max(ikbin))
    kmax = 10
    fourierspace_module.sk_one(pos, k0, kmax, ikvec, ikbin, sk)
    print sk

def _get_trajectories(input_files, args):
    from atooms.trajectory import Sliced
    from atooms.core.utils import fractional_slice
    for input_file in input_files:
        with Trajectory(input_file, fmt=args['fmt']) as th:
            if args['species_layout'] is not None:
                th.register_callback(change_species, args['species_layout'])
            sl = fractional_slice(args['first'], args['last'], args['skip'], len(th))
            if th.block_size > 1:
                sl_start = (sl.start // th.block_size) * th.block_size if sl.start is not None else sl.start
                sl_stop = (sl.stop // th.block_size) * th.block_size if sl.stop is not None else sl.stop
                sl = slice(sl_start, sl_stop, sl.step)
            ts = Sliced(th, sl)
            yield ts

def _compat(args, fmt, species_layout=None):
    if 'fmt' not in args:
        args['fmt'] = fmt
    if 'species_layout' not in args:
        args['species_layout'] = species_layout
    return args

def gr(grandcanonical=False, fmt=None, species_layout=None,
       norigins=-1, *input_files, **global_args):
    """Radial distribution function."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        th._grandcanonical = grandcanonical
        postprocessing.RadialDistributionFunction(th, norigins=norigins).do()
        ids = distinct_species(th[-1].particle)
        if len(ids) > 1:
            Partial(postprocessing.RadialDistributionFunction, ids, th).do()

def sk(nk=20, dk=0.1, kmin=-1.0, kmax=15.0, ksamples=30, species_layout=None,
       norigins=-1, grandcanonical=False, fmt=None,
       trajectory_field=None, field=None, *input_files, **global_args):
    """Structure factor."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        ids = distinct_species(th[-1].particle)
        postprocessing.StructureFactor(th, None, norigins=norigins,
                                       trajectory_field=trajectory_field,
                                       field=field, kmin=kmin,
                                       kmax=kmax, nk=nk,
                                       ksamples=ksamples).do()
        if len(ids) > 1 and trajectory_field is None:
            Partial(postprocessing.StructureFactor, ids, th, None,
                    norigins=norigins, kmin=kmin,
                    kmax=kmax, nk=nk,
                    ksamples=ksamples).do()

def skopti(nk=20, dk=0.1, kmin=-1.0, kmax=15.0, ksamples=30, species_layout=None,
       norigins=-1, species=None, grandcanonical=False, fmt=None,
       trajectory_field=None, field=None, *input_files, **global_args):
    """Structure factor."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        ids = distinct_species(th[-1].particle)
        postprocessing.StructureFactorOptimized(th, None, norigins=norigins,
                                                trajectory_field=trajectory_field,
                                                field=field, kmin=kmin,
                                                kmax=kmax, nk=nk,
                                                ksamples=ksamples).do()
        if len(ids) > 1 and trajectory_field is None:
            Partial(postprocessing.StructureFactor, ids, th, None,
                    norigins=norigins, kmin=kmin,
                    kmax=kmax, nk=nk,
                    ksamples=ksamples).do()

def ik(trajectory_radius=None, nk=20, dk=0.1, kmin=-1.0, kmax=15.0,
       ksamples=30, norigins=-1, verbose=False, grandcanonical=False,
       fmt=None, species_layout=None, *input_files, **global_args):
    """Spectral density,"""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        if trajectory_radius is None:
            trajectory_radius = input_file
            ids = distinct_species(th[-1].particle)
            postprocessing.SpectralDensity(th, trajectory_radius,
                                           kgrid=None, norigins=norigins,
                                           kmin=kmin, kmax=kmax, nk=nk,
                                           ksamples=ksamples).do()

def msd(rmsd_target=-1.0, time_target=-1.0, time_target_fraction=-1.0,
        tsamples=30, norigins=50, sigma=1.0, func=linear_grid,
        fmt=None, species_layout=None, *input_files, **global_args):
    """Mean square displacement."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        dt = th.timestep
        if rmsd_target > 0:
            t_grid = [0.0] + func(dt, time_when_msd_is(th, rmsd_target**2),
                                  tsamples)
        else:
            if time_target > 0:
                t_grid = [0.0] + func(dt, min(th.total_time,
                                              time_target), tsamples)
            elif time_target_fraction > 0:
                t_grid = [0.0] + func(dt, time_target_fraction*th.total_time,
                                      tsamples)
            else:
                t_grid = [0.0] + func(dt, th.steps[-1]*dt, tsamples)
        ids = distinct_species(th[-1].particle)
        postprocessing.MeanSquareDisplacement(th, tgrid=t_grid,
                                              norigins=norigins,
                                              sigma=sigma).do()
        if len(ids) > 1:
            p = Partial(postprocessing.MeanSquareDisplacement, ids,
                        th, tgrid=t_grid, norigins=norigins, sigma=sigma).do()

def vacf(time_target=1.0, tsamples=30, func=linear_grid, fmt=None,
         species_layout=None, *input_files, **global_args):
    """Velocity autocorrelation function."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        t_grid = [0.0] + func(th.timestep, time_target, tsamples)
        postprocessing.VelocityAutocorrelation(th, t_grid).do()
        ids = distinct_species(th[-1].particle)
        if len(ids) > 1:
            Partial(postprocessing.VelocityAutocorrelation, ids, th, t_grid).do()

def fkt(time_target=1e9, tsamples=60, kmin=7.0, kmax=7.0, ksamples=1,
        dk=0.1, tag_by_name=False, func=logx_grid, fmt=None,
        species_layout=None, *input_files, **global_args):
    """Total intermediate scattering function."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        t_grid = [0.0] + func(th.timestep, time_target, tsamples)
        k_grid = linear_grid(kmin, kmax, ksamples)
        ids = distinct_species(th[0].particle)
        if len(ids) > 1:
            Partial(postprocessing.IntermediateScattering, ids, th, k_grid, t_grid).do()

def fskt(time_target=1e9, tsamples=60, kmin=7.0, kmax=8.0, ksamples=1,
         dk=0.1, nk=8, norigins=-1, tag_by_name=False, func=None,
         fmt=None, species_layout=None, total=False, *input_files, **global_args):
    """Self intermediate scattering function."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        if func is None:
            func = logx_grid
            t_grid = [0.0] + func(th.timestep, min(th.times[-1], time_target), tsamples)
        else:
            t_grid = [th.timestep*i for i in th.steps]
        k_grid = linear_grid(kmin, kmax, ksamples)
        if total:
            postprocessing.SelfIntermediateScattering(th, k_grid, t_grid,
                                                      nk, dk=dk, norigins=norigins).do()
        ids = distinct_species(th[-1].particle)
        if len(ids) > 1:
            Partial(postprocessing.SelfIntermediateScattering, ids,
                    th, k_grid, t_grid, nk, dk=dk, norigins=norigins).do()

def chi4qs(tsamples=60, a=0.3, time_target=-1.0, fmt=None, species_layout=None, total=False, *input_files, **global_args):
    """Dynamic susceptibility of self overlap."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        func = logx_grid
        if time_target > 0:
            time_target = min(th.total_time, time_target)
        else:
            time_target = th.total_time * 0.75
        t_grid = [0.0] + func(th.timestep, time_target, tsamples)
        if total:
            postprocessing.Chi4SelfOverlap(th, t_grid, a=a).do()
        ids = distinct_species(th[0].particle)
        if not total and len(ids) > 1:
            Partial(postprocessing.Chi4SelfOverlap, ids, th, t_grid, a=a).do()

def chi4qs_opti(tsamples=60, a=0.3, fmt=None, species_layout=None, *input_files, **global_args):
    """Dynamic susceptibility of self overlap."""
    global_args = _compat(global_args, fmt=fmt, species_layout=species_layout)
    for th in _get_trajectories(input_files, global_args):
        func = logx_grid
        time_target = th.total_time * 0.75
        t_grid = [0.0] + func(th.timestep, time_target, tsamples)
        postprocessing.Chi4SelfOverlapOpti(th, t_grid, a=a).do()
        ids = distinct_species(th[0].particle)
        if len(ids) > 1:
            Partial(postprocessing.Chi4SelfOverlapOpti, ids, th, t_grid, a=a).do()
