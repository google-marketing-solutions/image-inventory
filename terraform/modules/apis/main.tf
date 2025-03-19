# modules/apis/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "apikeys.googleapis.com",
  ]
  disable_services_on_destroy = false
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
  depends_on = [module.module_services]
}

