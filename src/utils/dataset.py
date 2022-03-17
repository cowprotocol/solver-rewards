"""Generic tools for manipulating datasets"""
from dataclasses import fields, is_dataclass
from typing import Any


def index_by(data_list: list[Any], field_str: str) -> dict[Any, Any]:
    """
    :param data_list: list of Account structures (i.e. those having account field).
    :param field_str: field of data class to index by
    :return: mapping of Account structures by account
    """
    if len(data_list) == 0:
        return {}
    sample = data_list[0]
    assert is_dataclass(sample), "Method only accepts lists of type dataclass"
    field_names = {field.name for field in fields(sample)}
    assert field_str in field_names, f'{type(sample)} has no field "{field_str}"'

    results = {}
    for entry in data_list:
        index_key = entry.__dict__.get(field_str)
        if index_key not in results:
            results[index_key] = entry
        else:
            raise IndexError(
                f'Attempting to index by non-unique index key "{index_key}"'
            )
    return results
