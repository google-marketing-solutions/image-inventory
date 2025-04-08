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

"""Unit tests for the push_products_lib library."""

import os
import sys
import unittest
from unittest import mock
from google.cloud import tasks_v2


# To avoid relative symlink issues, get the absolute path to 'src' directory
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, src_path)

from shared.common import Product  # pylint: disable=g-import-not-at-top
from src.push_products import push_products_lib  # pylint: disable=g-import-not-at-top


class TestProductPusher(unittest.TestCase):
  """Unit tests for the ProductPusher class."""

  def setUp(self):
    """Set up test environment."""
    super().setUp()
    self.mock_bigquery_client = mock.MagicMock()
    self.mock_tasks_client = mock.MagicMock()

    self.product1 = Product(
        offer_id='offer1',
        merchant_id=1,
        aggregator_id=101,
        title='Offer 1',
        product_type='Product A',
        brand='Brand A',
        image_link='http://image1.com',
        additional_image_links=['http://image2.com'],
    )
    self.product2 = Product(
        offer_id='offer2',
        merchant_id=2,
        aggregator_id=102,
        title='Offer 2',
        product_type='Product B',
        brand='Brand B',
        image_link='http://image3.com',
        additional_image_links=[],
    )

    self.mock_project_id = 'test_project'
    self.mock_dataset_id = 'test_dataset'
    self.mock_location = 'test_location'
    self.mock_queue_id = 'test_queue'

    with mock.patch('google.cloud.bigquery.Client') as mock_bigquery_client:
      with mock.patch(
          'google.cloud.tasks_v2.CloudTasksClient'
      ) as mock_tasks_client:
        mock_bigquery_client.return_value = self.mock_bigquery_client
        mock_tasks_client.return_value = self.mock_tasks_client

        self.product_pusher = push_products_lib.ProductPusher(
            project_id=self.mock_project_id,
            dataset_id=self.mock_dataset_id,
            location=self.mock_location,
            queue_id=self.mock_queue_id,
        )

  def test_is_queue_empty_empty(self):
    """Test is_queue_empty function with empty queue."""
    mock_queue_path = 'mock_queue_path'
    self.mock_tasks_client.queue_path.return_value = mock_queue_path
    self.mock_tasks_client.list_tasks.return_value.tasks = []

    self.assertTrue(self.product_pusher.is_queue_empty())

    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=tasks_v2.ListTasksRequest(parent=mock_queue_path)
    )

  def test_is_queue_empty_not_empty(self):
    """Test is_queue_empty function with non-empty queue."""
    mock_queue_path = 'mock_queue_path'
    self.mock_tasks_client.queue_path.return_value = mock_queue_path
    self.mock_tasks_client.list_tasks.return_value.tasks = [tasks_v2.Task()]

    self.assertFalse(self.product_pusher.is_queue_empty())

    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=tasks_v2.ListTasksRequest(parent=mock_queue_path)
    )

  def test_get_new_products_from_view_success(self):
    """Test get_new_products_from_view function with successful BigQuery read."""
    mock_rows = [
        {
            'offer_id': 'offer1',
            'merchant_id': 1,
            'aggregator_id': 101,
            'title': 'Offer 1',
            'product_type': 'Product A',
            'brand': 'Brand A',
            'image_link': 'http://image1.com',
            'additional_image_links': ['http://image2.com'],
        },
        {
            'offer_id': 'offer2',
            'merchant_id': 2,
            'aggregator_id': 102,
            'title': 'Offer 2',
            'product_type': 'Product B',
            'brand': 'Brand B',
            'image_link': 'http://image3.com',
            'additional_image_links': [],
        },
    ]
    params = {
        'project_id': self.mock_project_id,
        'dataset_id': self.mock_dataset_id,
        'product_limit': 2,
    }

    mock_product_filter = mock.MagicMock()
    mock_product_filter.get_sql_filter.return_value = 'MOCK SQL FILTER STR'

    self.mock_bigquery_client.query.return_value.result.return_value = mock_rows

    products = self.product_pusher.get_new_products_from_view(
        product_limit=2, product_filter=mock_product_filter
    )

    call_args = self.mock_bigquery_client.query.call_args
    query = call_args[0][0]
    self.mock_bigquery_client.query.assert_called_once()
    mock_product_filter.get_sql_filter.assert_called_once()
    self.assertIn(
        'FROM {project_id}.{dataset_id}.get_new_products_view'.format(**params),
        query,
    )
    self.assertIn('LIMIT {product_limit}'.format(**params), query)
    self.assertIn('WHERE MOCK SQL FILTER STR', query)
    self.assertEqual(products, [self.product1, self.product2])

  def test_get_new_products_bigquery_error(self):
    """Test get_new_products_from_view function with BigQuery read error."""
    self.mock_bigquery_client.query.side_effect = Exception('BigQuery error')
    with self.assertRaises(push_products_lib.BigQueryReadError):
      self.product_pusher.get_new_products_from_view(product_limit=2)

  def test_get_all_products_from_view_success(self):
    """Test get_products function with successful BigQuery read."""
    mock_rows = [
        {
            'offer_id': 'offer1',
            'merchant_id': 1,
            'aggregator_id': 101,
            'title': 'Offer 1',
            'product_type': 'Product A',
            'brand': 'Brand A',
            'image_link': 'http://image1.com',
            'additional_image_links': ['http://image2.com'],
        },
        {
            'offer_id': 'offer2',
            'merchant_id': 2,
            'aggregator_id': 102,
            'title': 'Offer 2',
            'product_type': 'Product B',
            'brand': 'Brand B',
            'image_link': 'http://image3.com',
            'additional_image_links': [],
        },
    ]
    params = {
        'project_id': self.mock_project_id,
        'dataset_id': self.mock_dataset_id,
        'product_limit': 2,
    }
    mock_product_filter = mock.MagicMock()
    mock_product_filter.get_sql_filter.return_value = 'MOCK SQL FILTER STR'

    self.mock_bigquery_client.query.return_value.result.return_value = mock_rows

    products = self.product_pusher.get_all_products_from_view(
        product_limit=2, product_filter=mock_product_filter
    )

    call_args = self.mock_bigquery_client.query.call_args
    query = call_args[0][0]
    self.mock_bigquery_client.query.assert_called_once()
    mock_product_filter.get_sql_filter.assert_called_once()
    self.assertIn(
        'FROM {project_id}.{dataset_id}.get_all_products_view'.format(**params),
        query,
    )
    self.assertIn('WHERE MOCK SQL FILTER STR', query)
    self.assertIn('LIMIT {product_limit}'.format(**params), query)
    self.assertEqual(products, [self.product1, self.product2])

  def test_get_all_products_bigquery_error(self):
    """Test get_products function with BigQuery read error."""
    self.mock_bigquery_client.query.side_effect = Exception('BigQuery error')
    with self.assertRaises(push_products_lib.BigQueryReadError):
      self.product_pusher.get_all_products_from_view(product_limit=2)

  def test_push_products_success(self):
    """Test push_products function with successful Cloud Tasks publish."""

    mock_queue_path = 'mock_queue_path'
    self.mock_tasks_client.queue_path.return_value = mock_queue_path

    products = [self.product1, self.product2]
    expected_tasks = [
        tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url='http://test.com',
                body=products[i].to_json().encode(),
                headers={'Content-type': 'application/json'},
            )
        )
        for i in range(len(products))
    ]

    self.product_pusher.push_products(
        products=products, cloud_function_url='http://test.com'
    )
    self.assertEqual(self.mock_tasks_client.create_task.call_count, 2)
    self.mock_tasks_client.create_task.assert_has_calls([
        mock.call(tasks_v2.CreateTaskRequest(parent=mock_queue_path, task=t))
        for t in expected_tasks
    ])
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )

  def test_push_products_cloud_tasks_error(self):
    """Test push_products function with Cloud Tasks publish error."""
    self.mock_tasks_client.create_task.side_effect = Exception(
        'Cloud Tasks error'
    )
    products = [self.product1, self.product2]
    with self.assertRaises(push_products_lib.CloudTasksPublishError):
      self.product_pusher.push_products(
          products=products, cloud_function_url='http://test.com'
      )
