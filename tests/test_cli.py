import io
import json
import sys
from nose.tools import assert_raises, eq_, with_setup
from unittest.mock import patch, call

from luminoso_api.cli import main


@patch('luminoso_api.cli.LuminosoClient')
def test_save_token_without_token_errors(MockedClient):
    with patch.object(sys, 'argv', ['lumi-api', '-s', 'get', 'projects']):
        with assert_raises(SystemExit):
            main()
    assert not MockedClient.connect.called
    assert not MockedClient.save_token.called


@patch('luminoso_api.cli.LuminosoClient')
def test_save_token_with_token_saves_token_and_requests(MockedClient):
    MockedClient.connect().get.return_value = {}
    with patch.object(sys, 'argv', ['lumi-api', '-s', '-t', 'a token',
                                    'get', 'projects']):
        main()
    assert MockedClient.connect.called
    assert MockedClient.save_token.called
    assert MockedClient.connect().get.called


@patch('luminoso_api.cli.LuminosoClient')
def test_delete_prompts_and_continues(MockedClient):
    MockedClient.connect().delete.return_value = {}
    with patch('builtins.input', lambda x: 'y'):
        with patch.object(sys, 'argv', ['lumi-api', 'delete', 'projects']):
            main()
    assert MockedClient.connect.called
    assert MockedClient.connect().delete.called


@patch('luminoso_api.cli.LuminosoClient')
def test_delete_prompts_and_exits(MockedClient):
    MockedClient.connect().delete.return_value = {}
    with patch('builtins.input', lambda x: 'n'):
        with patch.object(sys, 'argv', ['lumi-api', 'delete', 'projects']):
            with assert_raises(SystemExit):
                main()
    assert MockedClient.connect.called
    assert not MockedClient.connect().delete.called


@patch('luminoso_api.cli.LuminosoClient')
def test_parameter_merging(MockedClient):
    MockedClient.connect().get.return_value = {}
    f = io.StringIO()
    f.write(json.dumps({"one": 1, "two": 2, "three": 3}))
    f.seek(0)
    with patch('builtins.open', return_value=f):
        with patch.object(sys, 'argv', ['lumi-api', 'get', 'projects',
                          'filename.json', '-p', 'one="won"',
                          '-j', '{"one": "once", "two": "too"}']):
            main()
    assert MockedClient.connect.called
    assert MockedClient.connect().get.called
    eq_(MockedClient.connect().get.call_args,
        call('projects', one='"won"', two='too', three=3))


hold_stdout = sys.stdout

def replace_stdout():
    global hold_stdout
    hold_stdout = sys.stdout
    sys.stdout = io.StringIO()


def restore_stdout():
    sys.stdout = hold_stdout


@with_setup(replace_stdout, restore_stdout)
@patch('luminoso_api.cli.LuminosoClient')
def test_csv_output(MockedClient):
    MockedClient.connect().get.return_value = [{'one': 'x', 'two': 'y'},
                                               {'one': 'z', 'two': 'a'}]
    with patch.object(sys, 'argv', ['lumi-api', '-c', 'get', 'projects']):
        main()
    assert MockedClient.connect.called
    assert not MockedClient.connect().delete.called
    buf = sys.stdout.getvalue()
    eq_(sys.stdout.getvalue(),
        "one,two\n"
        "x,y\n"
        "z,a\n")
