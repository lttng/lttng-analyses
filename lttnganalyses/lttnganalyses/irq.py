from .analysis import Analysis


class IrqAnalysis(Analysis):
    def __init__(self, state):
        self._state = state

    def process_event(self, ev):
        pass
