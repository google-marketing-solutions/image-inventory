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

"""Provides a Cloud Function to process & classify products."""

import logging
import os

import classify_product_lib
import functions_framework
from google.cloud import logging as cloud_logging
import google.generativeai as genai


# Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Global Initialization
PROJECT_ID = os.environ.get('PROJECT_ID', 'Project ID env variable is not set.')
DATASET_ID = os.environ.get('DATASET_ID', 'Dataset ID env variable is not set.')

## Global Persistent Connections

genai.configure(
    api_key=os.environ.get(
        'gemini_api_key', 'Gemini API key env variable is not set.'
    )
)


@functions_framework.http
def run(request) -> str:
  """HTTP Cloud Function."""
  if request.method != 'POST':
    return 'Method Not Allowed', 405
  if request.content_type != 'application/json':
    return 'Unsupported Media Type', 415

  try:
    request_json = request.get_json(silent=True)
    if not request_json:
      return 'Bad Request: No JSON data provided', 400
    product = classify_product_lib.Product(**request_json)
  except (TypeError, ValueError) as e:
    return f'Bad Request: Invalid JSON format: {e}', 400

  table_id = f'{PROJECT_ID}.{DATASET_ID}.image_classifications'
  classify_product_lib.process_product(product, table_id)

  return 'OK', 200
