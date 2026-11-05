from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from executar_avaliacao_sam3_persistente import supervise, pending_compute, CONTINUOUS, SYSTEM_REQUIRED


class SupervisorTests(unittest.TestCase):
    def test_failure_exit_releases_wake_and_preserves_exit_code(self):
        child = Mock(pid=123, returncode=7)
        child.poll.side_effect = [None, 7, 7]
        power = Mock(return_value=CONTINUOUS)
        code = supervise(lambda: child, power, lambda: True, lambda _: None, Mock())
        self.assertEqual(code, 7)
        self.assertEqual([c.args[0] for c in power.call_args_list], [SYSTEM_REQUIRED, CONTINUOUS])
        child.terminate.assert_not_called()

    def test_supervisor_exception_releases_wake_and_reaps_child(self):
        child = Mock(pid=123)
        child.poll.side_effect = [None, None, None]
        power = Mock(return_value=CONTINUOUS)
        def fail(_):raise RuntimeError('test interrupt')
        with self.assertRaisesRegex(RuntimeError, 'test interrupt'):
            supervise(lambda: child, power, lambda: True, fail, Mock())
        child.terminate.assert_called_once()
        child.wait.assert_called_once()
        self.assertEqual(power.call_args_list[-1].args[0], CONTINUOUS)

    def test_waiting_human_references_does_not_hold_wake(self):
        with tempfile.TemporaryDirectory(prefix='pfc-power-test-') as temporary:
            base=Path(temporary);ready=base/'ready.json'
            self.assertFalse(pending_compute(base, ready))
            (base/'CONCLUIDO.json').write_text('{}')
            self.assertTrue(pending_compute(base, ready))
            (base/'identidade').mkdir();(base/'identidade/CONCLUIDO.json').write_text('{}')
            ready.write_text('{"segmentation_pilot_ready":false}')
            self.assertFalse(pending_compute(base, ready))


if __name__ == '__main__':
    unittest.main()
