
# Image Inventory

Automatically classify product images from a Google Merchant Center feed.

## Overview

This solution automates the classification of product images sourced from a Google Merchant Center feed. It leverages Google Cloud services, including Cloud Functions, Cloud Tasks, BigQuery, and Gemini, to provide a scalable and reliable solution for image classification.

The system pulls product data directly from Google Merchant Center, processes the associated images, and stores the classification results in BigQuery for further analysis.

## Features

- **Automated Image Classification:** Automatically classifies images based on their contextual representation.
- **Integration with Google Merchant Center:** Pulls product data directly from Google Merchant Center using the [Merchant Center BigQuery Transfer](https://cloud.google.com/bigquery/docs/merchant-center-transfer).
- **Cloud-Based:** Leverages Google Cloud services like Cloud Tasks for scalability and reliability.
- **BigQuery Integration:** Stores product data and classification results in BigQuery.
- **Structured Output:** Uses structured output to constrain the generative results.
- **Gemini API:** Uses the Gemini's multimodal functionality to classify images based on your text prompt.

## Installation

### Prerequisites

This installer is using [Terraform](https://www.terraform.io) to define all resources required to set up Image Inventory on Google Cloud Platform.

You will need:

- a [Google Cloud project](https://console.cloud.google.com) with billing enabled.
- Access to [Google Merchant Center](https://business.google.com/us/merchant-center/) account.
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed.

### Clone this repository

Clone this repository using Cloud Shell or your local machine.

### Update `config/`

Go to the `config/` directory:

1. Replace `prompt.txt` with your text prompt.

- The prompt will be executed once for each product alongside each unprocessed image associated with the product (`image_link` and `additional_image_links`).
- In addition to your text in prompt.txt, Image Inventory will append the product's title & product type (when available) to the end of the prompt.
- Adjust the categories to your specific classification needs and make sure they are precise and unambiguous for your use case.

2. Update `structured_output.py`

- The solution will use the `LabeledImage` class defintion to structure and constrain the generated output.
- The prompt should be written with the intention of outputing a list of populated `LabeledImage` classes.
- The following data types are allowed in LabeledImage:    `str`, `enum.Enum`, `int`, `float`, `bool`, `list[AllowedType]`
- During `terraform apply`, the python helper function `generate_table_schema.py` will use the `LabeledImage` class to generate the schema for the `image_classifications` output table in BigQuery.
  - **Note**: If you update this class anytime after deploying, you will need to manually destroy the generated output table and rerun `terraform apply`

### Enable APIs in your Google Cloud Project

Before deploying, ensure the following APIs are enabled in your Google Cloud project:

- [Cloud Resource Manager API](https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com) (`cloudresourcemanager.googleapis.com`)
- [Service Usage API](https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com) (`serviceusage.googleapis.com`)
- All other APIs will be enabled automatically by Terraform.

### Provide values for variables

Create a `variables.tfvars` file in the `terraform/` directory and provide the following values ([click here for details](https://developer.hashicorp.com/terraform/language/values/variables#variable-definitions-tfvars-files)).

| variable                    | description                                                                                               |  |
| ---------------------       | --------------------------------------------------------------------------------------------------------- | ------------------- |
| project_id                  | Google Cloud Project ID                                                      | required            |
| service_account       | Name of service account to create. This account will be used to run and manage the solution. ({service_account}@{project_name}.iam.gserviceaccount.com)| required            |
| merchant_id    |  Merchant ID or Merchant Aggregator ID (MCA) to use. To find the unique identifier of your account, log into Merchant center and look for the number at the top-right corner of the page, above the account email address.| required            |
| bigquery_dataset_id | Name of dataset to create in BigQuery where Merchant Center transfer table(s) and output will be stored, defaults to `image_inventory`  | optional            |
| bigquery_table_name    | Name of dataset to create in BigQuery where output will be stored, defaults to `image_classifications`| optional            |
| location         | [Google Cloud region](https://cloud.withgoogle.com/region-picker) to use, defaults to `us-central1` | optional            |
| product_limit    | Number of products to push to tasks queue every time push_products is called, defaults to `100` | optional            |

### Deploy Image Inventory

To deploy Image Inventory  via Terraform run the below two commands.

The `init` command will initialise the Terraform configuration.

```shell
terraform init
```

The `apply` command will apply the resources to GCP, all required changes are listed when you run this command and you'll be prompted to confirm before anything is applied.

```shell
terraform apply -var-file=variables.tfvars
```

**Note**: If this is your first time using the Merchant Center Transfer, your `terraform apply` will likely fail with a table not found error. It may take up to 24 hours for the Merchant Center transfer table to become available. Once the transfer succeeds and the table is available in BigQuery, try running the `apply` command again.

## Destroy deployed resources

In case you want to undo the deployment you can run the below command from the same directory as you've deployed it from.

```shell
terraform destroy -var-file=variables.tfvars
```

### Contributing

See the [contributing guidelines](contributing.md) for details on how to contribute to this project.

### License

This project is licensed under the Apache 2.0 License.

### Disclaimer

This is not an officially supported Google product. This project is not
eligible for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).
