from abc import ABC, abstractmethod
from random import randint
SEED_TABLE_NAME = f"_pynonymizer_seed_fake_data_{randint(1, 99999)}"


class DatabaseProvider(ABC):
    @abstractmethod
    def create_database(self):
        pass

    @abstractmethod
    def drop_database(self):
        pass

    @abstractmethod
    def anonymize_database(self, database_strategy):
        pass

    @abstractmethod
    def restore_database(self, input_obj):
        pass

    @abstractmethod
    def dump_database(self, output_obj):
        pass
