import subprocess
import tempfile
import unittest
from pathlib import Path
from check_video_frames import analyze


class FrameScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name, filters in [('clean', []), ('flash', ['drawbox=color=white:t=fill:enable=eq(n\\,12)']),
                              ('cut', ['drawbox=color=white:t=fill:enable=gte(n\\,15)'])]:
            cmd = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=160x120:r=30:d=1']
            if filters:
                cmd += ['-vf', ','.join(filters)]
            subprocess.run(cmd + ['-c:v', 'libx264', '-crf', '0', '-pix_fmt', 'yuv420p',
                                  str(cls.root / (name + '.mp4'))], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_constant_video_checks_every_pair(self):
        r = analyze(self.root/'clean.mp4', static_region=(0, 0, 160, 30))
        self.assertEqual((r['decodedFrames'], r['adjacentPairsChecked']), (30, 29))
        self.assertEqual(r['flaggedFrames'], [])
        self.assertEqual(r['status'], 'passed')

    def test_single_bad_frame_is_caught_on_both_edges(self):
        r = analyze(self.root/'flash.mp4', static_region=(0, 0, 160, 30))
        self.assertEqual(r['status'], 'review_required')
        self.assertEqual([f['frame'] for f in r['flaggedFrames']], [12, 13])
        self.assertIn('known_static_region_changed', r['flaggedFrames'][0]['reasons'])

    def test_declared_cut_only_skips_declared_edge(self):
        self.assertEqual(analyze(self.root/'cut.mp4')['status'], 'review_required')
        self.assertEqual(analyze(self.root/'cut.mp4', allowed_cuts=(15,))['status'], 'passed')
        self.assertEqual(analyze(self.root/'flash.mp4', allowed_cuts=(12,))['status'], 'review_required')

    def test_out_of_bounds_regions_and_cuts_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze(self.root/'clean.mp4', static_region=(0, 0, 161, 30))
        with self.assertRaises(ValueError):
            analyze(self.root/'clean.mp4', allowed_cuts=(30,))


if __name__ == '__main__':
    unittest.main()
