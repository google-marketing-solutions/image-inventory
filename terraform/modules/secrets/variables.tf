# modules/secrets/variables.tf

variable "project_id" {
  type = string
}

variable "enable_apis" {
  type = bool
}

variable "api_key" {
  type      = string
  sensitive = true
}

variable "service_account_member" {
  type = string
}
