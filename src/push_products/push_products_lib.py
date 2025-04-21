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
from typing import List, Optional, Tuple

from google.cloud import bigquery
from google.cloud import tasks_v2

try:
  from shared import common  # pylint: disable=g-import-not-at-top
except ImportError:
  # This handles cases when code is not deployed using Terraform
  from ..shared import common  # pylint: disable=g-import-not-at-top, relative-beyond-top-level

Product = common.Product
ProductFilter = common.ProductFilter


class Error(Exception):
  """Base error class for this module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class CloudTasksPublishError(Error):
  """Error publishing to Cloud Tasks."""


class CloudTasksQueueNotEmptyError(Error):
  """Error when queue has unfinished tasks."""


class ProductPusher:
  """Product pusher class."""

  def __init__(
      self,
      project_id: str,
      dataset_id: str,
      location: str,
      queue_id: str,
  ):
    """Initialize instance of ProductPusher.

    Args:
      project_id: The Google Cloud project ID.
      dataset_id: The BigQuery dataset ID.
      location: The Google Cloud location.
      queue_id: The Cloud Tasks queue ID.
    """
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.location = location
    self.queue_id = queue_id

    self.bigquery_client = bigquery.Client(self.project_id)
    self.tasks_client = tasks_v2.CloudTasksClient()

  def is_queue_empty(self) -> bool:
    """Checks if the Google Cloud Tasks queue is empty.

    Returns:
        True if the queue is empty, False otherwise.
    """
    # List tasks in the queue
    parent_queue = self.tasks_client.queue_path(
        self.project_id, self.location, self.queue_id
    )
    try:
      request = tasks_v2.ListTasksRequest(parent=parent_queue, page_size=1)
      response = self.tasks_client.list_tasks(request=request)
      return not bool(list(response.tasks))
    except Exception as e:  # pylint: disable=broad-exception-caught
      raise CloudTasksPublishError(f'Error checking queue status: {e}') from e

  def get_all_products_from_view(
      self,
      product_limit: int = 10,
      product_filter: Optional[ProductFilter] = None,
  ) -> list[Product]:
    """Retrieves set of products & their images from feed to classify.

    This is used when Image Inventory is run on an ad-hoc basis, identifying
    all products to classify based on the Products_X table and product_filter.

    Args:
      product_limit (int): Maximum number of products to retrieve
      product_filter (Optional[ProductFilter]): A ProductFilter dataclass

    Returns:
      a list of Product dataclasses
    """

    sql_filter = product_filter.get_sql_filter() if product_filter else 'TRUE'
    query = (
        'SELECT'
        '   offer_id,'
        '   merchant_id,'
        '   aggregator_id,'
        '   title,'
        '   product_type,'
        '   brand,'
        '   image_link,'
        '   additional_image_links'
        f' FROM `{self.project_id}.{self.dataset_id}.get_all_products_view`'
        f' WHERE {sql_filter}'
        f' LIMIT {product_limit}'
    )
    try:
      query_job = self.bigquery_client.query(query)
      rows = query_job.result()
    except Exception as e:  # pylint: disable=broad-exception-caught
      raise BigQueryReadError(f'Failed to read from BigQuery view: {e}') from e

    products = [Product(**row) for row in rows]
    logging.info(
        'Retrieved %d products from get_all_products_view.', len(products)
    )
    return products

  def get_new_products_from_view(
      self,
      product_limit: int = 10,
      product_filter: Optional[ProductFilter] = None,
  ) -> list[Product]:
    """Retrieves set of new unprocessed products & their images to classify.

    This is used when Image Inventory is scheduled & running for the full feed,
    identifying new products to classify based on the get_new_products_view.

    Args:
      product_limit (int): Maximum number of products to retrieve
      product_filter (Optional[ProductFilter]): A ProductFilter dataclass

    Returns:
      a list of Product dataclasses
    """
    sql_filter = product_filter.get_sql_filter() if product_filter else 'TRUE'
    query = (
        'SELECT'
        '   offer_id,'
        '   merchant_id,'
        '   aggregator_id,'
        '   title,'
        '   product_type,'
        '   brand,'
        '   image_link,'
        '   additional_image_links'
        f' FROM `{self.project_id}.{self.dataset_id}.get_new_products_view`'
        f' WHERE {sql_filter}'
        f' LIMIT {product_limit}'
    )
    try:
      query_job = self.bigquery_client.query(query)
      rows = query_job.result()
    except Exception as e:  # pylint: disable=broad-exception-caught
      raise BigQueryReadError(f'Failed to read from BigQuery view: {e}') from e

    products = [Product(**row) for row in rows]
    logging.info(
        'Retrieved %d products from get_new_products_view.', len(products)
    )
    return products

  def push_products(
      self,
      products: list[Product],
      cloud_function_url: str,
  ) -> Tuple[int, int]:
    """Pushes products to Cloud Tasks, attempting all products even if some fail.

    Args:
      products (list[Product]): A list of Product dataclasses.
      cloud_function_url (str): The URL of the Cloud Function to call.

    Returns:
        A tuple containing:
          - success_count (int): Number of products successfully pushed.
          - failure_count (int): Number of products that failed to push.

    Raises:
        CloudTasksPublishError: If there's an issue getting the queue path.
                                Individual task creation errors are logged.
    """
    success_count = 0
    failure_count = 0
    failed_products: List[Tuple[Product, str]] = []

    try:
      parent_queue = self.tasks_client.queue_path(
          self.project_id, self.location, self.queue_id
      )
    except Exception as e:  # pylint: disable=broad-exception-caught
      raise CloudTasksPublishError(f'Failed to resolve queue path: {e}') from e

    logging.info(
        'Attempting to push %d products to Cloud Tasks queue: %s',
        len(products),
        parent_queue,
    )

    for product in products:
      try:
        task_payload = product.to_json().encode('utf-8')
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=cloud_function_url,
                body=task_payload,
                headers={
                    'Content-type': 'application/json',
                },
            )
        )
        request = tasks_v2.CreateTaskRequest(
            parent=parent_queue,
            task=task,
        )
        self.tasks_client.create_task(request=request)
        success_count += 1

      except Exception as e:  # pylint: disable=broad-exception-caught
        failure_count += 1
        error_message = (
            f'Failed to create task for product ID {product.offer_id}: {e}'
        )
        logging.error(error_message, exc_info=True)
        failed_products.append((product, error_message))

    logging.info(
        'Finished pushing products. Success: %d, Failures: %d',
        success_count,
        failure_count,
    )

    if failed_products:
      logging.warning(
          '%d products failed to queue. See previous error logs for details.',
          failure_count,
          extra={
              'json_fields': {
                  'failed_offer_ids': [p.offer_id for p, _ in failed_products]
              }
          },
      )

    return success_count, failure_count
