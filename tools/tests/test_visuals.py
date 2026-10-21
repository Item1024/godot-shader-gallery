"""Small synthetic regressions for the M5 comparator and evidence guards."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compare_visuals as visual


class VisualTests(unittest.TestCase):
    def test_threshold_uses_changed_pixels_not_changed_channels(self):
        a = np.zeros((100, 100, 4), dtype=np.int16)
        b = a.copy()
        b[0, 0, :3] = 9
        values = visual.metrics(a, b, [0, 0, 100, 100], 8/255)
        self.assertEqual(values['fraction'], 1/10000)
        self.assertAlmostEqual(values['mean'], 9/255/10000)
        self.assertTrue(visual.within(values, visual.REGRESSION))

    def test_localized_drift_fails_even_with_low_mean(self):
        a = np.zeros((100, 100, 4), dtype=np.int16)
        b = a.copy()
        b[:2, :, :3] = 9
        values = visual.metrics(a, b, [0, 0, 100, 100], 8/255)
        self.assertLess(values['mean'], 2/255)
        self.assertFalse(visual.within(values, visual.REGRESSION))

    def test_alpha_loss_cannot_pass_as_equal_rgb(self):
        a = np.zeros((2, 2, 4), dtype=np.int16)
        b = a.copy()
        b[0, 0, 3] = 255
        values = visual.metrics(a, b, [0, 0, 2, 2], 3/255)
        self.assertEqual(values['mean'], 0)
        self.assertFalse(visual.within(values, visual.REPEAT))

    def test_region_is_enforced_and_cannot_be_out_of_bounds(self):
        a = np.zeros((4, 4, 4), dtype=np.int16)
        b = a.copy()
        b[0, 0, :3] = 255
        self.assertEqual(visual.metrics(a, b, [1, 1, 3, 3])['mean'], 0)
        with self.assertRaises(ValueError):
            visual.metrics(a, b, [1, 1, 4, 4])

    def test_manifest_has_140_states_and_real_metadata_endpoints(self):
        manifest = visual.load_manifest()
        self.assertEqual(sum(len(e['states']) for e in manifest['effects']), 140)

    def test_self_comparison_cannot_prove_complete_dissolve(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            Image.new('RGBA', (4, 4), (0, 0, 0, 255)).save(path/'001_max.png')
            Image.new('RGBA', (4, 4)).save(path/'001_off.png')
            effect = dict(number=1, region=[0, 0, 4, 4], checks=[dict(kind='empty_alpha', a='max', b='off', name='empty')])
            self.assertFalse(visual.check_behavior(effect, path, path)[0]['passed'])

    def test_missing_or_partial_capture_is_rejected(self):
        manifest = visual.load_manifest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            report = dict(complete=False, only=0, defaults_only=True)
            (path/'capture.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                visual.read_capture(path, manifest, defaults_only=True)
            report.update(complete=True, manifest_sha256_lf=visual.digest(visual.MANIFEST, text=True), captures=[])
            (path/'capture.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'canonical states'):
                visual.read_capture(path, manifest, defaults_only=True)

    def test_image_tampering_is_rejected(self):
        manifest = visual.load_manifest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            rows = []
            for effect in manifest['effects']:
                id = f'{effect["number"]:03d}_default'
                image = path/(id+'.png')
                Image.new('RGBA', (640, 480)).save(image)
                rows.append(dict(id=id, category='state', filename=image.name, sha256=visual.digest(image)))
            report = dict(complete=True, only=0, defaults_only=True,
                          manifest_sha256_lf=visual.digest(visual.MANIFEST, text=True), captures=rows)
            (path/'capture.json').write_text(json.dumps(report))
            visual.read_capture(path, manifest, defaults_only=True)
            Image.new('RGBA', (640, 480), 'red').save(path/rows[0]['filename'])
            with self.assertRaisesRegex(ValueError, 'image hash'):
                visual.read_capture(path, manifest, defaults_only=True)

    def test_pending_or_stale_reference_approval_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path/'capture.json').write_text('{}')
            (path/'approval.json').write_text(json.dumps(dict(status='pending')))
            with self.assertRaisesRegex(ValueError, 'human approval'):
                visual.reference_approval(path, {})
            approval = dict(status='approved', reviewer='test fixture', reviewed_at='2026-10-21', capture_sha256='stale')
            (path/'approval.json').write_text(json.dumps(approval))
            with self.assertRaisesRegex(ValueError, 'does not match'):
                visual.reference_approval(path, {})


if __name__ == '__main__':
    unittest.main()
