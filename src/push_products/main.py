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

"""Provides a Cloud Function to push new products to Cloud Tasks."""

import logging
import os

import functions_framework
from google.cloud import logging as cloud_logging
import push_products_lib

logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Global Initialization
PROJECT_ID = os.environ.get('PROJECT_ID', 'Project ID env variable is not set.')
DATASET_ID = os.environ.get('DATASET_ID', 'Dataset ID env variable is not set.')

LOCATION = os.environ.get('LOCATION', 'Location env variable is not set.')
QUEUE_ID = os.environ.get('QUEUE_ID', 'Queue ID env variable is not set.')

CLOUD_FUNCTION_URL = os.environ.get(
    'CLOUD_FUNCTION_URL', 'Cloud Function URL env variable is not set.'
)


@functions_framework.http
def run(request):
  """HTTP Cloud Function."""
  request_json = request.get_json(silent=True)
  product_limit = request_json.get('product_limit', 10)

  product_pusher = push_products_lib.ProductPusher(
      project_id=PROJECT_ID,
      dataset_id=DATASET_ID,
      location=LOCATION,
      queue_id=QUEUE_ID,
  )
  products = product_pusher.get_new_products_from_view(
      product_limit=product_limit
  )
  if products:
    # To prevent duplicate tasks, do not push unless queue is empty.
    if not product_pusher.is_queue_empty():
      raise push_products_lib.CloudTasksQueueNotEmptyError(
          'Queue is not empty!'
      )
    logging.info('Found %d new products to push', len(products))
    product_pusher.push_products(
        products=products, cloud_function_url=CLOUD_FUNCTION_URL
    )
  else:
    logging.info('No new products found, exiting...')
  return 'OK', 200
