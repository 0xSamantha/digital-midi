import unittest
from unittest.mock import patch, Mock
from camera import select_device, open_camera


class CameraTests(unittest.TestCase):
    @patch('camera.sys.platform', 'darwin')
    @patch('camera.list_cameras')
    def test_prefers_facetime_over_obs(self, listing):
        listing.return_value = [{'index': 0, 'name': 'OBS Virtual Camera'},
                                {'index': 2, 'name': 'FaceTime HD Camera'}]
        self.assertEqual(select_device(), 2)
        self.assertEqual(select_device(0), 0)

    @patch('camera.sys.platform', 'darwin')
    @patch('camera.list_cameras')
    def test_missing_or_ambiguous_facetime_does_not_select_obs(self, listing):
        listing.return_value = [{'index': 0, 'name': 'OBS Virtual Camera'}]
        with self.assertRaisesRegex(RuntimeError, 'Select one with --device'):
            select_device()
        listing.return_value = [{'index': i, 'name': 'FaceTime HD Camera'} for i in (1, 2)]
        with self.assertRaises(RuntimeError):
            select_device()

    @patch('camera.select_device', return_value=2)
    def test_failed_capture_is_released(self, select):
        cv = Mock()
        cv.VideoCapture.return_value.isOpened.return_value = False
        with self.assertRaises(RuntimeError):
            open_camera(cv)
        cv.VideoCapture.return_value.release.assert_called_once()
