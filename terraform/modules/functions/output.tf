# modules/functions.output.tf

output "function_url" {
  value = google_cloudfunctions2_function.function.url
}
