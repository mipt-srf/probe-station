class BaseHandler:
    def __init__(self, parent):
        self.parent = parent

    @property
    def data(self):
        return self.parent.data

    @property
    def parameters(self):
        return self.parent.parameters

    def plot(self, **kwargs):
        raise NotImplementedError
