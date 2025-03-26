# modules/bigquery/variables.tf

variable "project_id" {
  type = string
}

variable "enable_apis" {
  type = bool
}

variable "default_service_account_email" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "bigquery_dataset_id" {
  type = string
}

variable "bigquery_table_name" {
  type = string
}

variable "merchant_id" {
  type = string
}
