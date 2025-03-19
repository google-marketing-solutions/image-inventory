# modules/apis/output.tf

output "api_key_string" {
  description = "The API key string."
  value       = google_apikeys_key.api_key.key_string
  sensitive   = true
}
