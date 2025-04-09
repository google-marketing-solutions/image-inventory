# modules/secrets/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

resource "google_secret_manager_secret" "api_key_secret" {
  secret_id = "image_inventory_api_key"
  replication {
    auto {}
  }
  depends_on = [
    google_project_service.enable_apis
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
