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

"""Unit tests for the classify_product_lib library."""

import datetime
import hashlib
import json
import os
import sys
import unittest
from unittest import mock
from config.structured_output import LabeledImage
from google import genai
from google.cloud import bigquery
from google.genai import types
import requests

# To avoid relative symlink issues, get the absolute path to 'src' directory
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, src_path)

from shared.common import Product  # pylint: disable=g-import-not-at-top
from src.classify_product import classify_product_lib  # pylint: disable=g-import-not-at-top


class TestClassifyProductLib(unittest.TestCase):
  """Unit tests for the classify_product_lib library."""

  def setUp(self):
    """Set up test environment."""
    super().setUp()

    self.mock_http_session = mock.MagicMock(spec=requests.Session)
    self.mock_bigquery_client = mock.Mock(spec=bigquery.Client)
    self.mock_genai_client = mock.Mock(spec=genai.Client)

    self.product1 = Product(
        offer_id='offer1',
        merchant_id=1,
        aggregator_id=101,
        title='Offer 1',
        product_type='Product A',
        image_link='http://image1.com',
        additional_image_links=['http://image2.com'],
    )

    self.mock_genai_file_ref_1 = mock.MagicMock(spec=types.File)
    self.mock_genai_file_ref_1.name = 'mock_file_name_1'
    self.mock_genai_file_ref_2 = mock.MagicMock(spec=types.File)
    self.mock_genai_file_ref_2.name = 'mock_file_name_2'

    self.processed_image1 = classify_product_lib.ProcessedImage(
        image_link='http://image1.com',
        genai_file_reference=self.mock_genai_file_ref_1,
        mime_type='image/jpeg',
        width=100,
        height=100,
        sha256_hash='test_hash',
    )
    self.processed_image2 = classify_product_lib.ProcessedImage(
        image_link='http://image2.com',
        genai_file_reference=self.mock_genai_file_ref_2,
        mime_type='image/jpeg',
        width=100,
        height=100,
        sha256_hash='test_hash',
    )

    self.mock_prompt = 'Test prompt'
    self.mock_model_name = 'gemini-1.0-pro-vision-latest'
    self.mock_table_id = 'test_project.test_dataset.test_table'

    self.product_classifier = self.get_class_under_test()

  def get_class_under_test(self):
    with mock.patch('requests.Session') as mock_http_client:
      with mock.patch('google.cloud.bigquery.Client') as mock_bigquery_client:
        with mock.patch('google.genai.Client') as mock_genai_client:
          mock_http_client.return_value = self.mock_http_session
          mock_bigquery_client.return_value = self.mock_bigquery_client
          mock_genai_client.return_value = self.mock_genai_client

          return classify_product_lib.ProductClassifier(
              prompt=self.mock_prompt,
              model_name=self.mock_model_name,
              table_id=self.mock_table_id,
          )

  def test_processed_image_to_json(self):
    """Test the to_json method of the ProcessedImage class."""
    self.assertEqual(
        self.processed_image1.to_json(),
        json.dumps({
            'image_link': 'http://image1.com',
            'mime_type': 'image/jpeg',
            'width': 100,
            'height': 100,
            'sha256_hash': 'test_hash',
            'labeled_image': None,
        }),
    )

  def test_process_image_success(self):
    """Test process_image function with successful image processing."""

    mock_response = mock.MagicMock()
    mock_response.content = b'test image content'
    mock_response.headers = {'content-type': 'image/jpeg'}
    self.mock_http_session.get.return_value = mock_response

    mock_genai_file_reference = mock.MagicMock(spec=types.File)
    self.mock_genai_client.files.upload.return_value = mock_genai_file_reference

    with mock.patch('io.BytesIO') as mock_bytes_io:
      with mock.patch('PIL.Image.open') as mock_image_open:
        mock_file = mock.MagicMock()
        mock_bytes_io.return_value = mock_file

        mock_image = mock.MagicMock()
        mock_image.size = (100, 100)
        mock_image_open.return_value = mock_image

        return_value = self.product_classifier.process_image(
            'http://image1.com'
        )

    self.mock_http_session.get.assert_called_once_with(
        'http://image1.com', headers=self.product_classifier.http_headers
    )
    self.mock_genai_client.files.upload.assert_called_once_with(
        file=mock_file, config={'mime_type': 'image/jpeg'}
    )
    self.assertEqual(
        return_value,
        classify_product_lib.ProcessedImage(
            image_link='http://image1.com',
            genai_file_reference=mock_genai_file_reference,
            mime_type='image/jpeg',
            width=100,
            height=100,
            sha256_hash=hashlib.sha256(mock_response.content).hexdigest(),
        ),
    )

  def test_process_image_pull_error(self):
    """Test process_image function with image pull error."""
    self.mock_http_session.get.side_effect = Exception('Image pull error')
    with self.assertRaises(classify_product_lib.ImagePullError):
      self.product_classifier.process_image('http://image1.com')

  def test_process_image_genai_error(self):
    """Test process_image function with genai error."""
    mock_response = mock.MagicMock()
    mock_response.content = b'test image content'
    mock_response.headers = {'content-type': 'image/jpeg'}
    self.mock_http_session.get.return_value = mock_response
    self.mock_genai_client.files.upload.side_effect = Exception('genai error')
    with self.assertRaises(classify_product_lib.GenerativeAIError):
      self.product_classifier.process_image('http://image1.com')

  def test_run_multimodal_query(self):
    """Test run_multimodal_query function."""
    mock_labeled_images = [
        LabeledImage(type='silo'),
        LabeledImage(type='lifestyle'),
    ]
    mock_genai_response = mock.MagicMock()
    mock_genai_response.parsed = mock_labeled_images
    mock_genai_response.text = 'test_response'
    self.mock_genai_client.models.generate_content.return_value = (
        mock_genai_response
    )
    processed_images = [self.processed_image1, self.processed_image2]

    return_value = self.product_classifier.run_multimodal_query(
        self.product1, processed_images
    )
    self.assertEqual(return_value, mock_genai_response.text)
    self.assertEqual(
        [processed_images[0].labeled_image, processed_images[1].labeled_image],
        mock_labeled_images,
    )

    self.mock_genai_client.models.generate_content.assert_called_once_with(
        model=self.product_classifier.model_name,
        contents=[
            self.mock_genai_file_ref_1,
            self.mock_genai_file_ref_2,
            mock.ANY,
        ],
        config=self.product_classifier.genai_config,
    )
    self.mock_genai_client.files.delete.assert_has_calls([
        mock.call(name=self.mock_genai_file_ref_1.name),
        mock.call(name=self.mock_genai_file_ref_2.name),
    ])

  def test_run_multimodal_query_genai_error(self):
    """Test run_multimodal_query function with genai error."""
    self.mock_genai_client.models.generate_content.side_effect = Exception(
        'genai error'
    )
    processed_images = [self.processed_image1, self.processed_image2]
    with self.assertRaises(classify_product_lib.GenerativeAIError):
      self.product_classifier.run_multimodal_query(
          self.product1, processed_images
      )

  def test_write_result_to_bigquery(self):
    """Test write_result_to_bigquery function."""

    self.processed_image1.labeled_image = LabeledImage(type='silo')
    self.processed_image2.labeled_image = LabeledImage(type='lifestyle')
    processed_images = [self.processed_image1, self.processed_image2]

    mock_insertion_datetime = datetime.datetime(
        2025, 3, 11, 21, 15, 37, tzinfo=datetime.timezone.utc
    )
    mock_insertion_timestamp = mock_insertion_datetime.strftime(
        '%Y-%m-%d %H:%M:%S'
    )
    self.mock_bigquery_client.insert_rows_json.return_value = []

    with mock.patch(
        'src.classify_product.classify_product_lib.datetime'
    ) as mock_datetime:
      mock_datetime.datetime.now.return_value = mock_insertion_datetime
      self.product_classifier.write_result_to_bigquery(processed_images)

    expected_rows = [
        {
            'image_link': 'http://image1.com',
            'mime_type': 'image/jpeg',
            'width': 100,
            'height': 100,
            'sha256_hash': 'test_hash',
            'type': 'silo',
            'timestamp': mock_insertion_timestamp,
        },
        {
            'image_link': 'http://image2.com',
            'mime_type': 'image/jpeg',
            'width': 100,
            'height': 100,
            'sha256_hash': 'test_hash',
            'type': 'lifestyle',
            'timestamp': mock_insertion_timestamp,
        },
    ]
    self.mock_bigquery_client.insert_rows_json.assert_called_once_with(
        self.mock_table_id, expected_rows
    )

  def test_write_result_to_bigquery_error(self):
    """Test write_result_to_bigquery function with error."""
    self.mock_bigquery_client.insert_rows_json.side_effect = Exception(
        'BigQuery error'
    )
    self.processed_image1.labeled_image = LabeledImage(type='silo')
    with self.assertRaises(classify_product_lib.BigQueryWriteError):
      self.product_classifier.write_result_to_bigquery([self.processed_image1])

  @mock.patch(
      'src.classify_product.classify_product_lib.ProductClassifier.write_result_to_bigquery'
  )
  @mock.patch(
      'src.classify_product.classify_product_lib.ProductClassifier.run_multimodal_query'
  )
  @mock.patch(
      'src.classify_product.classify_product_lib.ProductClassifier.process_image'
  )
  def test_process_product(
      self,
      mock_process_image,
      mock_run_multimodal_query,
      mock_write_result_to_bigquery,
  ):
    """Test process_offer function."""

    mock_processed_images = [
        mock.MagicMock(spec=classify_product_lib.ProcessedImage),
        mock.MagicMock(spec=classify_product_lib.ProcessedImage),
    ]
    mock_process_image.side_effect = mock_processed_images
    mock_run_multimodal_query.return_value = 'test_response'

    class_under_test = self.get_class_under_test()
    class_under_test.process_product(self.product1)

    mock_process_image.assert_has_calls(
        [mock.call('http://image1.com'), mock.call('http://image2.com')]
    )
    mock_run_multimodal_query.assert_called_once_with(
        self.product1, mock_processed_images
    )
    mock_write_result_to_bigquery.assert_called_once_with(mock_processed_images)

  def test_product_classifier_initialization(self):
    """Test ProductClassifier initialization."""
    self.assertEqual(self.product_classifier.prompt, self.mock_prompt)
    self.assertEqual(self.product_classifier.model_name, self.mock_model_name)
    self.assertEqual(self.product_classifier.table_id, self.mock_table_id)
    self.assertEqual(
        self.product_classifier.http_session, self.mock_http_session
    )
    self.assertEqual(
        self.product_classifier.bigquery_client, self.mock_bigquery_client
    )
    self.assertEqual(
        self.product_classifier.genai_client, self.mock_genai_client
    )

    if classify_product_lib.USER_AGENT:
      self.assertEqual(
          self.product_classifier.http_headers,
          {'User-Agent': classify_product_lib.USER_AGENT},
      )
    else:
      self.assertEqual(self.product_classifier.http_headers, {})
    self.assertIsInstance(
        self.product_classifier.genai_config, types.GenerateContentConfig
    )
