# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Lint as: python3
r"""Compute coverage for Abstract SQL for Michigan datasets.

Example usage:


${PATH_TO_BINARY} \
  --michigan_data_dir=${MICHIGAN_DIR} \
  --dataset_name=atis \
  --splits=dev \
  --alsologtostderr

Note that for atis, since the dataset does not use the JOIN ... ON notation,
and instead uses commas to separate tables in the FROM clause, it is necessary
to edit `abstract_sql` to consider from clauses with comma-separated tables.
"""

from __future__ import absolute_import
from __future__ import division

from __future__ import print_function

import collections
import json
import os

from absl import app
from absl import flags

from language.xsp.data_preprocessing import abstract_sql
from language.xsp.data_preprocessing import abstract_sql_converters
from language.xsp.data_preprocessing import michigan_preprocessing

FLAGS = flags.FLAGS

flags.DEFINE_string('michigan_data_dir', '',
                    'Path to michigan /data directory.')
flags.DEFINE_string('dataset_name', '', 'Name of dataset.')
flags.DEFINE_list('splits', None, 'The splits to count examples for.')


def _load_json(filename):
  with open(filename) as json_file:
    return json.load(json_file)


def compute_michigan_coverage():
  """Prints out statistics for asql conversions."""
  # Read data files.
  schema_csv_path = os.path.join(FLAGS.michigan_data_dir,
                                 '%s-schema.csv' % FLAGS.dataset_name)
  examples_json_path = os.path.join(FLAGS.michigan_data_dir,
                                    '%s.json' % FLAGS.dataset_name)
  schema = michigan_preprocessing.read_schema(schema_csv_path)
  foreign_keys = abstract_sql_converters.michigan_db_to_foreign_key_tuples(
      schema)
  table_schema = abstract_sql_converters.michigan_db_to_table_tuples(schema)
  nl_sql_pairs = michigan_preprocessing.get_nl_sql_pairs(
      examples_json_path, FLAGS.splits)

  # Iterate through examples and generate counts.
  num_examples = 0
  num_conversion_failures = 0
  num_successes = 0
  num_parse_failures = 0
  num_reconstruction_failtures = 0
  exception_counts = collections.defaultdict(int)
  for _, gold_sql_query in nl_sql_pairs:
    num_examples += 1
    print('Parsing example number %s.' % num_examples)
    try:
      sql_spans = abstract_sql.sql_to_sql_spans(gold_sql_query, table_schema)
      sql_spans = abstract_sql.replace_from_clause(sql_spans)
    except abstract_sql.UnsupportedSqlError as e:
      print('Error converting:\n%s\n%s' % (gold_sql_query, e))
      num_conversion_failures += 1
      exception_counts[str(e)[:100]] += 1
      continue
    except abstract_sql.ParseError as e:
      print('Error parsing:\n%s\n%s' % (gold_sql_query, e))
      num_parse_failures += 1
      exception_counts[str(e)[:100]] += 1
      continue
    try:
      sql_spans = abstract_sql.restore_from_clause(sql_spans, foreign_keys)
    except abstract_sql.UnsupportedSqlError as e:
      print('Error recontructing:\n%s\n%s' % (gold_sql_query, e))
      exception_counts[str(e)[:100]] += 1
      num_reconstruction_failtures += 1
      continue
    print('Success:\n%s\n%s' %
          (gold_sql_query, abstract_sql.sql_spans_to_string(sql_spans)))
    num_successes += 1
  print('exception_counts: %s' % exception_counts)
  print('Examples: %s' % num_examples)
  print('Failed conversions: %s' % num_conversion_failures)
  print('Failed parses: %s' % num_parse_failures)
  print('Failed reconstructions: %s' % num_reconstruction_failtures)
  print('Successes: %s' % num_successes)


def main(unused_argv):
  compute_michigan_coverage()


if __name__ == '__main__':
  app.run(main)
