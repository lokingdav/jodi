from rmd_utils import *


# TODO: Wire better error and usage messages
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("USAGE ")
        print("Usage: python main.py add_index_column <input_file.csv> <output_file.csv>")
        print("Usage: python main.py extract_columns <input_file.csv> <output_file.csv> <required columns>")
        print("Usage: python main.py remove_newlines_inside_rows <input_file.csv> <output_file.csv> <required columns>")
        print("Usage: python main.py group_rows <input_file.csv> <output_file.csv> <required column>")
        print("Usage: python main.py remove_duplicates_based_on_2_fields <input_file.csv> <output_file.csv> <required column 1> <required column 2>")

        print("Usage: python main.py print_duplicates <input_file.csv>")
        print("Usage: python main.py print_duplicated_rows_2_fields <input_file.csv> <required column 1> <required column 2>")
        exit(0)

    if sys.argv[1] == "add_index_column":
        if len(sys.argv) != 4:
            print("Usage: python main.py add_index_column <input_file.csv> <output_file.csv>")
            exit(0)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        add_index_column(input_file, output_file)
        exit(0)

    if sys.argv[1] == "extract_columns":
        if len(sys.argv) < 5:
            print("Usage: python main.py extract_columns <input_file.csv> <output_file.csv> <required columns>")
            exit(0)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        required_columns = sys.argv[4:]
        extract_columns(input_file, required_columns, output_file)
        exit(0)

    if sys.argv[1] == "print_duplicates":
        if len(sys.argv) != 2:
            print("Usage: python main.py print_duplicates <input_file.csv>")
            exit(0)
        input_file = sys.argv[2]
        print_duplicates(input_file)
        exit(0)

    if sys.argv[1] == "remove_newlines_inside_rows":
        if len(sys.argv) < 5:
            print("Usage: python main.py remove_newlines_inside_rows <input_file.csv> <output_file.csv> <required columns>")
            exit(0)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        required_columns = sys.argv[4:]
        remove_newlines_inside_rows(input_file, output_file, required_columns)
        exit(0)

    if sys.argv[1] == "group_rows":
        if len(sys.argv) != 5:
            print("Usage: python main.py group_rows <input_file.csv> <output_file.csv> <required column>")
            exit(0)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        required_column = sys.argv[4:]
        group_rows(input_file, output_file, required_column)
        exit(0)

    if sys.argv[1] == "print_duplicated_rows_2_fields":
        if len(sys.argv) != 5:
            print("Usage: python main.py print_duplicated_rows_2_fields <input_file.csv> <required column 1> <required column 2>")
            exit(0)
        input_file = sys.argv[2]
        required_columns = sys.argv[3:]
        print("here")
        print_duplicated_rows_2_fields(input_file, required_columns[0], required_columns[1])
        exit(0)
 
    if sys.argv[1] == "remove_duplicates_based_on_2_fields":
        if len(sys.argv) != 6:
            print("Usage: python main.py remove_duplicates_based_on_2_fields <input_file.csv> <output_file.csv> <required column 1> <required column 2>")
            exit(0)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        field1 = sys.argv[4]
        field2 = sys.argv[5]
        remove_duplicates_based_on_2_fields(input_file, field1, field2, output_file)
        exit(0)

    print("Check input: Wrong command")