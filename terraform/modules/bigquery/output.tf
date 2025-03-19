# modules/bigquery/output.tf

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}
