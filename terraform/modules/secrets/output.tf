# modules/secrets/outputs.tf

output "secret_id" {
  description = "The ID of the secret."
  value       = google_secret_manager_secret.api_key_secret.secret_id
}
