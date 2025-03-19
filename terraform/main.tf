# main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.24.0"
    }
  }
}

provider "google" {
  project               = var.project_id
  billing_project       = var.project_id
  user_project_override = true
}

data "google_project" "project" {}

resource "random_id" "default" {
  byte_length = 8
}

module "project-services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = true

  activate_apis = [
    "iam.googleapis.com",
  ]
  disable_services_on_destroy = false
}

resource "google_service_account" "service_account" {
  account_id   = var.service_account
  display_name = "Image Inventory Service Account"
  depends_on   = [module.project-services]
}

resource "google_project_iam_member" "project" {
  for_each = toset([
    "roles/bigquery.dataOwner",
    "roles/bigquery.jobUser",
    "roles/cloudtasks.enqueuer",
    "roles/cloudtasks.viewer",
    "roles/iam.serviceAccountOpenIdTokenCreator",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/run.invoker",
    "roles/secretmanager.viewer",
    "roles/storage.objectViewer",
  ])
  project = data.google_project.project.number
  role    = each.key
  member  = google_service_account.service_account.member
}


module "apis" {
  source      = "./modules/apis"
  project_id  = var.project_id
  enable_apis = true
}

module "secrets" {
  source                 = "./modules/secrets"
  project_id             = var.project_id
  enable_apis            = true
  service_account_member = google_service_account.service_account.member
  api_key                = module.apis.api_key_string
}

module "bigquery" {
  source                        = "./modules/bigquery"
  project_id                    = var.project_id
  enable_apis                   = true
  service_account_email         = google_service_account.service_account.email
  default_service_account_email = "service-${data.google_project.project.number}@gcp-sa-bigquerydatatransfer.iam.gserviceaccount.com"
  bigquery_dataset_id           = var.bigquery_dataset_id
  merchant_id                   = var.merchant_id
}


module "functions_classify_product" {
  source                = "./modules/functions"
  project_id            = var.project_id
  enable_apis           = true
  service_account_email = google_service_account.service_account.email
  location              = var.location
  function_name         = "classify-product-tf"
  function_description  = "Classify product image from Cloud Task message."
  source_dir            = "../src/classify_product"
  entry_point           = "run"
  runtime               = "python311"
  environment_variables = {
    PROJECT_ID = data.google_project.project.name
    DATASET_ID = module.bigquery.dataset_id
  }
  secret_environment_variables = {
    gemini_api_key = {
      key     = "gemini_api_key"
      secret  = module.secrets.secret_id
      version = "latest"
    }
  }
  random_id_prefix = random_id.default.hex
}

module "functions_push_products" {
  source                = "./modules/functions"
  project_id            = var.project_id
  enable_apis           = true
  service_account_email = google_service_account.service_account.email
  location              = var.location
  function_name         = "push-products-tf"
  function_description  = "Push new products to Cloud Tasks."
  source_dir            = "../src/push_products"
  entry_point           = "run"
  runtime               = "python311"
  environment_variables = {
    PROJECT_ID            = data.google_project.project.name
    DATASET_ID            = module.bigquery.dataset_id
    QUEUE_ID              = module.tasks.queue_name
    LOCATION              = var.location
    CLOUD_FUNCTION_URL    = module.functions_classify_product.function_url
    SERVICE_ACCOUNT_EMAIL = google_service_account.service_account.email
  }
  max_instance_count = 1
  available_memory   = "256M"
  timeout_seconds    = 300
  random_id_prefix   = random_id.default.hex
}

module "scheduler" {
  source                = "./modules/scheduler"
  project_id            = var.project_id
  enable_apis           = true
  location              = var.location
  function_url          = module.functions_push_products.function_url
  service_account_email = google_service_account.service_account.email
}

module "tasks" {
  source                = "./modules/tasks"
  project_id            = var.project_id
  enable_apis           = true
  location              = var.location
  service_account_email = google_service_account.service_account.email
  function_url          = module.functions_classify_product.function_url
}
