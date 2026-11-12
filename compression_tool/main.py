import os
import heapq
from pathlib import Path
from typing import BinaryIO, Optional, Union, cast

class HuffmanNode:
    """A node in a Huffman coding tree.

    Leaf nodes store an original byte value in ''char''. Internal nodes use an empty string and store the combined frequency of their child nodes.
    """

    def __init__(self, char: Union[int, str] = '', freq: int = 0) -> None:
        """Initialize a Huffman tree node.
        
        Args:
            char: Byte value for a leaf node, or an empty string for an internal node.
            freq: Frequency count represented by this node.
        
        Returns: 
            None.

        Raises:
            No exceptions are raised directly by this method.
        """
        self.char = char # this will hold ann int (0-255) in binary mode 
        self.freq = freq
        self.left: Optional["HuffmanNode"] = None
        self.right: Optional["HuffmanNode"] = None

    def __lt__(self, other: "HuffmanNode") -> bool:
        """Compare two nodes for heap ordering.

        Args: 
            other: The node to compare against this node.
        Returns:
            AttributeRrror: If ''other'' does not provide ''freq'' and ''char'' atributes.
        """

        # Tie breaker: If frequencies match, compare byte values to keep heap stable
        if self.freq == other.freq:
            return str(self.char) < str(other.char)
        return self.freq < other.freq

class HuffmanEncoderDecoder:
    """Encode and decode files using Huffman coding.
    The class expects input files to live in a ''data'' directory next to this script. Encoded and decoded files are also written to that directory.
    """
    def __init__(self, filename: Union[str, Path]) -> None:
        """Initialize the encoder/decoder with a target file.
            Args:
                filename: Name or path of the input file. Only the final file name component is used. which keeps all reads and writes inside the local ''data'' directory.
            Returns:
                 None.
            Raises:
                 No exceptions are raised directly by this method.
        """
        base_dir = Path(__file__).resolve().parent
        clean_filename = Path(filename).name

        #Absolute structural paths
        self.path: Path = base_dir / "data" / clean_filename

        name = Path(clean_filename).stem
        extension = Path(clean_filename).suffix

        self.encoded_file: Path = base_dir / "data" / f"{name}_encoded{extension}"
        self.decoded_file: Path = base_dir / "data" / f"{name}_decoded{extension}"

        self.heap: list[HuffmanNode] = []
        self.frequency_mapping: dict[int, int] = {}
        self.prefix_table: dict[int, str] = {}
        self.inverse_prefix_table: dict[str, int] = {}
        self.expected_total_chars: int = 0

    def build_char_frequency_map(self) -> None:
        """Build a frequency table for each byte value in the source file.

        Args: 
            None.
        Returns:
            None. The result is storage in ''self.frequency_mapping''.
        Raises:
            FileNotFoundError: If the source file does not exist.
            PermissionError: If the source file cannot be read.
            IsADirectoryError: If the source path points to a directory.
            OSError: If another operating-system file error occurs.
        """

        #read the input file byte by byte
        with open(self.path, 'rb') as file:
            byte = file.read(1)
            while byte:
                byte_val = byte[0] # get integer value (0-255)
                self.frequency_mapping[byte_val] = self.frequency_mapping.get(byte_val, 0) + 1
                byte = file.read(1)

    def build_binary_tree(self) -> None:
        """Build the Huffmn tree from the byte frequency mapping.

        Args:
            None.
        Returns: 
            None. The tree root is stored at ''self.heap[0]'' when at least one byte frequency is exist.
        Raises: 
            No exceptions are reised directly by this method when ''self.frequency_mapping'' contains integer frequencies.
        """

        #bug fixed: correctly maps char first. then freq to match class init
        self.heap = [HuffmanNode(char, freq) for char, freq in self.frequency_mapping.items()]
        heapq.heapify(self.heap)

        while len(self.heap) > 1:
            left = heapq.heappop(self.heap)
            right = heapq.heappop(self.heap)
            merged = HuffmanNode('', left.freq + right.freq)
            merged.left = left
            merged.right = right
            heapq.heappush(self.heap, merged)

    def generate_prefix_table(self) -> None:
        """Generate the byte-to-prefix lookup table from the Huffman tree.

        Args:
            None.
        Returns:
            None. Generated prefix codes are stored in ''self.prefix_table''.
        Raises:
            No exceptions are raised directly by this method.
        """

        if not self.heap:
            return  
        root = self.heap[0]

        def helperFunc(node: HuffmanNode, code: str) -> None:
            """Recursively traverse the Huffman tree and assign prefix codes.

            Args:
                node: Current Huffman tree node being visited.
                code: Prefix code accumulated from the root to ''node''.
            Returns:
                None. Leaf byte codes are added to ''self.prefix_table''.
            Raises:
                RecursionError: If the Huffman tree is unexpectedly deep enough.
            """
            if node.left is None and node.right is None:
                self.prefix_table[cast(int, node.char)] = code
                return
            if node.left:
                helperFunc(node.left, code + '0')
            if node.right:
                helperFunc(node.right, code + '1')

        # guard case for single-character files
        if root.left is None and root.right is None:
            self.prefix_table[cast(int, root.char)] = '0'
        else:
            helperFunc(root, '')

    def write_table_to_output(self) -> None:
        """Write the prefix-table metadata to the encoded output file.

        Args:
            None.
        Returns:
            None. Metadata is written to ''self.encoded_file''.
        Raises:
            PermissionError: If the encoded file cannot be written.
            IsADirectoryError: If the encoded file path points to a directory.
            OSError: If another operating-system file error occurs.
        """

        #calculate total characters by summing up all frequencies
        total_chars = sum(self.frequency_mapping.values())

        with open(self.encoded_file, 'wb') as file:
            file.write("PREFIX-TABLE-START\n".encode('utf-8'))
            #write total count on its own metadata line
            file.write(f"TOTAL-COUNT:{total_chars}\n".encode('utf-8'))

            for byte_val, code in self.prefix_table.items():
                file.write(f"{byte_val}:{code}\n".encode('utf-8'))
            file.write("PREFIX-TABLE-END\n".encode('utf-8'))

    def encode(self) -> None:
        """Encode the source file and write the compressed output file.

        Args:
            None.
        Returns:
            None. Encoded output is written to ''self.encoded_file''.
        Raises:
            KeyError: If a byte value in the source file does not have a corresponding prefix code in ''self.prefix_table''.
            FileNotFoundError: If the source file does not exist.
            PermissionError: If the source file cannot be read or the encoded file cannot be written.
            IsADirectoryError: If either file path points to a directory.
            OSError: If another operating-system file error occurs.
        """

        # 1. write metadata table
        self.write_table_to_output()

        # 2. Append packed compressed binary bits to our file
        with open(self.encoded_file, 'ab') as f_out:
            with open(self.path, 'rb') as f_in:
                bit_buffer = 0
                bit_count = 0
                while True:
                    chunk = f_in.read(8192)
                    if not chunk:
                        break
                    for byte_val in chunk:
                        code = self.prefix_table[byte_val]
                        for bit in code:
                            bit_buffer = (bit_buffer << 1) | int(bit)
                            bit_count += 1
                            if bit_count == 8:
                                f_out.write(bytes([bit_buffer]))
                                bit_buffer = 0
                                bit_count = 0

                if bit_count:
                    # Pad the final byte with zero bits on the right.
                    f_out.write(bytes([bit_buffer << (8 - bit_count)]))

    def read_table_from_input(self, f: BinaryIO) -> None:
        """Read the prefix-table metadata from the encoded input file.

        Args:
            f: Binary file object positioned at the start of the encoded file.
        Returns:
            None. Metadata is read into ''self.inverse_prefix_table'' and ''self.expected_total_chars''.
        Raises:
            ValueError: If the metadata format is invalid or missing.
            FileNotFoundError: If the encoded file does not exist.
            PermissionError: If the encoded file cannot be read.
            IsADirectoryError: If the encoded file path points to a directory.
            OSError: If another operating-system file error occurs.
        """

        self.inverse_prefix_table = {}
        self.expected_total_chars = 0 # track this globally in the class

        line = f.readline().decode('utf-8', errors='replace').strip()
        if line != "PREFIX-TABLE-START":
            raise ValueError("Invalid encoded file format: Missing PREFIX-TABLE-START")

        found_end = False
        while True:
            line = f.readline().decode('utf-8', errors='replace').strip()
            if line == "PREFIX-TABLE-END":
                found_end = True
                break
            if not line:
                raise ValueError("Invalid encoded file format: Missing PREFIX-TABLE-END")

            if line.startswith("TOTAL-COUNT:"):
                try:
                    self.expected_total_chars = int(line.split(":", 1)[1])
                except ValueError as exc:
                    raise ValueError("Invalid encoded file format: Invalid total count") from exc
                if self.expected_total_chars < 0:
                    raise ValueError("Invalid encoded file format: Negative total count")
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid encoded file format: Invalid prefix-table entry")
            try:
                byte_val = int(parts[0])
            except ValueError as exc:
                raise ValueError("Invalid encoded file format: Invalid byte value") from exc
            code = parts[1]
            if not 0 <= byte_val <= 255 or not code or any(bit not in "01" for bit in code):
                raise ValueError("Invalid encoded file format: Invalid prefix-table entry")
            self.inverse_prefix_table[code] = byte_val

        if not found_end:
            raise ValueError("Invalid encoded file format: Missing PREFIX-TABLE-END")

    def decode(self) -> None:
        """Decode the encoded input file and write the decompressed output file.

        Args:
            None.
        Returns:
            None. Decoded output is written to ''self.decoded_file''.
        Raises:
            ValueError: If the encoded file format is invalid or missing.
            KeyError: If a prefix code in the encoded file does not have a corresponding byte value in ''self.inverse_prefix_table''.
            FileNotFoundError: If the encoded file does not exist.
            PermissionError: If the encoded file cannot be read or the decoded file cannot be written.
            IsADirectoryError: If either file path points to a directory.
            OSError: If another operating-system file error occurs.
        """
        print(f"Reading prefix table from {self.encoded_file}...")
        decoded_bytes = bytearray()

        with open(self.encoded_file, 'rb') as f_in:
            # Re- read the header and fetch expected_total_chars
            self.read_table_from_input(f_in)

            # Diagnostic check to make sure the header was actually parsed:
            print(f"Targeting exactly {self.expected_total_chars} characters for the restoration...")

            current_bits = ""
            chars_recovered = 0

            chunk = f_in.read(1024)  # read in chunks for efficiency
            while chunk:
                for byte_val in chunk:
                    # Unpack integer byte into an 8-bit sequence
                    for shift in range(7, -1, -1):
                        bit = (byte_val >> shift) & 1
                        current_bits += str(bit)

                        # Check if the table immediately as bits drop in
                        if current_bits in self.inverse_prefix_table:
                            original_byte = self.inverse_prefix_table[current_bits]
                            decoded_bytes.append(original_byte)
                            chars_recovered += 1
                            current_bits = ""  # reset for the next code

                            # Stop if we've recovered the expected number of characters
                            if chars_recovered >= self.expected_total_chars:
                                print(f"Successfully recovered {chars_recovered} characters. Stopping early.")
                                #breakout of everything by converting to text and saving
                                self._save_decoded_text(decoded_bytes)
                                return
                chunk = f_in.read(1024)

        self._save_decoded_text(decoded_bytes)

    def _save_decoded_text(self, decoded_bytes: Union[bytes, bytearray]) -> None:
        """Save the decoded bytes to the output file.

        Args:
            decoded_bytes: The bytearray containing the decoded data.
        Returns:
            None. The data is written to ''self.decoded_file''.
        Raises:
            PermissionError: If the decoded file cannot be written.
            IsADirectoryError: If the decoded file path points to a directory.
            OSError: If another operating-system file error occurs.
        """
        print(f"Writing decoded output to {self.decoded_file}...")

        # Open in 'wb' mode instead of text mode
        with open(self.decoded_file, 'wb') as f_out:
            f_out.write(decoded_bytes)

def main() -> None:
    """Run the command-line Huffman compression and decompression Workflow.
    Args:
        None.
    Returns:
        None. The function orchestrates the encoding and decoding process.
    Raises:
        No exception are intentionally propagated. Common file and operating system exceptions are caught and reported to the user
    """
    print("Hello from compression-tool!")
    try:
        input_filename = input("please give the name of the file to be encoded: ")
        huffman_obj = HuffmanEncoderDecoder(input_filename)

        print(f"Building frequency map for {huffman_obj.path}...")
        huffman_obj.build_char_frequency_map()
        print("Character frequency map built successfully.\n")

        print("Building Huffman tree...")
        huffman_obj.build_binary_tree()
        print("Huffman tree built successfully.\n")

        print("Generating prefix table...")
        huffman_obj.generate_prefix_table()
        print("Prefix table generated successfully.\n")

        print("Encoding input file...")
        huffman_obj.encode()
        print(f"Encoding completed! Encoded file can be found at {huffman_obj.encoded_file}\n")
        
        print("Decoding the encoded file...")
        huffman_obj.decode()
        print(f"Decoded file can be found at {huffman_obj.decoded_file}\n")

        print("Comparing file sizes...")
        original_size = os.path.getsize(huffman_obj.path)
        encoded_size = os.path.getsize(huffman_obj.encoded_file)
        decoded_size = os.path.getsize(huffman_obj.decoded_file)

        print(f"Original file size: {original_size} bytes")
        print(f"Encoded file size: {encoded_size} bytes")
        print(f"Decoded file size: {decoded_size} bytes")

        # Calculate reduction percentage
        if original_size > 0:
            reduction_percentage = ((original_size - encoded_size) / original_size) * 100
            print(f"Size reduction: {reduction_percentage:.2f}%")
        else:
            print("Original file size is zero, cannot calculate reduction percentage.")

    except FileNotFoundError:
        print("Error: The specified file was not found.")
    except PermissionError:
        print("Error: Permission denied when accessing the file.")
    except IsADirectoryError:
        print("Error: The specified path is a directory, not a file.")
    except OSError as e:
        print(f"Error: An OS error occurred: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
