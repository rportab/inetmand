import unittest
from unittest.mock import Mock

from application.ports.os import OS
from application.use_cases.connection import is_connected, connect, disconnect


class TestIsConnected(unittest.TestCase):
    def test_when_isConnected_then_true(self):
        os = Mock(spec=OS)
        iface = 'any'
        os.iface_exists.return_value = True

        result = is_connected(os, iface)

        self.assertTrue(result)

class TestConnect(unittest.TestCase):
    os = Mock(spec=OS)
    iface = 'any'
    cmd = []

    def tearDown(self):
        self.os.reset_mock()

    def test_when_alreadyConnected_then_nothing(self):
        self.os.iface_exists.return_value = True

        connect(
            os=self.os,
            iface=self.iface,
            cmd=self.cmd,
            wait=False,
        )

        self.os.iface_exists.assert_called_once_with(self.iface)
        self.os.run.assert_not_called()

    def test_when_notConnectedAndNoWait_then_connectAndForget(self):
       self.os.iface_exists.return_value = False

       connect(
           os=self.os,
           iface=self.iface,
           cmd=self.cmd,
           wait=False,
       )

       self.os.iface_exists.assert_called_once_with(self.iface)
       self.os.run.assert_called_once()

    def test_when_notConnectedAndWait_then_connectAndWait(self):
        self.os.iface_exists.side_effect = [False, False, False, True]

        connect(
            os=self.os,
            iface=self.iface,
            cmd=self.cmd,
            wait=True,
        )

        self.assertEqual(4, self.os.iface_exists.call_count)
        self.os.run.assert_called_once()

class TestDisconnect(unittest.TestCase):
    def test_when_notConnected_then_nothing(self):
        os = Mock(spec=OS)
        iface = 'any'
        cmd = []
        os.iface_exists.return_value = False

        disconnect(
            os=os,
            iface=iface,
            cmd=cmd,
        )

        os.run.assert_not_called()
        os.iface_exists.assert_called_once_with(iface)


if __name__ == '__main__':
    unittest.main()
