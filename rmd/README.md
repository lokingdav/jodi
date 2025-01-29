# Robocall Mitigation Database

## Important csv files
- rmd-final.csv: final file obtained after deduplication
- rmd-original.csv: original file

## How to deduplicate entries
- A conveinient Jupyter notebook is provided which contains functions to organize, deduplicate and report statistics of the given RMD CSV file
- Deduplication is done through the following steps
    - remove rows where
        1. business_name and business_address are same
        2. business_name and contact_business_address are same
        3. business_name and are frn same

## CSV field definitions
Some important fields in the CSV are explained.
1. frn - Firm Registration Number
2. implementation - Status of S/S implementation
3. voice_service_provider_choice - Does the provider provide voice services?
4. gateway_provider_choice - Does the provider operate a gateway?
5. intermediate_provider_choice - Does the provider act as an intermediary for call routing?