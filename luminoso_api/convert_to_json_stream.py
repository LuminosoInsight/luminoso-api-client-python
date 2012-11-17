from itertools import islice, chain
from luminoso_api import LuminosoClient
import json
import codecs
import csv
import chardet
import logging
import unicodedata
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def transcode(input_filename, output_filename):
    if output_filename.endswith('.json'):
        LOG.warn("Changing .json to .jsons, because this program outputs a "
                 "JSON stream format that is not technically JSON itself.")
        output_filename += 's'
    output = codecs.open(output_filename, 'w', encoding='utf-8')
    for entry in open_json_or_csv_somehow(input_filename):
        print >> output, json.dumps(entry, ensure_ascii=False)
    output.close()

def open_json_or_csv_somehow(filename):
    format = None
    if filename.endswith('.csv'):
        format = 'csv'
    elif filename.endswith('.jsons'):
        format = 'jsons'
    else:
        opened = open(filename)
        line = opened.readline()
        if (line.count('{') == line.count('}') and
            line.count('[') == line.count(']')):
            # This line contains a complete JSON document. This probably
            # means it's in linewise JSON ('.jsons') format, unless the
            # whole file is on one line.
            char = ' '
            while char.isspace():
                char = opened.read()
                if char == '':
                    format = 'json'
                    break
            if format is None:
                format = 'jsons'
        else:
            format = 'json'
        opened.close()

    if format == 'json':
        return json.load(open(filename), encoding='utf-8')
    elif format == 'csv':
        return open_csv_somehow(filename)
    else:
        return stream_json_lines(filename)

def detect_file_encoding(filename):
    opened = open(filename)
    sample = opened.read(2 ** 16)

    encoding = chardet.detect(sample)['encoding']
    if encoding is None:
        encoding = 'utf-8'
    elif encoding == 'ISO-8859-2':
        LOG.warn("This file could be either in ISO-8859-2 or MacRoman encoding.")
        LOG.warn("ISO-8859-2 (Latin-2) is an old standard for ASCII-like text "
                 "that particularly supports characters found in Eastern "
                 "European languages.")
        LOG.warn("MacRoman is how Mac OS 9 and earlier saved text, and "
                 "Microsoft Office still uses it sometimes.")
        LOG.warn("We're going to guess it's MacRoman, but we might be wrong.")
        LOG.warn("You might want to remedy this by saving the file in UTF-8.")
        encoding = 'macroman'

    try:
        codecs.lookup(encoding)
    except LookupError:
        LOG.warn("This file might be encoded as %r, but Python doesn't "
                 "know how to read that. Falling back on ISO-8859-1, "
                 "but it's likely to be wrong." % encoding)
        encoding = 'iso-8859-1'
    opened.close()
    return encoding

def stream_json_lines(filename):
    for line in open(filename):
        line = line.strip()
        if line:
            yield json.loads(line, encoding='utf-8')

def open_csv_somehow(filename):
    encoding = detect_file_encoding(filename)
    csvfile = open(filename, 'rU')
    reader = csv.reader(csvfile, dialect='excel')
    header = reader.next()
    header = [cell.decode(encoding).lower() for cell in header]
    return read_csv(reader, header, encoding)

def read_csv(reader, header, encoding):
    for row in reader:
        if len(row) == 0:
            continue
        row = [cell.decode(encoding) for cell in row]
        row_list = zip(header, row)
        row_dict = dict(row_list)
        if len(row_dict['text']) == 0:
            continue
        row_dict['text'] = unicodedata.normalize(
            'NFKC', row_dict['text'].strip()
        )
        if 'date' in row_dict:
            row_dict['date'] = int(row_dict['date'])
        if 'query' in row_dict or 'subset' in row_dict:
            queries = [cell[1] for cell in row_list
                       if cell[0] == 'query' or cell[0] == 'subset']
            row_dict['queries'] = queries
            if 'query' in row_dict:
                del row_dict['query']
            if 'subset' in row_dict:
                del row_dict['subset']
        yield row_dict

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()
    transcode(args.input, args.output)

if __name__ == '__main__':
    main()
