# modules/cloudscheduler/main.tf

module "module_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 18.0"

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "cloudscheduler.googleapis.com",
  ]
  disable_services_on_destroy = false
}

resource "google_cloud_scheduler_job" "push_products" {
  name             = "scheduled-push-products"
  region           = var.location
  description      = "Invoke push-products on a schedule."
  schedule         = var.schedule # defaults to "0 * * * *" # Hourly
  time_zone        = "America/New_York"
  attempt_deadline = "300s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = var.function_url
    # body needs to be encoded as bytes
    body = base64encode(<<EOT
      {
        "product_limit": 100
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
    module.module_services
  ]
}
