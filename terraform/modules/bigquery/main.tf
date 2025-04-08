# modules/bigquery/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com"
  ]
  disable_services_on_destroy = false
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id  = var.bigquery_dataset_id
  description = "Image Inventory Dataset"
  access {
    role          = "OWNER"
    user_by_email = var.service_account_email
  }
  access {
    role          = "WRITER"
    user_by_email = var.default_service_account_email
  }
  lifecycle {
    ignore_changes = [access]
    prevent_destroy = true
  }
  depends_on = [module.module_services]
}

resource "google_bigquery_data_transfer_config" "merchant_center_config" {
  display_name           = "merchant_center_transfer"
  data_source_id         = "merchant_center"
  schedule               = "every 24 hours"
  destination_dataset_id = google_bigquery_dataset.dataset.dataset_id
  params = {
    "merchant_id"     = var.merchant_id
    "export_products" = "true"
  }
  service_account_name = var.service_account_email
}

resource "google_bigquery_table" "get_new_products" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = "get_new_products_view"
  deletion_protection = true # set to "true" in production

  view {
    query = templatefile(
      "${path.module}/templates/get_new_products.tftpl",
      {
        PROJECT_ID  = var.project_id,
        DATASET_ID  = google_bigquery_dataset.dataset.dataset_id,
        MERCHANT_ID = var.merchant_id,
        TABLE_NAME  = google_bigquery_table.image_classifications.table_id
      }
    )
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "get_all_products" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = "get_all_products_view"
  deletion_protection = true # set to "true" in production

  view {
    query = templatefile(
      "${path.module}/templates/get_all_products.tftpl",
      {
        PROJECT_ID  = var.project_id,
        DATASET_ID  = google_bigquery_dataset.dataset.dataset_id,
        MERCHANT_ID = var.merchant_id,
      }
    )
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "get_product_image_classifications" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = "get_product_image_classifications"
  deletion_protection = true # set to "true" in production

  view {
    query = templatefile(
      "${path.module}/templates/get_product_image_classifications.tftpl",
      {
        PROJECT_ID  = var.project_id,
        DATASET_ID  = google_bigquery_dataset.dataset.dataset_id,
        TABLE_NAME  = google_bigquery_table.image_classifications.table_id
      }
    )
    use_legacy_sql = false
  }
  depends_on = [ google_bigquery_table.get_all_products ]
}

data "external" "generate_table_schema" {
  program = ["python3", "${path.module}/helpers/generate_table_schema.py"]
}

resource "google_bigquery_table" "image_classifications" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  schema              = data.external.generate_table_schema.result.schema
  table_id            = var.bigquery_table_name
  deletion_protection = true # set to "true" in production
}
