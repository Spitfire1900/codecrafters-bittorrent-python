import json
import sys
import re

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

# import bencodepy - available if you need it!
# import requests - available if you need it!


# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"
def decode_bencode(bencoded_value: bytes):
    """
    Iteratively decode bencode data using a stack-based approach.
    Handles arbitrary nesting depth without recursion.
    """
    
    def parse_element(data: bytes, index: int):
        """Parse a single element starting at index. Returns (element, next_index)"""
        if index >= len(data):
            raise ValueError("Unexpected end of data")
        
        # Strings
        if chr(data[index]).isdigit():
            colon_index = data.find(b":", index)
            if colon_index == -1:
                raise ValueError("Invalid encoded string")
            length = int(data[index:colon_index])
            start = colon_index + 1
            end = start + length
            if end > len(data):
                raise ValueError("String length exceeds data")
            return data[start:end], end
        
        # Integers
        elif data[index] == ord("i"):
            end_index = data.find(b"e", index)
            if end_index == -1:
                raise ValueError("Invalid encoded integer - no closing 'e'")
            _bytes = data[index + 1:end_index]
            LOGGER.debug(f"Decoded integer bytes: {_bytes}")
            decoded = _bytes.decode()
            if not decoded or not (decoded.isdigit() or (decoded[0] == "-" and decoded[1:].isdigit())):
                raise ValueError(f"Invalid encoded integer, got {_bytes!r}")
            return int(decoded), end_index + 1
        
        else:
            raise ValueError(f"Unexpected character at index {index}: {chr(data[index])}")
    
    # Handle top-level non-list types
    if len(bencoded_value) == 0:
        raise ValueError("Empty encoded value")
    
    if bencoded_value[0] != ord("l"):
        # Top-level string or integer
        result, _ = parse_element(bencoded_value, 0)
        return result
    
    # List parsing using stack for iterative approach
    stack = []  # Stack of (list_container, depth_marker)
    current_list = []
    index = 1  # Skip initial 'l'
    
    while index < len(bencoded_value):
        char = bencoded_value[index]
        
        if char == ord("e"):
            # End of list
            if not stack:
                # This is the end of the top-level list
                return current_list
            # Pop from stack and add current list to parent
            parent_list, _ = stack.pop()
            parent_list.append(current_list)
            current_list = parent_list
            index += 1
        
        elif char == ord("l"):
            # Start of nested list
            stack.append((current_list, "list"))
            current_list = []
            index += 1
        
        else:
            # Parse element (string or integer)
            element, index = parse_element(bencoded_value, index)
            current_list.append(element)
    
    raise ValueError("Unclosed list - missing closing 'e'")


def main():
    command = sys.argv[1]

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.
        def bytes_to_str(data):
            LOGGER.debug("Type: %s, Value: %s", type(data), data)
            if isinstance(data, bytes):
                return data.decode()
            raise TypeError(f"Type not serializable: {type(data)}")

        print(
            json.dumps(decode_bencode(bencoded_value), default=bytes_to_str)
        )  # default is only used when not serializable, e.g. bytes
    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
