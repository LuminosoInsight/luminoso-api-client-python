"""
This file helps to build a JSON stream from arbitrary kinds of input,
including messy Excel CSV files.

The output this produces -- either in a real file, or in a temporarily
file that it returns a reference to -- is a JSON stream (.jsons), a file
with one JSON object per line.

Its input can be:

- A CSV in the "excel" dialect, with a header row
  - Preferably, this file is UTF-8 encoded.
  - However, this can read files in many other encodings, including MacRoman,
    which Excel sometimes produces and which trips up chardet.
- A single JSON list of the documents
- Or a JSON stream, which will effectively be validated before uploading.

The dictionary keys in JSON, or the column labels in CSV, should be the
document properties defined in the documentation at
https://analytics.luminoso.com/api/v4.
"""
from __future__ import unicode_literals
import json
import io
import csv
import ftfy
import logging
import unicodedata
import sys
import tempfile
from datetime import datetime
from .compat import PY3, string_type
logger = logging.getLogger(__name__)


def transcode(input_filename, output_filename=None, date_format=None):
    """
    Convert a JSON or CSV file of input to a JSON stream (.jsons). This
    kind of file can be easily uploaded using `luminoso_api.upload`.
    """
    if output_filename is None:
        # transcode to standard output
        output = sys.stdout
    else:
        if output_filename.endswith('.json'):
            logger.warning("Changing .json to .jsons, because this program "
                           "outputs a JSON stream format that is not "
                           "technically JSON itself.")
            output_filename += 's'
        output = open(output_filename, 'w')

    for entry in open_json_or_csv_somehow(input_filename,
                                          date_format=date_format):
        output.write(json.dumps(entry, ensure_ascii=False).encode('utf-8'))
        output.write('\n')
    output.close()


def transcode_to_stream(input_filename, date_format=None):
    """
    Read a JSON or CSV file and convert it into a JSON stream, which will
    be saved in an anonymous temp file.
    """
    tmp = tempfile.TemporaryFile()
    for entry in open_json_or_csv_somehow(input_filename,
                                          date_format=date_format):
        tmp.write(json.dumps(entry, ensure_ascii=False).encode('utf-8'))
        tmp.write(b'\n')
    tmp.seek(0)
    return tmp


def open_json_or_csv_somehow(filename, date_format=None):
    """
    Deduce the format of a file, within reason.

    - If the filename ends with .csv or .txt, it's csv.
    - If the filename ends with .jsons, it's a JSON stream (conveniently the
      format we want to output).
    - If the filename ends with .json, it could be a legitimate JSON file, or
      it could be a JSON stream, following a nonstandard convention that many
      people including us are guilty of. In that case:
      - If the first line is a complete JSON document, and there is more in the
        file besides the first line, then it is a JSON stream.
      - Otherwise, it is probably really JSON.
    - If the filename does not end with .json, .jsons, or .csv, we have to guess
      whether it's still CSV or tab-separated values or something like that.
      If it's JSON, the first character would almost certainly have to be a
      bracket or a brace. If it isn't, assume it's CSV or similar.
    """
    fileformat = None
    if filename.endswith('.csv'):
        fileformat = 'csv'
    elif filename.endswith('.jsons'):
        fileformat = 'jsons'
    else:
        with open(filename) as opened:
            line = opened.readline()
            if line[0] not in '{[' and not filename.endswith('.json'):
                fileformat = 'csv'
            else:
                if (line.count('{') == line.count('}') and
                    line.count('[') == line.count(']')):
                    # This line contains a complete JSON document. This probably
                    # means it's in linewise JSON ('.jsons') format, unless the
                    # whole file is on one line.
                    char = ' '
                    while char.isspace():
                        char = opened.read()
                        if char == '':
                            fileformat = 'json'
                            break
                    if fileformat is None:
                        fileformat = 'jsons'
                else:
                    fileformat = 'json'

    if fileformat == 'json':
        stream = json.load(open(filename), encoding='utf-8')
    elif fileformat == 'csv':
        stream = open_csv_somehow(filename)
    else:
        stream = stream_json_lines(filename)

    return _normalize_data(stream, date_format=date_format)


def _normalize_data(stream, date_format=None):
    """
    This function is meant to normalize data for upload to the Luminoso
    Analytics system. Currently it only normalizes dates.

    If date_format is not specified, or if there's no date in a particular doc,
    the the doc is yielded unchanged.
    """
    for doc in stream:
        if 'date' in doc and date_format is not None:
            try:
                doc['date'] = _convert_date(doc['date'], date_format)
            except ValueError:
                # ValueErrors cover the cases when date_format does not match
                # the actual format of the date, both for epoch and non-epoch
                # times.
                logger.exception('%s does not match the date format %s;'
                                 % (doc['date'], date_format))
        yield doc


def _convert_date(date_string, date_format):
    """
    Convert a date in a given format to epoch time. Mostly a wrapper for
    datetime's strptime.
    """
    if date_format != 'epoch':
        return datetime.strptime(date_string, date_format).timestamp()
    else:
        return float(date_string)


def detect_file_encoding(filename):
    """
    Use ftfy to detect the encoding of a file, based on a sample of its
    first megabyte.

    ftfy's encoding detector is limited. The only encodings it can detect are
    UTF-8, CESU-8, UTF-16, Windows-1252, and occasionally MacRoman. But it
    does much better than chardet.
    """
    with open(filename, 'rb') as opened:
        sample = opened.read(2 ** 20)
        _, encoding = ftfy.guess_bytes(sample)
        return encoding


def stream_json_lines(file):
    """
    Load a JSON stream and return a generator, yielding one object at a time.
    """
    if isinstance(file, string_type):
        file = open(file, 'rb')
    for line in file:
        line = line.strip()
        if line:
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            yield json.loads(line)


def open_csv_somehow(filename):
    """
    Given a filename that we're told is a CSV file, detect its encoding,
    parse its header, and return a generator yielding its rows as dictionaries.
    """
    if PY3:
        return open_csv_somehow_py3(filename)
    else:
        return open_csv_somehow_py2(filename)


def transcode_to_utf8(filename, encoding):
    """
    Convert a file in some other encoding into a temporary file that's in
    UTF-8.
    """
    tmp = tempfile.TemporaryFile()
    for line in io.open(filename, encoding=encoding):
        tmp.write(line.strip('\uFEFF').encode('utf-8'))

    tmp.seek(0)
    return tmp


def open_csv_somehow_py2(filename):
    """
    Open a CSV file using Python 2's CSV module, working around the deficiency
    where it can't handle the null bytes of UTF-16.
    """
    encoding = detect_file_encoding(filename)
    if encoding.startswith('UTF-16'):
        csvfile = transcode_to_utf8(filename, encoding)
        encoding = 'UTF-8'
    else:
        csvfile = open(filename, 'rU')
    line = csvfile.readline()
    csvfile.seek(0)

    if '\t' in line:
        # tab-separated
        reader = csv.reader(csvfile, delimiter='\t')
    else:
        reader = csv.reader(csvfile, dialect='excel')

    header = reader.next()
    header = [cell.decode(encoding).lower().strip() for cell in header]
    encode_fn = lambda x: x.decode(encoding, 'replace')
    return _read_csv(reader, header, encode_fn)


def open_csv_somehow_py3(filename):
    encoding = detect_file_encoding(filename)
    csvfile = open(filename, 'rU', encoding=encoding, newline='')
    line = csvfile.readline()
    csvfile.seek(0)

    if '\t' in line:
        # tab-separated
        reader = csv.reader(csvfile, delimiter='\t')
    else:
        reader = csv.reader(csvfile, dialect='excel')

    header = next(reader)
    header = [cell.lower().strip() for cell in header]
    encode_fn = lambda x: x
    return _read_csv(reader, header, encode_fn)


def _read_csv(reader, header, encode_fn):
    """
    Given a constructed CSV reader object, a header row that we've read, and
    a detected encoding, yield its rows as dictionaries.
    """
    for row in reader:
        if len(row) == 0:
            continue
        row = [encode_fn(cell) for cell in row]
        row_list = zip(header, row)
        row_dict = dict(row_list)
        if len(row_dict['text']) == 0:
            continue
        row_dict['text'] = unicodedata.normalize(
            'NFKC', row_dict['text'].strip()
        )
        if row_dict.get('title') == '':
            del row_dict['title']
        if 'date' in row_dict:
            # We handle dates further in open_json_or_csv_somehow
            if row_dict['date'] == '':
                del row_dict['date']
        if 'subset' in row_dict:
            subsets = [cell[1] for cell in row_list
                       if cell[1] != '' and cell[0] == 'subset']
            if subsets:
                row_dict['subsets'] = subsets
            if 'subset' in row_dict:
                del row_dict['subset']
        yield row_dict


def main():
    """
    Handle command line arguments to convert a file to a JSON stream as a
    script.
    """
    logging.basicConfig(level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser(
        description="Translate CSV or JSON input to a JSON stream, or verify "
                    "something that is already a JSON stream."
    )
    parser.add_argument('input',
        help='A CSV, JSON, or JSON stream file to read.')
    parser.add_argument('output', nargs='?', default=None,
        help="The filename to output to. Recommended extension is .jsons. "
             "If omitted, use standard output.")
    args = parser.parse_args()
    transcode(args.input, args.output)


if __name__ == '__main__':
    main()
