from dataclasses import dataclass


VALID_TONE_SOURCES = ("daw", "youtube", "microphone")


@dataclass(frozen=True)
class ToneSourceSession:
    """Identity for one exclusive tone-detection source session.

    Slow YouTube jobs and audio callbacks can finish after the user has moved
    to another source.  The monotonically increasing generation makes those
    late results harmless instead of letting them overwrite the live source.
    """

    source: str
    generation: int


class ToneSourceCoordinator:
    def __init__(self, initial_source: str = "daw"):
        self._generation = 0
        self._source = self._validated(initial_source)

    @staticmethod
    def _validated(source: str) -> str:
        value = str(source or "").strip().lower()
        if value not in VALID_TONE_SOURCES:
            raise ValueError(f"Unsupported tone source: {source}")
        return value

    @property
    def source(self) -> str:
        return self._source

    @property
    def session(self) -> ToneSourceSession:
        return ToneSourceSession(self._source, self._generation)

    def switch(self, source: str) -> ToneSourceSession:
        self._source = self._validated(source)
        self._generation += 1
        return self.session

    def accepts(self, source: str, generation: int) -> bool:
        return (str(source or "").lower() == self._source
                and int(generation) == self._generation)
