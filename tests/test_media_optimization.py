import io
import unittest
from PIL import Image
from banana_bot.routers.media import _optimize_photo

class PhotoOptimizationTests(unittest.TestCase):
    def test_large_photo_is_resized_for_faster_analysis(self):
        source=io.BytesIO(); Image.new("RGB",(3000,2000),"white").save(source,"PNG")
        result=_optimize_photo(source.getvalue())
        with Image.open(io.BytesIO(result)) as image:
            self.assertLessEqual(max(image.size),1280)
            self.assertEqual(image.format,"JPEG")
