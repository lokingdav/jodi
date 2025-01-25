# Robocall Mitigation Database

## Important files
- rmd-final.csv: final file obtained after deduplication
- rmd-original.csv: original file

## Commannds run to get the final file
```bash
python main.py add_index_column rmd-original.csv rmd-indexed.csv
python main.py extract_columns rmd-indexed.csv rmd-extracted-1.csv index frn business_name contact_telephone_number business_address contact_business_address implementation
python main.py remove_newlines_inside_rows rmd-extracted-1.csv rmd-extracted-2.csv business_address contact_business_address
python main.py remove_duplicates_based_on_2_fields rmd-extracted-2.csv rmd-interm-1.csv business_name business_address
python main.py remove_duplicates_based_on_2_fields rmd-interm-1.csv rmd-interm-2.csv business_name contact_business_address
python main.py remove_duplicates_based_on_2_fields rmd-interm-2.csv rmd-interm-3.csv business_name frn
cp rmd-interm-3.csv rmd-final.csv
```