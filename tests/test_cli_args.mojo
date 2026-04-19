from std.testing import assert_equal, assert_true
from std.collections import List

from cli.args import parse_args, argv_to_list, CliArgs, ParseResult


def make_args(strs: List[String]) raises -> CliArgs:
    var result = parse_args(strs)
    var args = result.args.copy()
    var err = result.error.copy()
    if len(err) > 0:
        raise Error(String("parse error: ") + err)
    return args^


def test_print_mode() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("hello world"))
    var args = make_args(raw)
    assert_equal(args.mode, String("print"))
    assert_equal(args.prompt, String("hello world"))


def test_version_mode() raises:
    var raw = List[String]()
    raw.append(String("--version"))
    var args = make_args(raw)
    assert_equal(args.mode, String("version"))


def test_model_flag() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("hi"))
    raw.append(String("--model"))
    raw.append(String("meta-llama/Llama-3.2-1B"))
    var args = make_args(raw)
    assert_equal(args.model, String("meta-llama/Llama-3.2-1B"))


def test_max_new_tokens() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("hi"))
    raw.append(String("--max-new-tokens"))
    raw.append(String("128"))
    var args = make_args(raw)
    assert_equal(args.max_new_tokens, 128)


def test_no_context_files() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("hi"))
    raw.append(String("--no-context-files"))
    var args = make_args(raw)
    assert_true(args.no_context_files)


def test_tools_csv() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("hi"))
    raw.append(String("--tools"))
    raw.append(String("read,bash,grep"))
    var args = make_args(raw)
    assert_equal(len(args.tools), 3)


def test_unknown_flag_error() raises:
    var raw = List[String]()
    raw.append(String("--unknown-flag-xyz"))
    var result = parse_args(raw)
    assert_true(len(result.error) > 0)


def test_default_model() raises:
    var raw = List[String]()
    raw.append(String("-p"))
    raw.append(String("test"))
    var args = make_args(raw)
    assert_equal(args.model, String("modularai/Llama-3.1-8B-Instruct-GGUF"))


def main() raises:
    test_print_mode()
    test_version_mode()
    test_model_flag()
    test_max_new_tokens()
    test_no_context_files()
    test_tools_csv()
    test_unknown_flag_error()
    test_default_model()
    print("All CLI args tests passed!")
