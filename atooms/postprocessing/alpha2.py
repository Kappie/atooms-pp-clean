# This file is part of atooms
# Copyright 2010-2018, Daniele Coslovich

"""Non-Gaussian parameter."""

import numpy

from .helpers import linear_grid
from .correlation import Correlation, gcf_offset
from .helpers import adjust_skip, setup_t_grid, ifabsmm

__all__ = ['NonGaussianParameter']


class NonGaussianParameter(Correlation):

    """Non-Gaussian parameter."""

    symbol = 'alpha_2(t)'
    short_name = 'alpha2'
    long_name = 'non-Gaussian parameter'
    phasespace = ['pos-unf']

    def __init__(self, trajectory, tgrid=None, norigins=50, nsamples=30):
        Correlation.__init__(self, trajectory, tgrid)
        if self.grid is None:
            self.grid = linear_grid(0.0, self.trajectory.total_time * 0.75, nsamples)
        self._discrete_tgrid = setup_t_grid(self.trajectory, self.grid)
        self.skip = adjust_skip(self.trajectory, norigins)

    def _compute(self):
        def alpha_2(x, y):
            if x is y:
                return 0.0
            dx2 = (x - y)**2
            dr2 = numpy.sum(dx2) / float(x.shape[0])
            dr4 = numpy.sum(numpy.sum(dx2, axis=1)**2) / float(x.shape[0])
            return 3 * dr4 / (5 * dr2**2) - 1

        self.grid, self.value = gcf_offset(alpha_2, self._discrete_tgrid, self.skip,
                                           self.trajectory.steps, self._pos_unf)
        self.grid = [ti * self.trajectory.timestep for ti in self.grid]

    def analyze(self):
        try:
            self.results['t_star'], self.results['a2_star'] = ifabsmm(self.grid, self.value)[1]
        except ZeroDivisionError:
            pass
