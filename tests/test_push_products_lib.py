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

import logging
import os
import sys
import unittest
from unittest import mock
from google.cloud import tasks_v2

# To avoid relative symlink issues, get the absolute path to 'src' directory
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if src_path not in sys.path:
  sys.path.insert(0, src_path)

try:
  from shared.common import Product  # pylint: disable=g-import-not-at-top
  from shared.common import ProductFilter  # pylint: disable=g-import-not-at-top
  from src.push_products import push_products_lib  # pylint: disable=g-import-not-at-top
except ImportError as e:
  raise ImportError(
      'Failed to import modules. Check sys.path and structure. Current'
      f' src_path: {src_path}. Error: {e}'
  ) from e


class TestProductPusher(unittest.TestCase):
  """Unit tests for the ProductPusher class."""

  def setUp(self):
    """Set up test environment."""
    super().setUp()
    self.mock_bigquery_client = mock.MagicMock()
    self.mock_tasks_client = mock.MagicMock()

    # Sample product data for tests
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
    self.product3 = Product(
        offer_id='offer3',
        merchant_id=3,
        aggregator_id=103,
        title='Offer 3',
        product_type='Product C',
        brand='Brand C',
        image_link='http://image4.com',
        additional_image_links=[],
    )

    # Configuration values
    self.mock_project_id = 'test_project'
    self.mock_dataset_id = 'test_dataset'
    self.mock_location = 'test_location'
    self.mock_queue_id = 'test_queue'
    self.mock_cloud_function_url = 'http://test-function.com/classify'
    self.mock_queue_path = f'projects/{self.mock_project_id}/locations/{self.mock_location}/queues/{self.mock_queue_id}'

    # Patch the client constructors and assign mocks
    self.bigquery_patcher = mock.patch(
        'google.cloud.bigquery.Client',
        autospec=True,
        return_value=self.mock_bigquery_client,
    )
    self.tasks_patcher = mock.patch(
        'google.cloud.tasks_v2.CloudTasksClient',
        autospec=True,
        return_value=self.mock_tasks_client,
    )

    self.mock_bigquery_constructor = self.bigquery_patcher.start()
    self.mock_tasks_constructor = self.tasks_patcher.start()

    # Instantiate the class under test AFTER patching
    self.product_pusher = push_products_lib.ProductPusher(
        project_id=self.mock_project_id,
        dataset_id=self.mock_dataset_id,
        location=self.mock_location,
        queue_id=self.mock_queue_id,
    )

    # Ensure the mock tasks client returns the expected queue path
    self.mock_tasks_client.queue_path.return_value = self.mock_queue_path

    # Suppress logging during tests unless needed for debugging
    logging.disable(logging.CRITICAL)

  def tearDown(self):
    """Clean up after tests."""
    self.bigquery_patcher.stop()
    self.tasks_patcher.stop()
    logging.disable(logging.NOTSET)  # Re-enable logging
    super().tearDown()

  # --- Tests for is_queue_empty ---

  def test_is_queue_empty_true(self):
    """Test is_queue_empty function when the queue is empty."""
    # Simulate an empty list response (iterator yields nothing)
    self.mock_tasks_client.list_tasks.return_value.tasks = iter([])

    self.assertTrue(self.product_pusher.is_queue_empty())
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    expected_request = tasks_v2.ListTasksRequest(
        parent=self.mock_queue_path, page_size=1
    )
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=expected_request
    )

  def test_is_queue_empty_false(self):
    """Test is_queue_empty function when the queue is not empty."""
    # Simulate a response with one task
    self.mock_tasks_client.list_tasks.return_value.tasks = iter(
        [tasks_v2.Task()]
    )

    self.assertFalse(self.product_pusher.is_queue_empty())
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    expected_request = tasks_v2.ListTasksRequest(
        parent=self.mock_queue_path, page_size=1
    )
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=expected_request
    )

  def test_is_queue_empty_generic_error(self):
    """Test is_queue_empty when list_tasks raises a generic error."""
    self.mock_tasks_client.list_tasks.side_effect = Exception('Some API error')

    with self.assertRaisesRegex(
        push_products_lib.CloudTasksPublishError, 'Error checking queue status'
    ):
      self.product_pusher.is_queue_empty()
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    expected_request = tasks_v2.ListTasksRequest(
        parent=self.mock_queue_path, page_size=1
    )
    self.mock_tasks_client.list_tasks.assert_called_once_with(
        request=expected_request
    )

  # --- Tests for get_new_products_from_view ---

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
    # Mock the query result
    mock_query_job = mock.MagicMock()
    mock_query_job.result.return_value = mock_rows
    self.mock_bigquery_client.query.return_value = mock_query_job

    # Mock ProductFilter
    mock_product_filter = mock.MagicMock(spec=ProductFilter)
    mock_product_filter.get_sql_filter.return_value = (
        'LOWER(brand) IN ("brand a")'
    )

    products = self.product_pusher.get_new_products_from_view(
        product_limit=2, product_filter=mock_product_filter
    )

    # Assertions
    self.assertEqual(len(products), 2)
    self.assertEqual(products[0], self.product1)
    self.assertEqual(products[1], self.product2)

    # Check BigQuery query call
    self.mock_bigquery_client.query.assert_called_once()
    call_args, _ = self.mock_bigquery_client.query.call_args
    query = call_args[0]
    self.assertIn(
        'FROM'
        f' `{self.mock_project_id}.{self.mock_dataset_id}.get_new_products_view`',
        query,
    )
    self.assertIn('LIMIT 2', query)
    self.assertIn('WHERE LOWER(brand) IN ("brand a")', query)
    mock_product_filter.get_sql_filter.assert_called_once()

  def test_get_new_products_bigquery_error(self):
    """Test get_new_products_from_view with BigQuery read error."""
    self.mock_bigquery_client.query.side_effect = Exception(
        'BigQuery connection failed'
    )
    with self.assertRaisesRegex(
        push_products_lib.BigQueryReadError, 'Failed to read from BigQuery view'
    ):
      self.product_pusher.get_new_products_from_view(product_limit=5)

  # --- Tests for get_all_products_from_view (similar to get_new_products) ---

  def test_get_all_products_from_view_success(self):
    """Test get_all_products_from_view with successful BigQuery read."""
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
    # Mock the query result
    mock_query_job = mock.MagicMock()
    mock_query_job.result.return_value = mock_rows
    self.mock_bigquery_client.query.return_value = mock_query_job

    mock_product_filter = mock.MagicMock(spec=ProductFilter)
    mock_product_filter.get_sql_filter.return_value = (
        'LOWER(product_type) LIKE "product a%"'
    )

    products = self.product_pusher.get_all_products_from_view(
        product_limit=5, product_filter=mock_product_filter
    )

    self.assertEqual(len(products), 2)
    self.assertEqual(products[0], self.product1)
    self.assertEqual(products[1], self.product2)

    self.mock_bigquery_client.query.assert_called_once()
    call_args, _ = self.mock_bigquery_client.query.call_args
    query = call_args[0]
    self.assertIn(
        'FROM'
        f' `{self.mock_project_id}.{self.mock_dataset_id}.get_all_products_view`',
        query,
    )
    self.assertIn('LIMIT 5', query)
    self.assertIn('WHERE LOWER(product_type) LIKE "product a%"', query)
    mock_product_filter.get_sql_filter.assert_called_once()

  def test_get_all_products_bigquery_error(self):
    """Test get_all_products_from_view with BigQuery read error."""
    self.mock_bigquery_client.query.side_effect = Exception('BigQuery died')
    with self.assertRaisesRegex(
        push_products_lib.BigQueryReadError, 'Failed to read from BigQuery view'
    ):
      self.product_pusher.get_all_products_from_view(product_limit=1)

  # --- Tests for push_products ---

  def test_push_products_success(self):
    """Test push_products function with successful Cloud Tasks publish for all tasks."""
    products_to_push = [self.product1, self.product2]
    expected_task_count = len(products_to_push)

    # Call the method
    success_count, failure_count = self.product_pusher.push_products(
        products=products_to_push,
        cloud_function_url=self.mock_cloud_function_url,
    )

    # Assertions
    self.assertEqual(success_count, expected_task_count)
    self.assertEqual(failure_count, 0)
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    self.assertEqual(
        self.mock_tasks_client.create_task.call_count, expected_task_count
    )

    # Verify the details of each task created (optional but good)
    calls = self.mock_tasks_client.create_task.call_args_list
    for i, product in enumerate(products_to_push):
      request_arg = calls[i].kwargs[
          'request'
      ]  # Access by keyword arg 'request'
      self.assertEqual(request_arg.parent, self.mock_queue_path)
      task = request_arg.task
      self.assertEqual(task.http_request.url, self.mock_cloud_function_url)
      self.assertEqual(task.http_request.http_method, tasks_v2.HttpMethod.POST)
      self.assertEqual(
          task.http_request.body, product.to_json().encode('utf-8')
      )
      self.assertEqual(
          task.http_request.headers['Content-type'], 'application/json'
      )

  def test_push_products_partial_failure(self):
    """Test push_products when some tasks fail to create."""
    products_to_push = [self.product1, self.product2, self.product3]
    expected_success = 2
    expected_failures = 1

    # Simulate failure for the second product (index 1)
    mock_task_result_ok = mock.MagicMock()  # Simulate successful task creation
    mock_task_result_fail = Exception(
        'Simulated task creation failure for offer2'
    )

    self.mock_tasks_client.create_task.side_effect = [
        mock_task_result_ok,  # Success for product1
        mock_task_result_fail,  # Failure for product2
        mock_task_result_ok,  # Success for product3
    ]

    # Patch logging to check error messages
    with mock.patch(
        'src.push_products.push_products_lib.logging'
    ) as mock_logging:
      # Call the method
      success_count, failure_count = self.product_pusher.push_products(
          products=products_to_push,
          cloud_function_url=self.mock_cloud_function_url,
      )

    # Assertions
    self.assertEqual(success_count, expected_success)
    self.assertEqual(failure_count, expected_failures)
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    # create_task should be called for all products, even if some fail
    self.assertEqual(
        self.mock_tasks_client.create_task.call_count, len(products_to_push)
    )

    # Check that error was logged for the failed task
    mock_logging.error.assert_called_once()
    args, kwargs = mock_logging.error.call_args
    self.assertIn(
        f'Failed to create task for product ID {self.product2.offer_id}',
        args[0],
    )
    self.assertTrue(kwargs.get('exc_info'))  # Check if stack trace was included

    # Check summary logs
    self.assertIn(
        mock.call(
            'Finished pushing products. Success: %d, Failures: %d',
            expected_success,
            expected_failures,
        ),
        mock_logging.info.call_args_list,
    )
    self.assertIn(
        mock.call(
            '%d products failed to queue. See previous error logs for details.',
            expected_failures,
            extra={
                'json_fields': {
                    'failed_offer_ids': [
                        self.product2.offer_id,
                    ]
                }
            },
        ),
        mock_logging.warning.call_args_list,
    )

  def test_push_products_queue_path_error(self):
    """Test push_products when getting the queue path fails."""
    products_to_push = [self.product1, self.product2]

    # Simulate error when calling queue_path
    self.mock_tasks_client.queue_path.side_effect = Exception(
        'Cannot resolve queue path'
    )

    # Assert that the specific error is raised
    with self.assertRaisesRegex(
        push_products_lib.CloudTasksPublishError, 'Failed to resolve queue path'
    ):
      self.product_pusher.push_products(
          products=products_to_push,
          cloud_function_url=self.mock_cloud_function_url,
      )

    # Assert queue_path was called
    self.mock_tasks_client.queue_path.assert_called_once_with(
        self.mock_project_id, self.mock_location, self.mock_queue_id
    )
    # Assert create_task was NOT called
    self.mock_tasks_client.create_task.assert_not_called()


if __name__ == '__main__':
  unittest.main()
