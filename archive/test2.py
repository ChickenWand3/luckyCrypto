
class CustomFileReader:
    def __init__(self, file_path, mode='r', encoding='utf-8'):
        self.file_path = file_path
        self.mode = mode
        self.encoding = encoding
        self.file = None

    def __enter__(self):
        if 'b' in self.mode:
            self.file = open(self.file_path, self.mode)  # Binary mode: no encoding
        else:
            self.file = open(self.file_path, self.mode, encoding=self.encoding)  # Text mode
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

    def read(self):
        return self.file.read()

    def readline(self):
        return self.file.readline()

    def readlines(self):
        return self.file.readlines()
    
    def read_last_n_lines(self, n):
        # If n is more than number of lines total, it will return all lines
        if self.file:
            # Go to end of file
            self.file.seek(0, 2)

            # Get position
            pos = self.file.tell()
            # Initialize num lines, result lines
            num_lines = 0
            result_lines = []
            while pos > 0: # While not at beginning of file (prevent going backwards too far)
                # Move position of file pointer backwards and read 1 byte. Compare is newline
                pos -= 1
                self.file.seek(pos)
                if self.file.read(1) == b'\n':
                    num_lines += 1
                    if num_lines == n: # If we reached our goal of going back n lines, return the lines decoded. File must be opened in binary mode
                        for line in self.readlines():
                                result_lines.append(line.decode().strip())
                        return result_lines
        else:
            return None

with CustomFileReader("usdc_transfer.log", "rb") as f:
    lines = f.read_last_n_lines(10)
    print(lines)