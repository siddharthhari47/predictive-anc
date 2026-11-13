"""Container dispatch using metadata only; no new test waveforms accessed."""
import unittest
from anc_lab.selector_fresh_study import needs_container_decode


class MediaDispatchTests(unittest.TestCase):
    def test_ogg_video_and_official_video_transcode_use_decoder(self):
        self.assertTrue(needs_container_decode({'mime':'application/ogg','file':'a.ogv'},{}))
        self.assertTrue(needs_container_decode({'mime':'application/ogg','file':'a.ogg'},
            {'representation':{'metadata':{'type':'video/webm; codecs="vp9, opus"'}}}))
        self.assertTrue(needs_container_decode({'mime':'video/webm','file':'a.webm'},{}))

    def test_ordinary_audio_keeps_original_loader(self):
        for mime,file in [('application/ogg','a.ogg'),('audio/wav','a.wav'),('audio/opus','a.opus')]:
            self.assertFalse(needs_container_decode({'mime':mime,'file':file},{}))


if __name__=='__main__':unittest.main()
