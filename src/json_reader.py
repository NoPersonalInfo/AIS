"""
COPYRIGHT © BSH HOME APPLIANCES GROUP  2020

ALLE RECHTE VORBEHALTEN. ALL RIGHTS RESERVED.

The reproduction, transmission or use of this document or its contents is not permitted without express
written authority. Offenders will be liable for damages. All rights, including rights created by  patent
grant or registration of a utility model or design, are reserved.
"""
import json
from abc import ABC
from abc import abstractmethod


class JsonDataManager:

    @staticmethod
    def save_data_to(path, data):
        '''
        :param path: path to the new .json file.
        :param data: json feasible datatype.
        '''
        with open(path, "w") as file:
            json.dump(data, file, sort_keys=True, indent=4)

    @staticmethod
    def load_data_from(path):
        '''
        Loads a given .json file.
        :param path: Path to json file.
        :return: Entire Data of the
        chosen .json file.
        '''
        with open(path) as file:
            return json.load(file)


class JsonConvertable(ABC):
    '''
    A class inherting from this class
    implements functionalities for using
    json in combination with JsonDataManager.
    '''

    @abstractmethod
    def convert_python_to_json(self):
        '''
        Converts a python datastructure
        to a json feasible datatype
        '''
        pass

    @staticmethod
    @abstractmethod
    def convert_json_to_python(data, additional_parameters=None):
        '''
        Converts a json Datatype back to the original Instance.
        :param additional_parameters: Holds more information for
        reconversion if need be.
        '''
        pass
