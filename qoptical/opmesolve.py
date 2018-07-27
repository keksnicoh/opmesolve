# -*- coding: utf-8 -*-
""" optical lindblad master equation solver.

    :author: keksnicoh
"""
import numpy as np
from .util import *
from . import settings
from .kernel_qutip import QutipKernel

DTYPE_JUMP = np.dtype([
    ('I', settings.DTYPE_INT,     2),
    ('d', settings.DTYPE_COMPLEX, 1),
    ('w', settings.DTYPE_FLOAT,   1),
    ('n', settings.DTYPE_FLOAT,   1),
])
class ReducedSystem():
    """ classification of a reduced system in an optical environment.

        this contains the most basic information to compile a kernel
        which then performs integration and manages runtime state.
    """

    def __init__(self, h0, dipole=None, n_htl=0, n_e_ops=0, tw=None, jumps=None):
        """ Creates a reduced system for time independent Hamilton `h_0`.
            The ReducedSystem couples thru `dipole` to an optical bath.
            A time dependent unitary evolution can be setup thru `n_htl`
            time dependent Hamiltonians of form ``H_i(t) = H_i * f_i(t)``.

            If no transition frequencies `tw` given, all possible combination
            of transition frequencies are generated.

            The `n_e_ops` allows to define how many observables are calculated
            during integration. Note that if `n_e_ops > 0` then it won't be
            possible to access final state ``rho(t_f)``.

            XXX:
            ----
            - Allow defintition of jumps
        """
        # normalize
        h0      = sqmat(h0).astype(settings.DTYPE_COMPLEX)
        dipole  = None if dipole is None else sqmat(dipole)
        tw      = np.array(tw, dtype=settings.DTYPE_FLOAT) \
                  if tw is not None else None
        n_htl   = int(n_htl)
        n_e_ops = int(n_e_ops)

        # validate
        assert tw is None or jumps is None,             'overdetermined args'
        assert np.all(h0.H == h0),                      'h0 must be hermitian'
        if dipole is not None:
            assert np.all(dipole.H == dipole),          'dipole transition moment must be hermitian'
            assert np.all(dipole.shape == h0.shape),    'dipole transition moment must match h0'
        assert n_htl >= 0,                              'n_htl must 0 or positive.'
        assert n_e_ops >= 0,                            'n_e_ops must 0 or positive.'
        assert tw is None or np.all(tw > 0),            'transition frequencies must be greater than zero'

        self.h0      = h0
        self.dipole  = dipole
        self.tw      = tw
        self.n_htl   = n_htl
        self.n_e_ops = n_e_ops

        self.ev, self.s = eigh(h0)
        self.jumps      = None

    def get_jumps(self):
        """ returns jumping configuration for the system """
        if self.jumps is not None:
            return self.jumps

        if self.tw is None:
            self.tw = self.get_possible_tw()

        assert np.all(self.tw > 0),  'transition frequencies must be greater than zero'

        # sort transition frequencies to get a sorted
        # list of jumps later on.
        self.tw = sorted(self.tw)

        # create list of jumps and distribute by degeneracy
        # of the jump.
        jumps = [None for _ in range(self.h0.shape[0])]
        for w in self.tw:
            tr       = self.get_transitions(w)
            i        = len(tr) - 1
            jumps[i] = tr if jumps[i] is None else np.concatenate((jumps[i], tr))

        self.jumps = jumps
        return self.jumps


    def get_possible_tw(self):
        """ returns all possible transition frequencies
            bewteen the energy eigenstates of the system.
        """
        ev = self.ev
        f  = np.array([np.abs(a - b) for a in ev for b in ev if not np.isclose(a, b)])
        return f[~(np.triu(np.abs(f[:, None] - f) <= settings.EQ_COMPARE_TOL, 1)).any(0)]


    def get_transitions(self, w):
        """ returns an array of `DTYPE_JUMP` describing the
            possible transitions at frequency `w`.
        """

        # dipole transition moment
        dij = (lambda i, j: (self.s[j] @ self.dipole @ self.s[i].T.conj())[0, 0]) \
              if self.dipole is not None else \
              (lambda i, j: 1)

        return np.array([((i, j), dij(i, j), np.abs(e1 - e2), 0)
                for i, e1 in enumerate(self.ev)
                for j, e2 in enumerate(self.ev)
                if np.isclose(e1 - e2, w)], dtype=DTYPE_JUMP)


    def thermal_state(self, T):
        """ creates a thermal state at
            temperature ``T``. If T defines many
            temperatures then a list of thermal
            states is returned.
        """
        return unvectorize(
            np.diag(thermal_dist(t, self.ev)) \
                .astype(settings.DTYPE_COMPLEX)
            for t in vectorize(T)
        )


    def pure_energy_state(self, i):
        """ creates a state |i><i| where |i> is
            the ``i``-th energy eigenstate. If i defines
            many states then a list of pure
            energy states is returned.
        """
        return unvectorize(
            ketbra(self.s, i, i)
            for i in vectorize(i)
        )


def opmesolve(H, rho0, t_bath, y_0, tlist, dipole=None, tw=None, e_ops=[], kernel="QuTip"):

    if len(H) == 0:
        raise ValueError()
    if isinstance(H, list):
        if len(H) == 1:
            h0, htl = H[0], []
        else:
            h0, htl = H[0], H[1:]
    else:
        h0, htl = H, []

    system = ReducedSystem(h0      = h0,
                           dipole  = dipole,
                           tw      = tw,
                           n_htl   = len(htl),
                           n_e_ops = len(e_ops))

    # get kernel
    if isinstance(kernel, str):
        if kernel == "QuTip":
            kernel = QutipKernel(system)
        else:
            raise ValueError('invalid kernel {}.'.format(kernel))
    else:
        raise ValueError('invalid kernel.')

    kernel.compile()
    kernel.sync(state=rho0,
                htl=htl,
                t_bath=t_bath,
                y_0=y_0,
                e_ops=e_ops if len(e_ops) else None)

    return kernel.run(tlist)



