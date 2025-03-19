# modules/cloudtasks/outputs.tf

output "queue_name" {
  description = "The name of the Cloud Tasks queue."
  value       = google_cloud_tasks_queue.classify_products_queue.name
}
