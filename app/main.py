import json
import sys
import re
from typing import Union, Tuple, List, Any, Callable

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
def decode_bencode(bencoded_value: bytes) -> Union[bytes, int, List[Any], dict]:
    """
    Iteratively decode bencode data using a stack-based approach.
    Handles arbitrary nesting depth without recursion.
    
    Supports:
    - Strings: 5:hello
    - Integers: i42e
    - Lists: l...e
    - Dictionaries: d...e (keys must be in sorted order)
    
    Args:
        bencoded_value: Bencode-encoded bytes to decode
        
    Returns:
        Decoded value (bytes, int, list, or dict)
        
    Raises:
        ValueError: If the bencode data is malformed
    """
    
    def parse_element(data: bytes, index: int) -> Tuple[Union[bytes, int], int]:
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
    
    # Handle top-level non-list/non-dict types
    if len(bencoded_value) == 0:
        raise ValueError("Empty encoded value")
    
    if bencoded_value[0] not in (ord("l"), ord("d")):
        # Top-level string or integer
        result, _ = parse_element(bencoded_value, 0)
        return result
    
    # Stack-based parsing for lists and dictionaries
    # Stack items: (container, type, pending_key_for_dict)
    # where container is List or dict, type is 'list' or 'dict'
    stack: List[Tuple[Union[List[Any], dict[Any, Any]], str, Any]] = []
    
    # Determine initial container type
    if bencoded_value[0] == ord("d"):
        current_container: Union[List[Any], dict[Any, Any]] = {}
        container_type = "dict"
        expecting_key = True
    else:
        current_container = []
        container_type = "list"
        expecting_key = False
    
    pending_key: Any = None  # For dictionaries, temporary storage for the key
    index: int = 1  # Skip initial 'l' or 'd'
    
    while index < len(bencoded_value):
        char = bencoded_value[index]
        
        if char == ord("e"):
            # End of current container
            if not stack:
                # End of top-level container
                return current_container
            # Pop from stack
            parent_container, parent_type, parent_pending_key = stack.pop()
            
            if parent_type == "dict":
                # We're closing a nested container (list or dict) that's a value in the parent dict
                assert isinstance(parent_container, dict)
                parent_container[parent_pending_key] = current_container
                expecting_key = True
            else:
                # We're closing a nested container (list or dict) that's an element in the parent list
                assert isinstance(parent_container, list)
                parent_container.append(current_container)
                expecting_key = False
            
            current_container = parent_container
            container_type = parent_type
            pending_key = parent_pending_key if parent_type == "dict" else None
            index += 1
        
        elif char == ord("l"):
            # Start of nested list
            stack.append((current_container, container_type, pending_key))
            current_container = []
            container_type = "list"
            expecting_key = False
            index += 1
        
        elif char == ord("d"):
            # Start of nested dictionary
            stack.append((current_container, container_type, pending_key))
            current_container = {}
            container_type = "dict"
            expecting_key = True
            index += 1
        
        else:
            # Parse element (string or integer)
            element, index = parse_element(bencoded_value, index)
            
            if container_type == "dict":
                assert isinstance(current_container, dict)
                if expecting_key:
                    # Store key temporarily
                    pending_key = element
                    expecting_key = False
                else:
                    # This is a value, pair it with the stored key
                    current_container[pending_key] = element
                    expecting_key = True
            else:
                assert isinstance(current_container, list)
                # List element
                current_container.append(element)
    
    raise ValueError("Unclosed container - missing closing 'e'")


def main() -> None:
    command: str = sys.argv[1]

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    if command == "decode":
        bencoded_value: bytes = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.
        def convert_bytes_to_str(obj: Any) -> Any:
            """Recursively convert bytes to strings in dicts and lists."""
            if isinstance(obj, bytes):
                return obj.decode()
            elif isinstance(obj, dict):
                return {(k.decode() if isinstance(k, bytes) else k): convert_bytes_to_str(v) 
                        for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_bytes_to_str(item) for item in obj]
            else:
                return obj

        def bytes_to_str(data: Any) -> str:
            LOGGER.debug("Type: %s, Value: %s", type(data), data)
            if isinstance(data, bytes):
                return data.decode()
            raise TypeError(f"Type not serializable: {type(data)}")

        result = decode_bencode(bencoded_value)
        result = convert_bytes_to_str(result)
        print(
            json.dumps(result, default=bytes_to_str)

        )  # default is only used when not serializable, e.g. bytes
    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
