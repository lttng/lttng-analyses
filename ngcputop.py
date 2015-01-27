#!/usr/bin/env python3

import sys

sys.path += ['linuxautomaton', 'lttnganalyses', 'lttnganalysescli']

import lttnganalysescli.cputop


if __name__ == '__main__':
    lttnganalysescli.cputop.run()
