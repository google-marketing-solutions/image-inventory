# modules/cloudscheduler/variables.tf

variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "function_url" {
  type = string
}

variable "product_limit" {
  type = number
}

variable "service_account_email" {
  type = string
}

variable "schedule" {
  type    = string
  default = "0 * * * *"
}
