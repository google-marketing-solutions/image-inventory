# modules/apis/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "apikeys.googleapis.com"
}

resource "google_apikeys_key" "api_key" {
  name         = "image-inventory-generative-language-api-key"
  display_name = "Image Inventory API key"
  project      = var.project_id
  restrictions {
    api_targets {
      service = "generativelanguage.googleapis.com"
    }
  }
  depends_on = [google_project_service.enable_apis]
}

