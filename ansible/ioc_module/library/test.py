import argparse

def parse_arguments():
    # Create the argument parser
    parser = argparse.ArgumentParser(description="A script with five command-line arguments.")
    
    # Add arguments
    parser.add_argument('input_file', type=str, help='The input file to process.')
    parser.add_argument('output_file', type=str, help='The output file where results will be saved.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('-n', '--number', type=int, default=42, help='An integer number (default: 42).')
    parser.add_argument('--timeout', type=float, help='Timeout value in seconds.')

    return parser.parse_args()

def main():
    args = parse_arguments()

    # Print all arguments in a single formatted string
    print(f"Input File: {args.input_file}\n"
          f"Output File: {args.output_file}\n"
          f"Verbose: {args.verbose}\n"
          f"Number: {args.number}\n"
          f"Timeout: {args.timeout}")

if __name__ == "__main__":
    main()
