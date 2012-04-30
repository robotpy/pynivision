import unittest
import gc
from nivision import *

class DisposeTestCase(unittest.TestCase):
    def test_opaque_dispose(self):
        img = imaqCreateImage(IMAQ_IMAGE_U8)
        self.assertIsNotNone(img.value)
        imaqDispose(img)
        self.assertIsNone(img.value)
        imaqDispose(img)
        del img
        gc.collect()

    def test_opaque_del(self):
        img = imaqCreateImage(IMAQ_IMAGE_U8)
        self.assertIsNotNone(img.value)
        del img
        gc.collect()

    def test_array_dispose(self):
        names = imaqGetFilterNames()
        x = len(names)
        x = names[0]
        for n in names:
            pass
        self.assertIsNotNone(names._contents)
        imaqDispose(names)
        self.assertIsNone(names._contents)
        imaqDispose(names)
        del names
        gc.collect()

    def test_array_del(self):
        names = imaqGetFilterNames()
        self.assertIsNotNone(names._contents)
        del names
        gc.collect()

    def test_pointer_dispose(self):
        img = imaqCreateImage(IMAQ_IMAGE_U8)
        imaqCountParticles(img, 1)
        report = imaqMeasureParticles(img, IMAQ_CALIBRATION_MODE_PIXEL,
                [IMAQ_MT_CENTER_OF_MASS_X, IMAQ_MT_CENTER_OF_MASS_Y])
        x = report.numMeasurements
        self.assertIsNotNone(report._contents)
        imaqDispose(report)
        self.assertIsNone(report._contents)
        imaqDispose(report)
        del report
        gc.collect()

    def test_pointer_del(self):
        img = imaqCreateImage(IMAQ_IMAGE_U8)
        imaqCountParticles(img, 1)
        report = imaqMeasureParticles(img, IMAQ_CALIBRATION_MODE_PIXEL,
                [IMAQ_MT_CENTER_OF_MASS_X, IMAQ_MT_CENTER_OF_MASS_Y])
        x = report.numMeasurements
        self.assertIsNotNone(report._contents)
        del report
        gc.collect()

def suite():
    return unittest.makeSuite(DisposeTestCase)

if __name__ == "__main__":
    unittest.TextTestRunner().run(suite())
