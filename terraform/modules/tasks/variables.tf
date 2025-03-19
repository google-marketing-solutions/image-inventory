# modules/tasks/variables.tf

variable "project_id" {
  type = string
}

variable "enable_apis" {
  type = bool
}

variable "location" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "function_url" {
  type = string
}
