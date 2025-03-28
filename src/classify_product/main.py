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


# Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# Global Initialization
for env_var in ['PROJECT_ID', 'DATASET_ID', 'TABLE_NAME', 'MODEL_NAME']:
  if os.environ.get(env_var) is None:
    raise KeyError(f'{env_var} env variable is not set.')

PROJECT_ID = os.environ['PROJECT_ID']
DATASET_ID = os.environ['DATASET_ID']
TABLE_NAME = os.environ['TABLE_NAME']
TABLE_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}'
MODEL_NAME = os.environ['MODEL_NAME']

_PROMPT_FILE = os.path.join('config', 'prompt.txt')
with open(_PROMPT_FILE, 'r', encoding='utf-8') as f:
  PROMPT = f.read()

product_classifier_cls = classify_product_lib.ProductClassifier(
    PROMPT, MODEL_NAME, TABLE_ID
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

  product_classifier_cls.process_product(product)

  return 'OK', 200
