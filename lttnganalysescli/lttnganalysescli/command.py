import linuxautomaton.automaton
#import lttnganalysescli
import argparse
import sys


class Command:
    def __init__(self, add_arguments_cb, enable_u_opt):
        self._add_arguments_cb = add_arguments_cb
        self._enable_u_opt = enable_u_opt
        self._create_automaton()

    def _error(self, msg, exit_code=1):
        print(msg, file=sys.stderr)
        sys.exit(exit_code)

    def _gen_error(self, msg, exit_code=1):
        self._error('Error: {}'.format(msg), exit_code)

    def _cmdline_error(self, msg, exit_code=1):
        self._error('Command line error: {}'.format(msg), exit_code)

    def _parse_args(self):
        ap = argparse.ArgumentParser(description=self._DESC)

        # common arguments
        ap.add_argument('-b', '--begin', help='begin timestamp')
        ap.add_argument('-e', '--end', help='end timestamp')

        # optional common argument
        if self._enable_u_opt:
            ap.add_argument('-u', '--uuu', help='famous U option')

        # specific arguments
        self._add_arguments_cb(ap)

        # version of the specific command
        #version = '%(prog)s v{}'.format(lttnganalysescli.__version__)
        ap.add_argument('-V', '--version', action='version',
                        version=self._VERSION)

        # parse arguments
        args = ap.parse_args()

        # common validation
        if args.begin != 'begin':
            self._cmdline_error('begin argument should be "begin"')

        if args.end != 'end':
            self._cmdline_error('end argument should be "end"')

        if self._enable_u_opt:
            if args.uuu != 'uuu':
                self._cmdline_error('uuu argument should be "uuu"')

        # transform and save arguments
        self._arg_begin = len(args.begin)
        self._arg_end = len(args.end)

        if self._enable_u_opt:
            self._arg_uuu = len(args.uuu)

        # save all arguments
        self._args = args

    def _create_automaton(self):
        self._automaton = linuxautomaton.automaton.Automaton()
