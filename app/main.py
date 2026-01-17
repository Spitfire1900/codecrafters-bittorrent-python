import json
import sys
from typing import Union, Tuple, List, Any

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class BencodeParser:
    """
    Iterative bencode parser supporting strings, integers, lists, and dictionaries.
    
    Uses a stack-based approach to handle arbitrary nesting depth without recursion.
    """
    
    def __init__(self, data: bytes) -> None:
        """Initialize parser with bencode data."""
        self.data = data
        self.index = 0
    
    def parse(self) -> Union[bytes, int, List[Any], dict]:
        """
        Parse bencode data and return the decoded value.
        
        Returns:
            Decoded value (bytes, int, list, or dict)
            
        Raises:
            ValueError: If the bencode data is malformed
        """
        if len(self.data) == 0:
            raise ValueError("Empty encoded value")
        
        # Handle top-level strings and integers
        if self.data[0] not in (ord("l"), ord("d")):
            return self._parse_element()
        
        # Parse lists and dictionaries with stack
        return self._parse_container()
    
    def _parse_element(self) -> Union[bytes, int]:
        """
        Parse a single element (string or integer) and return it.
        Updates self.index to point past the element.
        """
        if self.index >= len(self.data):
            raise ValueError("Unexpected end of data")
        
        current_byte = self.data[self.index]
        
        # Parse string (e.g., "5:hello")
        if chr(current_byte).isdigit():
            return self._parse_string()
        
        # Parse integer (e.g., "i42e")
        elif current_byte == ord("i"):
            return self._parse_integer()
        
        else:
            raise ValueError(
                f"Unexpected character at index {self.index}: {chr(current_byte)}"
            )
    
    def _parse_string(self) -> bytes:
        """Parse a bencode string (format: length:data)."""
        colon_index = self.data.find(b":", self.index)
        if colon_index == -1:
            raise ValueError("Invalid encoded string - missing colon")
        
        try:
            length = int(self.data[self.index:colon_index])
        except ValueError:
            raise ValueError(f"Invalid string length: {self.data[self.index:colon_index]}")
        
        start = colon_index + 1
        end = start + length
        
        if end > len(self.data):
            raise ValueError("String length exceeds available data")
        
        self.index = end
        return self.data[start:end]
    
    def _parse_integer(self) -> int:
        """Parse a bencode integer (format: i<number>e)."""
        end_index = self.data.find(b"e", self.index)
        if end_index == -1:
            raise ValueError("Invalid encoded integer - missing closing 'e'")
        
        int_bytes = self.data[self.index + 1:end_index]
        LOGGER.debug(f"Decoded integer bytes: {int_bytes}")
        
        try:
            int_str = int_bytes.decode()
        except UnicodeDecodeError:
            raise ValueError(f"Invalid integer encoding: {int_bytes!r}")
        
        # Validate integer format
        if not int_str or not (
            int_str.isdigit() or (int_str[0] == "-" and int_str[1:].isdigit())
        ):
            raise ValueError(f"Invalid integer value: {int_bytes!r}")
        
        self.index = end_index + 1
        return int(int_str)
    
    def _parse_container(self) -> Union[List[Any], dict]:
        """
        Parse a container (list or dict) using stack-based iteration.
        Handles arbitrary nesting depth without recursion.
        """
        # Stack items: (container, container_type, pending_key)
        stack: List[Tuple[Union[List[Any], dict[Any, Any]], str, Any]] = []
        
        # Initialize based on first character
        if self.data[self.index] == ord("d"):
            current = {}
            container_type = "dict"
            expecting_key = True
        else:
            current = []
            container_type = "list"
            expecting_key = False
        
        pending_key: Any = None
        self.index += 1  # Skip 'l' or 'd'
        
        while self.index < len(self.data):
            char = self.data[self.index]
            
            # End of container
            if char == ord("e"):
                if not stack:
                    # End of top-level container
                    return current
                
                # Pop from stack and attach current to parent
                parent, parent_type, parent_key = stack.pop()
                if parent_type == "dict":
                    assert isinstance(parent, dict)
                    parent[parent_key] = current
                    expecting_key = True
                else:
                    assert isinstance(parent, list)
                    parent.append(current)
                    expecting_key = False
                
                current = parent
                container_type = parent_type
                pending_key = parent_key if parent_type == "dict" else None
                self.index += 1
            
            # Start of nested list
            elif char == ord("l"):
                stack.append((current, container_type, pending_key))
                current = []
                container_type = "list"
                expecting_key = False
                self.index += 1
            
            # Start of nested dict
            elif char == ord("d"):
                stack.append((current, container_type, pending_key))
                current = {}
                container_type = "dict"
                expecting_key = True
                self.index += 1
            
            # Parse element (string or integer)
            else:
                element = self._parse_element()
                
                if container_type == "dict":
                    assert isinstance(current, dict)
                    if expecting_key:
                        pending_key = element
                        expecting_key = False
                    else:
                        current[pending_key] = element
                        expecting_key = True
                else:
                    assert isinstance(current, list)
                    current.append(element)
        
        raise ValueError("Unclosed container - missing closing 'e'")


def decode_bencode(bencoded_value: bytes) -> Union[bytes, int, List[Any], dict]:
    """
    Decode bencode data.
    
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
    parser = BencodeParser(bencoded_value)
    return parser.parse()


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
