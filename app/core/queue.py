class ProcessingQueue:
    """
    Manages the list of videos waiting for processing.
    """

    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def clear(self):
        self.items.clear()

    def get_all(self):
        return list(self.items)