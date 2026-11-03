import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.app.service import Store

class ConnectionLifecycleTests(unittest.TestCase):
    def test_context_closes_even_when_references_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'lab.sqlite')
            retained = []
            for _ in range(1100):
                with store.db() as connection:
                    connection.execute('SELECT 1').fetchone()
                    retained.append(connection)
            for connection in retained:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute('SELECT 1')

    def test_commit_and_rollback_before_close(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'lab.sqlite')
            with store.db() as connection:
                connection.execute('CREATE TABLE lifecycle_test(value INTEGER)')
                connection.execute('INSERT INTO lifecycle_test VALUES (1)')
            with self.assertRaisesRegex(ValueError, 'rollback'):
                with store.db() as connection:
                    connection.execute('INSERT INTO lifecycle_test VALUES (2)')
                    raise ValueError('rollback')
            with store.db() as connection:
                self.assertEqual([r[0] for r in connection.execute('SELECT value FROM lifecycle_test')], [1])
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
