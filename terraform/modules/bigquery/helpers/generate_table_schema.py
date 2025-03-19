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

"""Helper function for generating BigQuery table schemas."""

import enum
import json
from typing import Dict, List, TypedDict, get_type_hints

from config.structured_output import LabeledImage


AllowedTypes = [
    str,
    enum.Enum,
    int,
    float,
    bool,
    list[str],
    list[int],
    list[float],
    list[enum.Enum],
]


def default_schema_fields() -> List[Dict[str, str]]:
  return [
      {
          "name": "image_link",
          "type": "STRING",
          "mode": "NULLABLE",
      },
      {
          "name": "mime_type",
          "type": "STRING",
          "mode": "NULLABLE",
      },
      {
          "name": "width",
          "type": "INTEGER",
          "mode": "NULLABLE",
      },
      {
          "name": "height",
          "type": "INTEGER",
          "mode": "NULLABLE",
      },
      {
          "name": "sha256_hash",
          "type": "STRING",
          "mode": "NULLABLE",
      },
      {
          "name": "timestamp",
          "type": "TIMESTAMP",
          "mode": "NULLABLE",
      },
  ]


def generate_bigquery_schema_string(
    labeled_image_class: type[TypedDict],
) -> str:
  """Generates a BigQuery schema from a TypedDict class and returns it as a JSON string.

  Args:
    labeled_image_class: The TypedDict class representing the schema.

  Returns:
    A JSON string representing the BigQuery schema.
  """

  schema = default_schema_fields()
  for field_name, field_type in get_type_hints(labeled_image_class).items():
    if field_type is str or (
        hasattr(field_type, "__mro__") and enum.Enum in field_type.__mro__
    ):
      schema.append({
          "name": field_name,
          "type": "STRING",
          "mode": "NULLABLE",
      })
    elif field_type is int:
      schema.append({
          "name": field_name,
          "type": "INTEGER",
          "mode": "NULLABLE",
      })
    elif field_type is float:
      schema.append({
          "name": field_name,
          "type": "FLOAT",
          "mode": "NULLABLE",
      })
    elif field_type is bool:
      schema.append({
          "name": field_name,
          "type": "BOOLEAN",
          "mode": "NULLABLE",
      })
    # Check if the field type is a list
    elif hasattr(field_type, "__origin__") and field_type.__origin__ is list:
      element_type = field_type.__args__[0]
      if element_type is str or (
          hasattr(element_type, "__mro__") and enum.Enum in element_type.__mro__
      ):
        schema.append({
            "name": field_name,
            "type": "STRING",
            "mode": "REPEATED",
        })
      elif element_type is int:
        schema.append({
            "name": field_name,
            "type": "INTEGER",
            "mode": "REPEATED",
        })
      elif element_type is float:
        schema.append({
            "name": field_name,
            "type": "FLOAT",
            "mode": "REPEATED",
        })
    else:
      raise TypeError(f"Unsupported type for field {field_name}: {field_type}")

  return json.dumps(schema)


if __name__ == "__main__":
  print(json.dumps({"schema": generate_bigquery_schema_string(LabeledImage)}))
