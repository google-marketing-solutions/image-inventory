# modules/cloudscheduler/main.tf

resource "google_project_service" "enable_apis" {
  project = var.project_id
  service = "cloudscheduler.googleapis.com"
}


resource "google_cloud_scheduler_job" "push_products" {
  name             = "scheduled-push-products"
  region           = var.location
  description      = "Invoke push-products on a schedule."
  schedule         = var.schedule # defaults to "0 * * * *" # Hourly
  time_zone        = "America/New_York"
  attempt_deadline = "300s"
  paused           = true

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = var.function_url
    # body needs to be encoded as bytes
    body = base64encode(<<EOT
      {
        "product_limit": ${var.product_limit}
      }
      EOT
    )
    headers = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  depends_on = [
    google_project_service.enable_apis
  ]
}
