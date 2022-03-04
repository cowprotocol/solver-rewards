import csv
import os
from dataclasses import fields, astuple, dataclass

FILE_OUT_PATH = os.environ.get('FILE_OUT_PATH', './out')


@dataclass
class File:
    """Simple structure for declaring and passing around filenames"""
    name: str
    path: str = FILE_OUT_PATH

    def filename(self) -> str:
        """Returns the complete path to file"""
        return os.path.join(self.path, self.name)

    def __str__(self):
        return self.filename()


def write_to_csv(data_list: list, outfile: File):
    """Writes `data_list` to `filename` as csv"""
    print(f"dumping {len(data_list)} results to {outfile.name}")
    headers = [f.name for f in fields(data_list[0])]
    data_tuple = [astuple(x) for x in data_list]

    # Creates out path if it doesn't exist.
    if not os.path.exists(outfile.path):
        os.makedirs(outfile.path)

    with open(outfile.filename(), 'w', encoding='utf-8') as out_file:
        dict_writer = csv.DictWriter(out_file, headers, lineterminator='\n')
        dict_writer.writeheader()
        writer = csv.writer(out_file, lineterminator='\n')
        writer.writerows(data_tuple)
