"""
Comprehensive pytest test suite for the bencode decoder.

Tests the decode_bencode function directly with various inputs.
"""

import pytest
from app.main import decode_bencode


class TestBasicStrings:
    """Test basic string encoding/decoding."""
    
    def test_simple_string(self):
        result = decode_bencode(b"5:hello")
        assert result == b"hello"
    
    def test_string_with_numbers(self):
        result = decode_bencode(b"10:hello12345")
        assert result == b"hello12345"
    
    def test_empty_string(self):
        result = decode_bencode(b"0:")
        assert result == b""
    
    def test_single_character(self):
        result = decode_bencode(b"1:a")
        assert result == b"a"
    
    def test_string_with_spaces(self):
        result = decode_bencode(b"11:hello world")
        assert result == b"hello world"


class TestBasicIntegers:
    """Test basic integer encoding/decoding."""
    
    def test_positive_integer(self):
        result = decode_bencode(b"i42e")
        assert result == 42
    
    def test_zero(self):
        result = decode_bencode(b"i0e")
        assert result == 0
    
    def test_negative_integer(self):
        result = decode_bencode(b"i-5e")
        assert result == -5
    
    def test_large_integer(self):
        result = decode_bencode(b"i123456789e")
        assert result == 123456789
    
    def test_negative_large_integer(self):
        result = decode_bencode(b"i-987654321e")
        assert result == -987654321


class TestEmptyAndSimpleLists:
    """Test empty and simple list encoding/decoding."""
    
    def test_empty_list(self):
        result = decode_bencode(b"le")
        assert result == []
    
    def test_list_with_one_string(self):
        result = decode_bencode(b"l5:helloe")
        assert result == [b"hello"]
    
    def test_list_with_one_integer(self):
        result = decode_bencode(b"li42ee")
        assert result == [42]
    
    def test_list_with_string_and_integer(self):
        result = decode_bencode(b"l5:helloi42ee")
        assert result == [b"hello", 42]
    
    def test_list_with_multiple_strings(self):
        result = decode_bencode(b"l5:hello5:worlde")
        assert result == [b"hello", b"world"]
    
    def test_list_with_multiple_integers(self):
        result = decode_bencode(b"li1ei2ei3ee")
        assert result == [1, 2, 3]


class TestNestedLists:
    """Test nested list encoding/decoding."""
    
    def test_one_level_nested_empty(self):
        result = decode_bencode(b"llee")
        assert result == [[]]
    
    def test_one_level_nested_with_element(self):
        result = decode_bencode(b"ll5:helloee")
        assert result == [[b"hello"]]
    
    def test_nested_lists_with_multiple_items(self):
        result = decode_bencode(b"lli1ei2eee")
        assert result == [[1, 2]]
    
    def test_original_failing_case(self):
        """Test the case that originally failed during development."""
        result = decode_bencode(b"l5:helloi42el4:testee")
        assert result == [b"hello", 42, [b"test"]]
    
    def test_string_containing_e(self):
        """Test list containing string with 'e' character."""
        result = decode_bencode(b"l4:testee")
        assert result == [b"test"]
    
    def test_multiple_nested_lists(self):
        result = decode_bencode(b"ll1:aeee")
        assert result == [[b"a"]]
    
    def test_deeply_nested_lists(self):
        result = decode_bencode(b"llllleeeee")
        assert result == [[[[[]]]]]
    
    def test_mixed_nested_structure(self):
        result = decode_bencode(b"li1el2:hiei99ee")
        assert result == [1, [b"hi"], 99]


class TestComplexStructures:
    """Test complex nested structures."""
    
    def test_complex_nested_with_multiple_elements(self):
        result = decode_bencode(b"li1el5:helloei99ee")
        assert result == [1, [b"hello"], 99]
    
    def test_list_starting_with_string_containing_digit(self):
        result = decode_bencode(b"l10:0123456789i99ee")
        assert result == [b"0123456789", 99]
    
    def test_list_with_single_element(self):
        result = decode_bencode(b"l5:helloe")
        assert result == [b"hello"]
    
    def test_nested_list_then_integer(self):
        result = decode_bencode(b"lli1eei42ee")
        assert result == [[1], 42]


class TestDictionaries:
    """Test dictionary encoding/decoding."""
    
    def test_empty_dict(self):
        result = decode_bencode(b"de")
        assert result == {}
    
    def test_simple_key_value(self):
        result = decode_bencode(b"d3:key5:valuee")
        assert result == {b"key": b"value"}
    
    def test_dict_with_integer(self):
        result = decode_bencode(b"d1:ai42ee")
        assert result == {b"a": 42}
    
    def test_dict_with_string(self):
        result = decode_bencode(b"d1:a5:helloe")
        assert result == {b"a": b"hello"}
    
    def test_dict_with_list(self):
        result = decode_bencode(b"d1:al5:helloee")
        assert result == {b"a": [b"hello"]}
    
    def test_dict_with_multiple_keys(self):
        result = decode_bencode(b"d1:ai1e1:bi2ee")
        assert result == {b"a": 1, b"b": 2}
    
    def test_nested_dict(self):
        result = decode_bencode(b"d2:d1d3:key5:valueeee")
        assert result == {b"d1": {b"key": b"value"}}
    
    def test_dict_with_multi_element_list(self):
        result = decode_bencode(b"d1:ali1ei2eee")
        assert result == {b"a": [1, 2]}
    
    def test_dict_with_list_of_dicts(self):
        """Test dictionary containing a list with a dictionary."""
        result = decode_bencode(b"d1:al1:aee")
        assert result == {b"a": [b"a"]}
    
    def test_dict_with_nested_dict(self):
        """Test dictionary containing another dictionary."""
        result = decode_bencode(b"d1:ad1:b1:cee")
        assert result == {b"a": {b"b": b"c"}}


class TestErrorCases:
    """Test error handling for invalid bencode."""
    
    def test_missing_colon_in_string(self):
        with pytest.raises(ValueError):
            decode_bencode(b"5hello")
    
    def test_missing_closing_e_for_integer(self):
        with pytest.raises(ValueError):
            decode_bencode(b"i42")
    
    def test_unclosed_list(self):
        with pytest.raises(ValueError):
            decode_bencode(b"l5:hello")
    
    def test_invalid_character(self):
        with pytest.raises(ValueError):
            decode_bencode(b"x5:hello")
    
    def test_empty_input(self):
        with pytest.raises(ValueError):
            decode_bencode(b"")
    
    def test_malformed_integer(self):
        with pytest.raises(ValueError):
            decode_bencode(b"iabce")
    
    def test_string_too_long(self):
        with pytest.raises(ValueError):
            decode_bencode(b"100:hello")
    
    def test_negative_string_length(self):
        with pytest.raises(ValueError):
            decode_bencode(b"-5:hello")


class TestDeepNesting:
    """Test deep nesting without stack overflow."""
    
    def test_100_levels_of_nesting(self):
        """Test 100 levels of list nesting."""
        encoded = b"l" * 100 + b"e" * 100
        result = decode_bencode(encoded)
        
        # Verify structure by checking type and depth
        current = result
        depth = 0
        while isinstance(current, list):
            depth += 1
            if len(current) == 0:
                break
            current = current[0]
        
        assert depth == 100
    
    def test_1000_levels_of_nesting(self):
        """Test 1000 levels of list nesting."""
        encoded = b"l" * 1000 + b"e" * 1000
        result = decode_bencode(encoded)
        
        # Verify structure by checking depth
        current = result
        depth = 0
        while isinstance(current, list):
            depth += 1
            if len(current) == 0:
                break
            current = current[0]
        
        assert depth == 1000


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_string_with_4_chars(self):
        result = decode_bencode(b"4:test")
        assert result == b"test"
    
    def test_string_with_5_chars(self):
        result = decode_bencode(b"5:hello")
        assert result == b"hello"
    
    def test_string_all_es(self):
        result = decode_bencode(b"3:eee")
        assert result == b"eee"
    
    def test_string_with_numbers(self):
        result = decode_bencode(b"5:12345")
        assert result == b"12345"
    
    def test_zero_length_string_in_list(self):
        result = decode_bencode(b"l0:e")
        assert result == [b""]
    
    def test_multiple_zero_length_strings(self):
        result = decode_bencode(b"l0:0:0:e")
        assert result == [b"", b"", b""]
    
    def test_mixed_types_in_list(self):
        result = decode_bencode(b"li42e5:helloee")
        assert result == [42, b"hello"]
    
    def test_dict_with_empty_string_key(self):
        result = decode_bencode(b"d0:1:ae")
        assert result == {b"": b"a"}
    
    def test_dict_with_empty_string_value(self):
        result = decode_bencode(b"d1:a0:e")
        assert result == {b"a": b""}


class TestTopLevelTypes:
    """Test decoding top-level types directly."""
    
    def test_top_level_string(self):
        result = decode_bencode(b"11:hello world")
        assert result == b"hello world"
    
    def test_top_level_integer(self):
        result = decode_bencode(b"i999e")
        assert result == 999
    
    def test_top_level_list(self):
        result = decode_bencode(b"li1ei2ee")
        assert result == [1, 2]
    
    def test_top_level_dict(self):
        result = decode_bencode(b"d1:ai1ee")
        assert result == {b"a": 1}


class TestRealWorldScenarios:
    """Test scenarios based on real bencode usage (BitTorrent files)."""
    
    def test_torrent_like_structure(self):
        """Simulate a simplified torrent file structure."""
        # d
        #   4:name 12:Example File
        #   6:length i1024e
        # e
        encoded = b"d4:name12:Example File6:lengthi1024ee"
        result = decode_bencode(encoded)
        
        assert isinstance(result, dict)
        assert b"name" in result
        assert result[b"name"] == b"Example File"
    
    def test_nested_announce_list(self):
        """Simulate announce list with multiple trackers."""
        # d
        #   13:announce-list
        #   ll8:tracker1el8:tracker2ee
        # e
        encoded = b"d13:announce-listll8:tracker1el8:tracker2eee"
        result = decode_bencode(encoded)
        
        assert isinstance(result, dict)
        assert b"announce-list" in result
        announce_list = result[b"announce-list"]
        assert isinstance(announce_list, list)
        assert len(announce_list) == 2
    
    def test_file_list_with_metadata(self):
        """Simulate file list with metadata."""
        # Simple list containing two dictionaries
        # l d 4:name 3:foo i10e e d 4:name 3:bar i20e e e
        encoded = b"ld4:name3:fooi10eeld4:name3:bari20eeee"
        result = decode_bencode(encoded)
        
        assert isinstance(result, list)
        assert len(result) == 2


class TestTypeConsistency:
    """Test that return types are consistent."""
    
    def test_list_elements_preserve_type(self):
        """Verify list elements maintain their types."""
        result = decode_bencode(b"l5:helloi42e3:keye")
        assert isinstance(result, list)
        assert isinstance(result[0], bytes)
        assert isinstance(result[1], int)
        assert isinstance(result[2], bytes)
    
    def test_dict_keys_are_bytes(self):
        """Verify dictionary keys are bytes."""
        result = decode_bencode(b"d3:key5:valuee")
        assert isinstance(result, dict)
        keys = list(result.keys())
        assert len(keys) > 0
        assert isinstance(keys[0], bytes)
    
    def test_dict_values_preserve_type(self):
        """Verify dictionary values maintain their types."""
        result = decode_bencode(b"d1:si42e1:t5:testee")
        assert isinstance(result, dict)
        assert isinstance(result[b"s"], int)
        assert isinstance(result[b"t"], bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
