from std.testing import assert_equal, assert_true
from prompt.formatter import format_llama3_single_turn


def test_single_turn_header_structure() raises:
    var out = format_llama3_single_turn("hello")
    assert_true(out.startswith("<|begin_of_text|>"))
    assert_true("<|start_header_id|>user<|end_header_id|>" in out)
    assert_true("<|eot_id|>" in out)
    assert_true(out.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n"))


def test_user_message_embedded() raises:
    var out = format_llama3_single_turn("what is 2+2")
    assert_true("what is 2+2" in out)


def test_empty_prompt_still_well_formed() raises:
    var out = format_llama3_single_turn("")
    assert_true(out.startswith("<|begin_of_text|>"))
    assert_true(out.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n"))


def test_special_chars_do_not_break_template() raises:
    var out = format_llama3_single_turn("hello\nworld\t<foo>")
    assert_true("hello\nworld\t<foo>" in out)


# Runnable entrypoint so `mojo run tests/test_formatter.mojo` exercises every test.
def main() raises:
    test_single_turn_header_structure()
    test_user_message_embedded()
    test_empty_prompt_still_well_formed()
    test_special_chars_do_not_break_template()
    print("OK: test_formatter (4 tests)")
