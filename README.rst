=======
sipster
=======


.. image:: https://img.shields.io/pypi/v/sipster.svg
        :target: https://pypi.python.org/pypi/sipster

.. image:: https://img.shields.io/travis/vodik/sipster.svg
        :target: https://travis-ci.org/vodik/sipster

.. image:: https://pyup.io/repos/github/vodik/sipster/shield.svg
     :target: https://pyup.io/repos/github/vodik/sipster/
     :alt: Updates


Toying around with using aiosip for agent/scenario testing similar to
how SIPp works. Lost of stuff to do, but looking very, very promising.

Currently almost non-functional, part of a fast answer scenario is
implemented, and that requires a customized aiosip install which I
haven't published yet - its stuff I want to get upstreamed.

To run it:

-------
Example
-------

.. code-block:: bash

    python -m sipster sipster.scenarios:fastanswer

----
TODO
----

- Upstream API changes where makes sense
- Integrate RTP and DTMF support from aiortp
- pytest integration via plugin
- Provide a set of useful general SIP compliance tests
