"""Random numbers for the simulation: the libraries of Leemis and Park, without global state.

``rngs`` is the multi-stream Lehmer generator, ``rvgs`` turns its uniforms into random
variates, ``rvms`` holds the distribution functions the output analysis needs. They follow
the Python translation by Philip Steele of the C libraries by Steve Park and Dave Geyer (see
``THIRD_PARTY_NOTICES.md``).
"""
