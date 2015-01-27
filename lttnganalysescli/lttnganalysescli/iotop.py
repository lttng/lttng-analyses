from .command import Command
import lttnganalyses.iotop
import random


class Iotop(Command):
    _VERSION = '1.2.3'
    _DESC = """The iotop command blabla bla.
It also does this and that."""

    def __init__(self):
        super().__init__(self._add_arguments, True)

    def _validate_transform_args(self):
        # split?
        self._arg_split_count = None
        self._arg_split = self._args.split

        # split count if splitting?
        if self._arg_split:
            if self._args.split_count is None:
                self._cmdline_error('you must specify --split-count '
                                    'with --split')
            else:
                self._arg_split_count = self._args.split_count

        # path
        self._arg_path = self._args.path

    def run(self):
        # parse arguments first
        self._parse_args()

        # validate, transform and save specific arguments
        self._validate_transform_args()

        # everything processed at this point
        print('begin: {}'.format(self._arg_begin))
        print('end: {}'.format(self._arg_end))
        print('uuu: {}'.format(self._arg_uuu))
        print('split: {}'.format(self._arg_split))
        print('split-count: {}'.format(self._arg_split_count))
        print('path: {}'.format(self._arg_path))
        print('---')

        # create the appropriate analysis/analyses
        self._create_analysis()

        # run the analysis
        self._run_analysis()

        # print results
        self._print_results()

    def _create_analysis(self):
        self._analysis = lttnganalyses.iotop.Iotop(self._automaton.state,
                                                   self._arg_split,
                                                   self._arg_split_count)

    def _run_analysis(self):
        # event (demo)
        class Event:
            def __init__(self):
                self.cond = bool(random.getrandbits(1))
                self.name = 'hello'

        # loop of events here
        for i in range(random.randint(5000, 10000)):
            ev = Event()

            # feed automaton
            self._automaton.process_event(ev)

            # feed analysis
            self._analysis.process_event(ev)

    def _print_results(self):
        print('event count: {}'.format(self._analysis.event_count))
        print('buckets:')

        for index, count in enumerate(self._analysis.buckets):
            print('  {:04d}: {}'.format(index, count))

    def _add_arguments(self, ap):
        # specific argument
        ap.add_argument('-s', '--split', action='store_true', help='split')
        ap.add_argument('-c', '--split-count', type=int, help='split count')

        # could be a common argument too
        ap.add_argument('path', help='trace path')


# entry point
def run():
    # create command
    iotopcmd = Iotop()

    # execute command
    iotopcmd.run()
