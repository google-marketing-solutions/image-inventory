# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Library with functionality to push new products to Cloud Tasks."""

import dataclasses
import json
import logging

from google.cloud import bigquery
from google.cloud import tasks_v2
from shared.common import Product


class Error(Exception):
  """Base error class for this module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class CloudTasksPublishError(Error):
  """Error publishing to Cloud Tasks."""


class CloudTasksQueueNotEmptyError(Error):
  """Error when queue has unfinished tasks."""


## Global Persistent Connections

# BigQuery
bigquery_client = bigquery.Client()
# Cloud Tasks
tasks_client = tasks_v2.CloudTasksClient()


def is_queue_empty(project_id: str, location: str, queue_id: str):
  """Checks if the Google Cloud Tasks queue is empty.

  Args:
    project_id (str): Project ID for Cloud Tasks queue
    location (str): Location of Cloud Tasks queue
    queue_id (str): Queue ID for Cloud Tasks queue

  Returns:
      True if the queue is empty, False otherwise.
  """
  # List tasks in the queue
  parent_queue = tasks_client.queue_path(project_id, location, queue_id)
  request = tasks_v2.ListTasksRequest(parent=parent_queue)
  response = tasks_client.list_tasks(request=request)
  # Check if the queue is empty
  return not bool(list(response.tasks))


def get_products(
    project_id: str, dataset_id: str, product_limit: int = 10
) -> list[Product]:
  """Retrieves set of products & their images to classify.

  Args:
    project_id (str): Project ID for BigQuery
    dataset_id (str): Dataset ID for BigQuery
    product_limit (int): Maximum number of products to retrieve

  Returns:
    a list of Product dataclasses
  """
  query = (
      'SELECT'
      '   offer_id,'
      '   merchant_id,'
      '   aggregator_id,'
      '   title,'
      '   product_type,'
      '   image_link,'
      '   additional_image_links'
      f' FROM {project_id}.{dataset_id}.get_new_products_view'
      f' LIMIT {product_limit}'
  )
  try:
    query_job = bigquery_client.query(query)
    rows = query_job.result()
  except Exception as e:  # pylint: disable=broad-exception-caught
    raise BigQueryReadError(e) from e
  products = [Product(**row) for row in rows]
  return products


def push_products(
    products: list[Product],
    cloud_function_url: str,
    project_id: str,
    location: str,
    queue_id: str,
):
  """Pushes products to Cloud Tasks.

  Args:
    products (list[Product]): A list of Product dataclasses.
    cloud_function_url (str): The URL of the Cloud Function to call.
    project_id (str): Project ID for Cloud Tasks queue
    location (str): Location for Cloud Tasks queue
    queue_id (str): Queue ID for Cloud Tasks queue

  Raises:
    CloudTasksPublishError: if the Cloud Tasks publish fails
  """

  task_count = 0
  parent_queue = tasks_client.queue_path(project_id, location, queue_id)

  for product in products:
    try:
      # Construct the request body.
      task = tasks_v2.Task(
          http_request=tasks_v2.HttpRequest(
              http_method=tasks_v2.HttpMethod.POST,
              url=cloud_function_url,
              body=product.to_json().encode(),
              headers={
                  'Content-type': 'application/json',
              },
          )
      )
      # Use the client to build and send the task.
      tasks_client.create_task(
          tasks_v2.CreateTaskRequest(
              parent=parent_queue,
              task=task,
          )
      )
      task_count += 1
    except Exception as e:
      raise CloudTasksPublishError(e) from e

  logging.info('Submitted %d tasks to Cloud Tasks.', task_count)
