import json
import logging
import os
import sys
from typing import Any, Optional

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
LOGGER = logging.getLogger(__name__)
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOGGER.setLevel(getattr(logging, log_level, logging.DEBUG))


class BencodeParser:
    """
    Iterative bencode parser supporting strings, integers, lists, and dictionaries.

    Uses a stack-based approach to handle arbitrary nesting depth without recursion.

    Args:
        data: Bencode-encoded bytes to parse
        max_depth: Optional maximum nesting depth (None = no limit)
        max_size: Optional maximum bytes allowed to decode (None = no limit)
    """

    def __init__(
        self,
        data: bytes,
        max_depth: Optional[int] = None,
        max_size: Optional[int] = None,
    ) -> None:
        """Initialize parser with bencode data."""
        self.data = data
        self.index = 0
        self.max_depth = max_depth
        self.max_size = max_size
        self.current_depth = 0

    def parse(self) -> bytes | int | list[Any] | dict:
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

    def _parse_element(self) -> bytes | int:
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

        len_bytes = self.data[self.index : colon_index]

        try:
            length = int(len_bytes)
        except ValueError:
            raise ValueError(f"Invalid string length: {len_bytes}")

        # RFC 1337: Disallow leading zeros (except for single '0')
        if len(len_bytes) > 1 and len_bytes.startswith(b"0"):
            raise ValueError("String lengths must not have leading zeros")

        if length < 0:
            raise ValueError("String length cannot be negative")

        # Check max_size limit
        if self.max_size is not None and length > self.max_size:
            raise ValueError(
                f"String length {length} exceeds maximum allowed {self.max_size}"
            )

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

        int_bytes = self.data[self.index + 1 : end_index]
        LOGGER.debug(f"Decoded integer bytes: {int_bytes}")

        try:
            int_str = int_bytes.decode()
        except UnicodeDecodeError:
            raise ValueError(f"Invalid integer encoding: {int_bytes!r}")

        # Validate integer format according to RFC 1337
        if not int_str or not (
            int_str.isdigit() or (int_str[0] == "-" and int_str[1:].isdigit())
        ):
            raise ValueError(f"Invalid integer value: {int_bytes!r}")

        # RFC 1337: Reject numbers with leading zeros (except for "-0" edge case)
        num_part = int_str.lstrip("-")
        if len(num_part) > 1 and num_part.startswith("0"):
            raise ValueError("Integers must not have leading zeros")

        # Prevent leading minus sign with zero (i.e., "i-0e")
        if int_str == "-0":
            raise ValueError("Negative zero is not allowed")

        self.index = end_index + 1
        return int(int_str)

    def _parse_container(self) -> list[Any] | dict:
        """
        Parse a container (list or dict) using stack-based iteration.
        Handles arbitrary nesting depth without recursion.
        """
        # Stack items: (container, container_type, pending_key)
        stack: list[tuple[list[Any] | dict[Any, Any], str, Any]] = []

        # Check initial depth
        if self.max_depth is not None and self.current_depth >= self.max_depth:
            raise ValueError(f"Maximum nesting depth {self.max_depth} exceeded")

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
        self.current_depth += 1
        self.index += 1  # Skip 'l' or 'd'

        while self.index < len(self.data):
            char = self.data[self.index]

            # End of container
            if char == ord("e"):
                self.current_depth -= 1
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
                if (
                    self.max_depth is not None
                    and self.current_depth + 1 > self.max_depth
                ):
                    raise ValueError(f"Maximum nesting depth {self.max_depth} exceeded")
                stack.append((current, container_type, pending_key))
                current = []
                container_type = "list"
                expecting_key = False
                self.current_depth += 1
                self.index += 1

            # Start of nested dict
            elif char == ord("d"):
                if (
                    self.max_depth is not None
                    and self.current_depth + 1 > self.max_depth
                ):
                    raise ValueError(f"Maximum nesting depth {self.max_depth} exceeded")
                stack.append((current, container_type, pending_key))
                current = {}
                container_type = "dict"
                expecting_key = True
                self.current_depth += 1
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


def decode_bencode(
    bencoded_value: bytes,
    max_depth: Optional[int] = None,
    max_size: Optional[int] = None,
) -> bytes | int | list[Any] | dict:
    """
    Decode bencode data.

    Supports:
    - Strings: 5:hello
    - Integers: i42e
    - Lists: l...e
    - Dictionaries: d...e (keys must be in sorted order)

    Args:
        bencoded_value: Bencode-encoded bytes to decode
        max_depth: Optional maximum nesting depth (None = no limit)
        max_size: Optional maximum bytes allowed in a single string (None = no limit)

    Returns:
        Decoded value (bytes, int, list, or dict)

    Raises:
        ValueError: If the bencode data is malformed
    """
    parser = BencodeParser(bencoded_value, max_depth=max_depth, max_size=max_size)
    return parser.parse()


def bytes_to_hex_string(data: bytes) -> str:
    """Convert bytes to hex string format like '<hex>AA BB CC...</hex>'.
    
    Args:
        data: Bytes to convert
        
    Returns:
        Hex string representation
    """
    hex_str = " ".join(f"{byte:02X}" for byte in data)
    return f"<hex>{hex_str}</hex>"


def convert_bytes_to_str(obj: Any, use_latin1: bool = False, is_pieces_field: bool = False) -> Any:
    """Recursively convert bytes to strings in dicts and lists.

    Args:
        obj: Object to convert
        use_latin1: If True, use latin-1 fallback for non-UTF-8 bytes
        is_pieces_field: If True, convert bytes to hex format for pieces field

    Returns:
        Converted object with bytes as strings where possible
    """
    if isinstance(obj, bytes):
        if is_pieces_field:
            return bytes_to_hex_string(obj)
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            if use_latin1:
                return obj.decode("latin-1")
            else:
                return obj  # Keep as bytes if decoding fails
    elif isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            # Special handling for 'pieces' field within 'info' dict
            if key == "pieces":
                result[key] = convert_bytes_to_str(v, use_latin1=use_latin1, is_pieces_field=True)
            else:
                result[key] = convert_bytes_to_str(v, use_latin1=use_latin1, is_pieces_field=False)
        return result
    elif isinstance(obj, list):
        return [convert_bytes_to_str(item, use_latin1=use_latin1, is_pieces_field=is_pieces_field) for item in obj]
    else:
        return obj


def bytes_to_str(data: Any) -> str:
    """JSON serializer for bytes objects."""
    LOGGER.debug("Type: %s, Value: %s", type(data), data)
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")
    raise TypeError(f"Type not serializable: {type(data)}")


def parse_torrent_file(torrent_file_path: str) -> dict:
    """
    Parse a torrent file and return its decoded content.
    
    Args:
        torrent_file_path: Path to the torrent file
        
    Returns:
        Dictionary containing the parsed torrent data
        
    Raises:
        FileNotFoundError: If the torrent file doesn't exist
        ValueError: If the torrent file is malformed
    """
    if not os.path.exists(torrent_file_path):
        raise FileNotFoundError(f"Torrent file not found: {torrent_file_path}")
    
    try:
        with open(torrent_file_path, 'rb') as f:
            torrent_data = f.read()
        
        # Parse the bencoded data
        decoded_data = decode_bencode(torrent_data)
        
        # Convert bytes to strings where possible
        parsed_data = convert_bytes_to_str(decoded_data)
        
        return parsed_data
        
    except Exception as e:
        raise ValueError(f"Error parsing torrent file: {e}")


def validate_torrent_structure(torrent_data: dict) -> bool:
    """
    Validate that the parsed torrent data has the required structure.
    
    Args:
        torrent_data: Parsed torrent data dictionary
        
    Returns:
        True if the torrent structure is valid, False otherwise
    """
    required_keys = ['info']
    
    # Check required top-level keys
    for key in required_keys:
        if key not in torrent_data:
            LOGGER.error(f"Missing required key: {key}")
            return False
    
    # Check info dictionary
    info = torrent_data.get('info', {})
    if not isinstance(info, dict):
        LOGGER.error("Info section must be a dictionary")
        return False
    
    # Check required info keys
    required_info_keys = ['piece length']
    for key in required_info_keys:
        if key not in info:
            LOGGER.error(f"Missing required info key: {key}")
            return False
    
    return True


def main() -> None:
    """Entry point for the bencode tool."""
    import argparse

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    parser = argparse.ArgumentParser(description="Minimal bencoding tool")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Command to execute"
    )

    # Decode subcommand
    decode_parser = subparsers.add_parser("decode", help="Decode bencode data")
    decode_parser.add_argument("bencoded", help="Bencoded payload")
    decode_parser.add_argument(
        "--latin1", action="store_true", help="Use latin-1 fallback for non-UTF-8 bytes"
    )
    decode_parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum nesting depth (DoS protection)",
    )
    decode_parser.add_argument(
        "--max-size",
        type=int,
        default=None,
        help="Maximum string size in bytes (DoS protection)",
    )
    
    # Parse torrent subcommand
    torrent_parser = subparsers.add_parser("parse-torrent", help="Parse torrent file")
    torrent_parser.add_argument("torrent_file", help="Path to torrent file")
    torrent_parser.add_argument(
        "--validate", action="store_true", help="Validate torrent structure"
    )
    torrent_parser.add_argument(
        "--pretty", action="store_true", help="Pretty print JSON output"
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        raise

    if args.command == "decode":
        try:
            # Accept both UTF-8 strings and hex-encoded values
            bencoded_value = args.bencoded.encode("utf-8")
        except Exception as e:
            print(f"Error encoding input: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            result = decode_bencode(
                bencoded_value, max_depth=args.max_depth, max_size=args.max_size
            )
            result = convert_bytes_to_str(result, use_latin1=args.latin1)
            print(json.dumps(result, default=bytes_to_str))
        except ValueError as e:
            print(f"Decode error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "parse-torrent":
        try:
            result = parse_torrent_file(args.torrent_file)
            
            if args.validate:
                is_valid = validate_torrent_structure(result)
                print(f"Torrent structure validation: {'PASS' if is_valid else 'FAIL'}")
                if not is_valid:
                    sys.exit(1)
            
            if args.pretty:
                print(json.dumps(result, default=bytes_to_str, indent=2))
            else:
                print(json.dumps(result, default=bytes_to_str))
                
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        raise NotImplementedError(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
