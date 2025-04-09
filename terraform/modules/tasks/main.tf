# modules/cloudtasks/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "cloudtasks.googleapis.com"
}

resource "google_cloud_tasks_queue" "classify_products_queue" {
  name     = "classify-products-queue"
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
  depends_on = [google_project_service.enable_apis]
}
