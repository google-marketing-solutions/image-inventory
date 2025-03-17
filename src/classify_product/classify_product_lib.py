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

"""Provides image classification using Gemini."""

import dataclasses
import datetime
import enum
import hashlib
import io
import json
import logging
import os
import sys
from typing import Optional

from config.structured_output import LabeledImage
from google.cloud import bigquery
import google.generativeai as genai
from google.generativeai.types import file_types
from PIL import Image
import requests
from shared.common import Product
from typing_extensions import TypedDict


class Error(Exception):
  """Base error class for this module."""


class BigQueryReadError(Error):
  """Error reading from BigQuery."""


class BigQueryWriteError(Error):
  """Error writing to BigQuery."""


class ImagePullError(Error):
  """Error pulling image."""


class GenerativeAIError(Error):
  """Error calling Gemini."""


class TooManyFailuresError(Error):
  """Error when too many failures occur."""


@dataclasses.dataclass
class ProcessedImage:
  """Processed image data class."""

  image_link: str
  genai_file_reference: any
  mime_type: str
  width: int
  height: int
  sha256_hash: str
  labeled_image: LabeledImage = dataclasses.field(init=False)

  def to_json(self) -> str:
    """Returns a JSON string representation of the ProcessedImage."""
    data_dict = dataclasses.asdict(self)
    data_dict.pop('genai_file_reference', None)
    return json.dumps(data_dict)


# HTTP
# USER_AGENT = (  # Default requests user agent can cause 403 errors.
#     'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P)'
#     ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile'
#     ' Safari/537.36 (compatible; Googlebot/2.1;'
#     ' +http://www.google.com/bot.html)'
# )
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
http_session = requests.Session()
# Gemini
MODEL_NAME = 'gemini-2.0-flash'
genai_client = genai.GenerativeModel(model_name=MODEL_NAME)
# BigQuery
bigquery_client = bigquery.Client()

_PROMPT_FILE = os.path.join('config', 'prompt.txt')
with open(_PROMPT_FILE, 'r', encoding='utf-8') as f:
  _PROMPT = f.read()


def process_image(image_link: str) -> ProcessedImage:
  """Processes an image link to extract relevant details & upload to Gemini.

  Args:
    image_link: the image link to process

  Returns:
    a populated ProcessedImage dataclass (except for type)

  Raises:
    ImagePullError: if the image cannot be downloaded from the link
    GenerativeAIError: if the image cannot be uploaded to Gemini
  """
  # Download image from link
  headers = {'User-Agent': USER_AGENT} if USER_AGENT else {}
  try:
    response = http_session.get(image_link, headers=headers)
    response.raise_for_status()
    response_content = response.content
    mime_type = response.headers.get('content-type')
  except Exception as e:
    raise ImagePullError(e) from e

  # Upload to Gemini for multimodal query
  try:
    genai_file_reference = genai.upload_file(
        io.BytesIO(response_content), mime_type=mime_type
    )
  except Exception as e:
    raise GenerativeAIError(e) from e

  # Process image attributes locally
  sha256_hash = hashlib.sha256(response_content).hexdigest()
  image_obj = Image.open(io.BytesIO(response_content))
  width, height = image_obj.size
  # Release memory by deleting image object.
  del image_obj

  return ProcessedImage(
      image_link=image_link,
      genai_file_reference=genai_file_reference,
      mime_type=mime_type,
      width=width,
      height=height,
      sha256_hash=sha256_hash,
  )


def run_multimodal_query(
    product: Product, processed_images: list[ProcessedImage]
):
  """Runs a multimodal query to Gemini to classify the images.

  The determined type is written back to the ProcessedImage dataclass.

  Args:
    product: the Product dataclass for the images to be processed
    processed_images: a list of ProcessedImage dataclasses to classify

  Raises:
    GenerativeAIError: if the Gemini query fails
  """
  prompt = []

  # Adding image indexes to the prompt to match the output with the images.
  # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding#best-practices
  image_ids = ['image' + str(i) for i in range(len(processed_images))]
  prompt.extend(image_ids)

  prompt.append(_PROMPT)
  if product.title is not None:
    prompt.append(f'The product showcased by the images is: {product.title}')
  if product.product_type is not None:
    prompt.append(
        'The category of the product shown in the images is:'
        f' {product.product_type}'
    )

  # Join the uploaded image references and prompt strings together.
  payload = [i.genai_file_reference for i in processed_images] + [
      '\n'.join(prompt)
  ]

  try:
    result = genai_client.generate_content(
        payload,
        generation_config=genai.GenerationConfig(
            response_mime_type='application/json',
            top_k=1,
            top_p=0.2,
            response_schema=list[LabeledImage],
        ),
    )
  except Exception as e:
    raise GenerativeAIError(e) from e

  result_json = json.loads(result.text)
  for pos, labeled_image in enumerate(result_json):
    processed_images[pos].labeled_image = LabeledImage(**labeled_image)

  # Delete the uploaded images from Gemini after processing.
  for processed_image in processed_images:
    processed_image.genai_file_reference.delete()


def write_result_to_bigquery(
    processed_images: list[ProcessedImage], table_id: str
):
  """Writes results to BigQuery.

  Args:
    processed_images: a list of ProcessedImage dataclasses to write rows for.

  Raises:
    BigQueryWriteError: if the BigQuery write fails
  """
  rows = []
  insertion_datetime = datetime.datetime.now(datetime.timezone.utc)
  insertion_timestamp = insertion_datetime.strftime(
      '%Y-%m-%d %H:%M:%S'
  )  # Format: YYYY-MM-DD HH:MM:SS

  for processed_image in processed_images:
    row = {
        key: value
        for key, value in dataclasses.asdict(processed_image).items()
        if key not in ('genai_file_reference', 'labeled_image')
    }
    row.update(dataclasses.asdict(processed_image.labeled_image))
    row['timestamp'] = insertion_timestamp
    rows.append(row)
  try:
    errors = bigquery_client.insert_rows_json(table_id, rows)
    if errors:
      raise BigQueryWriteError(errors)
  except Exception as e:
    raise BigQueryWriteError(e) from e


def process_product(product: Product, table_id: str):
  """Processes product to extract relevant details locally & using Gemini.

  Args:
    product: the Product dataclass to process
    table_id: the BigQuery table to write results to

  Returns:
    a list of ProcessedImage dataclasses
  """
  try:
    image_links = [
        x
        for x in [product.image_link] + product.additional_image_links
        if x is not None
    ]
    processed_images = [process_image(image_link) for image_link in image_links]
    run_multimodal_query(product, processed_images)
    write_result_to_bigquery(processed_images, table_id)
  except Exception as e:
    logging.error(
        '[FAILED] Error processing product ID %s',
        product.offer_id,
        exec_info=True,
        extra={'json_fields': {'product': product.to_json()}},
    )
    raise

  logging.info(
      '[COMPLETED] Finished processing product ID %s',
      product.offer_id,
      extra={
          'json_fields': {
              'product': product.to_json(),
              'processed_images': [pi.to_json() for pi in processed_images],
          }
      },
  )
