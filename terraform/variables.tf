# variables.tf

variable "project_id" {
  type = string
}

variable "service_account" {
  type = string
}

variable "merchant_id" {
  type = string
}

variable "model_name" {
  type = string
  default = "gemini-2.0-flash"
}

variable "bigquery_dataset_id" {
  type    = string
  default = "image_inventory"
}

variable "bigquery_table_name" {
  type    = string
  default = "image_classifications"
}

variable "product_limit" {
  type    = number
  default = 100
}

variable "location" {
  type    = string
  default = "us-central1"
}

variable "gcp_service_account_roles" {
  description = "The list of project roles necessary for the service account"
  type        = list(string)
  default = [
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
  ]
}
