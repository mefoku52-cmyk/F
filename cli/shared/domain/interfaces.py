from abc import ABC, abstractmethod


class IUser(ABC):
    @abstractmethod
    def get_id(self):
        pass


class IToken(ABC):
    @abstractmethod
    def get_user(self) -> "IUser":
        pass


class IRepository(ABC):
    @abstractmethod
    def save(self, entity):
        pass

    @abstractmethod
    def get(self, id):
        pass

    @abstractmethod
    def delete(self, id):
        pass
