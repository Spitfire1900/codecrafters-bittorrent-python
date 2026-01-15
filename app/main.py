import json
import sys

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

    match bencoded_value:
        case data if chr(data[0]).isdigit():
            first_colon_index = data.find(b":")
            if first_colon_index == -1:
                raise ValueError("Invalid encoded value")
            return data[first_colon_index + 1 :]
        case data if data[0] == ord("i"):
            if data[-1] != ord("e"):
                raise ValueError("Invalid encoded integer")
            _bytes = data[1:-1]
            LOGGER.debug(f"Decoded integer bytes: {_bytes}")
            decoded = _bytes.decode()
            if decoded.isdigit() or (decoded[0] == "-" and decoded[1:].isdigit()):
                return int(decoded)
            else:
                raise ValueError(f"Invalid encoded integer, got {_bytes!r}")
        case _:
            raise NotImplementedError(
                "Only strings and integers are supported at the moment, receieved {bencoded_value!r}"
            )


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
