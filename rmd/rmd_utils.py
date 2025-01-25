import sys

import csv
import pandas as pd

# Takes a CSV file and inserts an index column at the beginning and outputs a new CSV file
def add_index_column(input_file, output_file):
    try:
        # Open the input CSV file
        with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)

            # Read the header (if any) and the rest of the rows
            rows = list(reader)
            
            # Check if the file is empty
            if not rows:
                print("The input file is empty.")
                return

            header = rows[0]  # First row is assumed to be the header
            data = rows[1:]   # Remaining rows are the data

            # Add 'Index' to the header
            new_header = ['index'] + header

            # Add row numbers to each row of data
            new_data = [[i + 1] + row for i, row in enumerate(data)]

        # Write the updated data to the output file
        with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)

            # Write the header and data
            writer.writerow(new_header)
            writer.writerows(new_data)

        print(f"File processed successfully. Output saved to: {output_file}")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Takes a CSV file and column names as input an outputs a new CSV file containing only those columns specified
def extract_columns(input_file, required_columns, output_file):
    try:
        # Open the input CSV file
        with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)

            # Check if the required columns exist
            for column in required_columns:
                if column not in reader.fieldnames:
                    print(f"Error: Required column '{column}' is missing in the input file.")
                    return

            # Extract required columns
            extracted_data = []
            for row in reader:
                extracted_row = {col: row[col] for col in required_columns}
                extracted_data.append(extracted_row)

        # Write the extracted data to the output CSV file
        with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=required_columns)

            # Write the header and rows
            writer.writeheader()
            writer.writerows(extracted_data)

        print(f"Data extracted successfully. Output saved to: {output_file}")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Takes a CSV file as input and prints duplicates in each column
def print_duplicates(file_path):
    try:
        # Load the CSV file
        df = pd.read_csv(file_path, dtype=str)

        # Identify duplicates in each column
        for column in df.columns:
            duplicates = df[column][df[column].duplicated()]
            if not duplicates.empty:
                print(f"Duplicates in column '{column}':")
                print(duplicates)
                print()
            else:
                print(f"No duplicates found in column '{column}'.")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Takes a CSV file and column names as input and removes any new lines present in any of the column entries. Outputs a new CSV file.
def remove_newlines_inside_rows(file_path, output_path, columns_to_process):
    try:
        # Load the CSV file
        df = pd.read_csv(file_path, dtype=str)

        # Function to replace newlines within double quotes
        def replace_newlines_in_quotes(text):
            try:
                text = text.replace("\n", ' ')
            except:
                None
            return text

        # Process the specified columns
        for column in columns_to_process:
            if column in df.columns:
                df[column] = df[column].apply(replace_newlines_in_quotes)

        # Save the updated CSV
        df.to_csv(output_path, index=False)

        print(f"Processed CSV saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Takes a CSV file and column name as input and groups all rows based on unique entires in the column. Outputs a new CSV file.
def group_rows(input_csv, output_csv, field_name):
    # Load the CSV file
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: The file '{input_csv}' was not found.")
        return
    except Exception as e:
        print(f"Error reading the file: {e}")
        return
    
    # Check if the field exists
    if field_name not in df.columns:
        print(f"Error: The field '{field_name}' does not exist in the CSV file.")
        return
    
    # Identify rows with duplicate values in the specified field
    duplicates = df[df.duplicated(subset=field_name, keep=False)]
    non_duplicates = df[~df.duplicated(subset=field_name, keep=False)]
    
    # Combine duplicates and non-duplicates, with duplicates first
    grouped_df = pd.concat([duplicates.sort_values(by=field_name), non_duplicates]).reset_index(drop=True)
    
    # Save to a new CSV
    grouped_df.to_csv(output_csv, index=False)
    print(f"Grouped rows have been saved to '{output_csv}'.")

# takes a CSV file and two field names as input, then selects and prints rows where both field entries are duplicated
def print_duplicated_rows_2_fields(input_csv, field1, field2):
    # Load the CSV file
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: The file '{input_csv}' was not found.")
        return
    except Exception as e:
        print(f"Error reading the file: {e}")
        return

    # Check if the specified fields exist
    if field1 not in df.columns or field2 not in df.columns:
        print(f"Error: One or both fields '{field1}' and '{field2}' do not exist in the CSV file.")
        return

    # Identify rows where both fields have duplicate values
    duplicated_rows = df[df.duplicated(subset=[field1, field2], keep=False)]
    
    # Group by the specified fields and sort the results
    grouped_duplicates = duplicated_rows.sort_values(by=[field1, field2])
    
    # Print the grouped duplicate rows (only the specified fields)
    if grouped_duplicates.empty:
        print("No rows with duplicate values in both fields were found.")
    else:
        print("Grouped duplicate rows with specified fields:")
        print(grouped_duplicates[['index', field1, field2]].to_string(index=False))

# Reads a CSV file, removes duplicates based on two specified fields, and writes the result to a new file.
def remove_duplicates_based_on_2_fields(csv_file, field1, field2, output_file):
    # Load the CSV file
    try:
        # Load the CSV file
        df = pd.read_csv(csv_file)
        
        # Separate rows with NaN in the specified fields
        nan_rows = df[df[[field1, field2]].isna().any(axis=1)]
        
        # Identify rows without NaN in the specified fields
        valid_rows = df.dropna(subset=[field1, field2])
        
        # Identify duplicates in valid rows
        duplicates = valid_rows.duplicated(subset=[field1, field2], keep=False)
        
        # Filter unique rows from valid rows (first occurrence of duplicates + rows that are not duplicates)
        deduplicated_valid_rows = valid_rows[~duplicates | (valid_rows.duplicated(subset=[field1, field2], keep='first'))]
        
        # Combine deduplicated valid rows with rows that have NaN
        final_df = pd.concat([deduplicated_valid_rows, nan_rows], ignore_index=True)
        
        # Save the result to a new CSV file
        final_df.to_csv(output_file, index=False)
        
        print(f"Deduplicated data (excluding NaN fields) has been saved to {output_file}.")
    except Exception as e:
        print(f"An error occurred: {e}")
