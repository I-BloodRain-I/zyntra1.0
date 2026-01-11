import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

def test_normalize_cmyk_valid_string(canvas):
    result = canvas._normalize_cmyk("10,20,30,40")
    assert result == "10,20,30,40"

def test_normalize_cmyk_with_spaces(canvas):
    result = canvas._normalize_cmyk("10 , 20 , 30 , 40")
    assert result == "10,20,30,40"

def test_normalize_cmyk_floats(canvas):
    result = canvas._normalize_cmyk("10.5,20.7,30.1,40.9")
    assert "10.5" in result and "20.7" in result

def test_normalize_cmyk_integers_from_floats(canvas):
    result = canvas._normalize_cmyk("10.0,20.0,30.0,40.0")
    assert result == "10,20,30,40"

def test_normalize_cmyk_empty_string(canvas):
    result = canvas._normalize_cmyk("")
    assert result == "0,0,0,0"

def test_normalize_cmyk_none_value(canvas):
    result = canvas._normalize_cmyk(None)
    assert result == "0,0,0,0"

def test_normalize_cmyk_less_than_4_parts(canvas):
    result = canvas._normalize_cmyk("10,20")
    assert result == "10,20,0,0"

def test_normalize_cmyk_more_than_4_parts(canvas):
    result = canvas._normalize_cmyk("10,20,30,40,50,60")
    assert result == "10,20,30,40"

def test_normalize_cmyk_non_numeric_parts(canvas):
    result = canvas._normalize_cmyk("abc,20,xyz,40")
    assert result == "0,20,0,40"

def test_normalize_cmyk_single_value(canvas):
    result = canvas._normalize_cmyk("50")
    assert result == "50,0,0,0"

def test_normalize_cmyk_three_values(canvas):
    result = canvas._normalize_cmyk("10,20,30")
    assert result == "10,20,30,0"

def test_normalize_cmyk_negative_values(canvas):
    result = canvas._normalize_cmyk("-10,-20,-30,-40")
    assert result == "-10,-20,-30,-40"

def test_normalize_cmyk_zero_values(canvas):
    result = canvas._normalize_cmyk("0,0,0,0")
    assert result == "0,0,0,0"

def test_normalize_cmyk_large_values(canvas):
    result = canvas._normalize_cmyk("100,100,100,100")
    assert result == "100,100,100,100"

def test_normalize_cmyk_mixed_format(canvas):
    result = canvas._normalize_cmyk("10.5, 20 , abc , 40.0")
    assert "10.5" in result and "20" in result and "0" in result and "40" in result

def test_normalize_cmyk_empty_parts(canvas):
    result = canvas._normalize_cmyk("10,,30,")
    assert result == "10,0,30,0"

def test_normalize_cmyk_only_commas(canvas):
    result = canvas._normalize_cmyk(",,,")
    assert result == "0,0,0,0"

def test_normalize_cmyk_numeric_value(canvas):
    result = canvas._normalize_cmyk(50)
    assert result == "50,0,0,0"

def test_normalize_cmyk_whitespace_only(canvas):
    result = canvas._normalize_cmyk("   ")
    assert result == "0,0,0,0"

def test_normalize_cmyk_tab_separated(canvas):
    result = canvas._normalize_cmyk("10\t20\t30\t40")
    assert result

def test_normalize_cmyk_special_chars(canvas):
    result = canvas._normalize_cmyk("10@20#30$40")
    assert result

def test_normalize_cmyk_very_long_string(canvas):
    result = canvas._normalize_cmyk("1" * 1000)
    assert result

def test_normalize_cmyk_unicode_numbers(canvas):
    result = canvas._normalize_cmyk("१०,२०,३०,४०")
    assert result

def test_normalize_cmyk_hex_values(canvas):
    result = canvas._normalize_cmyk("0x10,0x20,0x30,0x40")
    assert result

def test_normalize_cmyk_fractional_negative(canvas):
    result = canvas._normalize_cmyk("-10.5,-20.7,-30.1,-40.9")
    assert result

def test_normalize_cmyk_infinity_value(canvas):
    result = canvas._normalize_cmyk("inf,20,30,40")
    assert result

def test_normalize_cmyk_nan_value(canvas):
    result = canvas._normalize_cmyk("nan,20,30,40")
    assert result

def test_normalize_cmyk_very_small_floats(canvas):
    result = canvas._normalize_cmyk("0.001,0.002,0.003,0.004")
    assert result

def test_normalize_cmyk_very_large_floats(canvas):
    result = canvas._normalize_cmyk("999999.999,888888.888,777777.777,666666.666")
    assert result

def test_normalize_cmyk_leading_zeros(canvas):
    result = canvas._normalize_cmyk("00010,00020,00030,00040")
    assert result == "10,20,30,40"

def test_normalize_cmyk_trailing_comma(canvas):
    result = canvas._normalize_cmyk("10,20,30,40,")
    assert result == "10,20,30,40"

def test_normalize_cmyk_leading_comma(canvas):
    result = canvas._normalize_cmyk(",10,20,30,40")
    assert result == "0,10,20,30"

def test_normalize_cmyk_multiple_commas(canvas):
    result = canvas._normalize_cmyk("10,,,20")
    assert result == "10,0,0,20"

def test_normalize_cmyk_percentage_signs(canvas):
    result = canvas._normalize_cmyk("10%,20%,30%,40%")
    assert result

def test_normalize_cmyk_boolean_values(canvas):
    result = canvas._normalize_cmyk(True)
    assert result

def test_normalize_cmyk_list_input(canvas):
    result = canvas._normalize_cmyk([10, 20, 30, 40])
    assert result

def test_normalize_cmyk_dict_input(canvas):
    result = canvas._normalize_cmyk({"c": 10, "m": 20, "y": 30, "k": 40})
    assert result

def test_normalize_cmyk_tuple_input(canvas):
    result = canvas._normalize_cmyk((10, 20, 30, 40))
    assert result

def test_normalize_cmyk_mixed_separators(canvas):
    result = canvas._normalize_cmyk("10;20,30:40")
    assert result

def test_normalize_cmyk_quotes_in_string(canvas):
    result = canvas._normalize_cmyk('"10","20","30","40"')
    assert result

def test_normalize_cmyk_parentheses(canvas):
    result = canvas._normalize_cmyk("(10,20,30,40)")
    assert result

def test_normalize_cmyk_brackets(canvas):
    result = canvas._normalize_cmyk("[10,20,30,40]")
    assert result

def test_normalize_cmyk_braces(canvas):
    result = canvas._normalize_cmyk("{10,20,30,40}")
    assert result

def test_normalize_cmyk_newline_separated(canvas):
    result = canvas._normalize_cmyk("10\n20\n30\n40")
    assert result

def test_normalize_cmyk_mixed_whitespace(canvas):
    result = canvas._normalize_cmyk("10 , \t20\n,30  ,\r\n40")
    assert result
