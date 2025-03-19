# modules/cloudfunctions/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "generativelanguage.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
  ]
  disable_services_on_destroy = false
}

resource "google_storage_bucket" "gcf_source" {
  name                        = "${var.random_id_prefix}-${var.function_name}-gcf-source"
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_iam_member" "member" {
  bucket = google_storage_bucket.gcf_source.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${var.service_account_email}"
}

data "archive_file" "function_src" {
  type                        = "zip"
  output_path                 = "/tmp/${var.function_name}.zip"
  source_dir                  = var.source_dir
  exclude_symlink_directories = false
  excludes                    = ["**/__pycache__/"]
}

resource "google_storage_bucket_object" "gcf_source" {
  name   = "${var.function_name}.zip"
  bucket = google_storage_bucket.gcf_source.name
  source = data.archive_file.function_src.output_path
}

data "google_storage_bucket_object" "source_code" {
  bucket = google_storage_bucket_object.gcf_source.bucket
  name   = google_storage_bucket_object.gcf_source.name
}

resource "google_cloudfunctions2_function" "function" {
  name        = var.function_name
  location    = var.location
  description = var.function_description

  build_config {
    runtime     = var.runtime
    entry_point = var.entry_point
    source {
      storage_source {
        bucket     = data.google_storage_bucket_object.source_code.bucket
        object     = data.google_storage_bucket_object.source_code.name
        generation = data.google_storage_bucket_object.source_code.generation
      }
    }
  }
  service_config {
    max_instance_count               = var.max_instance_count
    max_instance_request_concurrency = var.max_instance_request_concurrency
    available_memory                 = var.available_memory
    available_cpu                    = var.available_cpu
    timeout_seconds                  = var.timeout_seconds
    service_account_email            = var.service_account_email
    ingress_settings                 = "ALLOW_INTERNAL_ONLY"
    dynamic "secret_environment_variables" {
      for_each = var.secret_environment_variables
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }
    environment_variables = var.environment_variables
  }
  depends_on = [
    module.module_services,
  ]
}
