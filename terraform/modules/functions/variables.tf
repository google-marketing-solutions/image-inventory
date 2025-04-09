# modules/cloudfunctions/variables.tf

variable "project_id" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "location" {
  type = string
}

variable "function_name" {
  type = string
}

variable "function_description" {
  type = string
}

variable "source_dir" {
  type = string
}

variable "entry_point" {
  type = string
}

variable "runtime" {
  type = string
}

variable "max_instance_count" {
  type    = number
  default = 100
}

variable "max_instance_request_concurrency" {
  type    = number
  default = 20
}

variable "available_memory" {
  type    = string
  default = "1G"
}

variable "available_cpu" {
  type    = string
  default = "1"
}

variable "timeout_seconds" {
  type    = number
  default = 180
}

variable "secret_environment_variables" {
  type = map(object({
    key     = string
    secret  = string
    version = string
  }))
  default = {}
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "random_id_prefix" {
  type = string
}
