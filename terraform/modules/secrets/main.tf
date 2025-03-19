# modules/secrets/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "secretmanager.googleapis.com",
  ]
  disable_services_on_destroy = false
}

resource "google_secret_manager_secret" "api_key_secret" {
  secret_id = "image_inventory_api_key"
  replication {
    auto {}
  }
  depends_on = [
    module.module_services
  ]
}

resource "google_secret_manager_secret_iam_member" "member" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.api_key_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = var.service_account_member
}

resource "google_secret_manager_secret_version" "api_key_secret" {
  secret                 = google_secret_manager_secret.api_key_secret.name
  secret_data_wo         = var.api_key
  secret_data_wo_version = 1
  enabled                = true
}
