"""The mapper: the documents read from the input files, turned into the objects of the domain.

The entry points are :func:`~satedge_simulator.io.loading.network.load_network` and
:func:`~satedge_simulator.io.loading.workload.load_workload`. This package depends on the
domain, and on no adapter outside :mod:`satedge_simulator.io`. The modules of
:mod:`satedge_simulator.io` that read the files do not depend on this package.
"""
