from testing import assert_equal, assert_true
from prompt.formatter import format_llama3_single_turn


def test_single_turn_header_structure():
    var out = format_llama3_single_turn("hello")
    assert_true(out.startswith("<|begin_of_text|>"))
    assert_true("<|start_header_id|>user<|end_header_id|>" in out)
    assert_true("<|eot_id|>" in out)
    assert_true(out.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n"))


def test_user_message_embedded():
    var out = format_llama3_single_turn("what is 2+2")
    assert_true("what is 2+2" in out)


def test_empty_prompt_still_well_formed():
    var out = format_llama3_single_turn("")
    assert_true(out.startswith("<|begin_of_text|>"))
    assert_true(out.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n"))


def test_special_chars_do_not_break_template():
    var out = format_llama3_single_turn("hello\nworld\t<foo>")
    assert_true("hello\nworld\t<foo>" in out)
