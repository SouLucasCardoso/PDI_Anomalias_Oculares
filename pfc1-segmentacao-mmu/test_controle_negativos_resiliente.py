import unittest
from executar_sam3_negativos_resiliente import watch


class Child:
    def __init__(self, code=0):
        self.returncode = None
        self.steps = 0
        self.code = code

    def poll(self):
        if self.steps >= 3:
            self.returncode = self.code
        return self.returncode

    def tick(self, seconds):
        self.steps += 1


class IsolatedObserverTests(unittest.TestCase):
    def test_permission_error_in_observer_does_not_interrupt_training(self):
        child = Child(); errors = []
        def locked_report():
            raise PermissionError('Report locked by another process')
        self.assertEqual(watch(child, locked_report, child.tick, errors.append), 0)
        self.assertEqual(child.steps, 3)
        self.assertEqual(len(errors), 3)

    def test_reporting_log_failure_also_does_not_interrupt_training(self):
        child = Child()
        def fail(*args):
            raise PermissionError('Output unavailable')
        self.assertEqual(watch(child, fail, child.tick, fail), 0)
        self.assertEqual(child.steps, 3)

    def test_scientific_worker_failure_remains_failure(self):
        child = Child(code=7)
        self.assertEqual(watch(child, lambda: None, child.tick, lambda error: None), 7)


if __name__ == '__main__':
    unittest.main()
