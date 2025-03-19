# modules/cloudtasks/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "cloudtasks.googleapis.com",
  ]
  disable_services_on_destroy = false
}

resource "google_cloud_tasks_queue" "classify_images_queue" {
  name     = "classify-images-queue"
  location = var.location
  http_target {
    oidc_token {
      service_account_email = var.service_account_email
      audience              = var.function_url
    }
  }
  rate_limits {
    max_concurrent_dispatches = 100
    max_dispatches_per_second = 33
  }
  retry_config {
    max_attempts  = 3
    max_backoff   = "3600s"
    min_backoff   = "1s"
    max_doublings = 5
  }
  depends_on = [module.module_services]
}
