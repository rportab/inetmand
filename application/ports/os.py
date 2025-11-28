from abc import abstractmethod, ABC
from dataclasses import dataclass


@dataclass
class CommandOutput:
    code: int
    error: str
    output: str


class OS(ABC):
    @abstractmethod
    def run(self, args: list[str]) -> CommandOutput:
        pass

    @abstractmethod
    def iface_exists(self, iface: str) -> bool:
        pass
