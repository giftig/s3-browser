import shutil


def print_grid(data):
    """
    Print a list of strings in a grid according to the terminal size
    """
    largest = 0
    for e in data:
        largest = max(len(e), largest)

    # Add spacing
    largest += 1

    w = shutil.get_terminal_size().columns
    num_cols = int(w / largest)

    # Give up if we can't fit the data into columns anyway
    if num_cols <= 1:
        for e in data:
            print(e)

        return

    # Pad the strings to all be the same length, and divide into columns
    padded = [e.ljust(largest) for e in data]
    col_size = int(len(data) / num_cols)
    groups = [col_size] * num_cols

    # Account for remainder: first x columns need to be longer
    for i in range(len(data) % num_cols):
        groups[i] += 1

    output = [''] * groups[0]
    i = 0
    for g in groups:
        for j in range(g):
            output[j] += padded[i]
            i += 1

    for line in output:
        print(line)
