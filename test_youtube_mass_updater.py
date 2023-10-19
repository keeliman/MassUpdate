import unittest
import datetime

from youtube_mass_updater import load_configurations, validate_configurations, process_video_title, calculate_publish_time, is_valid_date_format

class TestYoutubeScheduler(unittest.TestCase):

    def test_load_configurations(self):
        config = load_configurations()
        expected_keys = [
            'TITLE_PREFIX', 'TITLE_SUFFIX', 'PLAYLIST_ID', 'DESCRIPTION', 
            'FIRST_INTERVAL', 'SECOND_INTERVAL', 'TEMP_DATE', 'MAX_VIDEOS', 
            'REQ_MAX_RESULT', 'START_DATE', 'START_VIDEO_NUMBER', 'END_VIDEO_NUMBER',
            'VIDEOS_PER_DAY'
        ]
        for key in expected_keys:
            self.assertIn(key, config)

    def test_validate_configurations(self):
        valid_config = {
            "TITLE_PREFIX": "Prefix",
            "TITLE_SUFFIX": "Suffix",
            "PLAYLIST_ID": "PLAYLIST123",
            "DESCRIPTION": "Description",
            "FIRST_INTERVAL": (1, 9),
            "SECOND_INTERVAL": (13, 23),
            "TEMP_DATE": '2023-10-17',
            "MAX_VIDEOS": 400,
            "REQ_MAX_RESULT": 400,
            "START_DATE": datetime.datetime(2023, 10, 17),
            "START_VIDEO_NUMBER": 130,
            "END_VIDEO_NUMBER": 200,
            "VIDEOS_PER_DAY": 2
        }
        self.assertTrue(validate_configurations(valid_config))
        
        invalid_config = valid_config.copy()
        invalid_config['TITLE_PREFIX'] = ''
        self.assertFalse(validate_configurations(invalid_config))

    def test_process_video_title(self):
        video = {'snippet': {'title': 'Video'}}
        prefix = "Prefix_"
        suffix = "_Suffix"
        self.assertEqual(process_video_title(video, prefix, suffix), "Prefix_Video_Suffix")

    def test_calculate_publish_time(self):
        start_date = datetime.datetime(2023, 10, 17)
        index = 2
        first_interval = (1, 9)
        second_interval = (13, 23)
        videos_per_day = 2

        result = calculate_publish_time(start_date, index, first_interval, second_interval, videos_per_day)
        self.assertEqual(result.date(), start_date.date() + datetime.timedelta(days=1))  # should be the next day
        self.assertGreaterEqual(result.hour,1)  # should be in the first interval
        self.assertLessEqual(result.hour, 9)

    def test_is_valid_date_format(self):
        self.assertTrue(is_valid_date_format('2023-10-17'))
        self.assertFalse(is_valid_date_format('17-10-2023'))

if __name__ == '__main__':
    unittest.main(exit=False)
