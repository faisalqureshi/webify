import logging
import codecs
import os
import re
from util2 import mustache_renderer, WebifyLogger

# We have four options here.  A single image, a series of images, a single video, a series of videos.
#
# Single image/video
# ![caption]{file}
#
# Series of images/videos, use | to separate the files
# ![caption]{file1|file2|...|fileN}
#
# The user can provide up to four mustache templates, one corresponding to each of the four cases.

class HTML_Filter:

    def __init__(self, files):
        self.logger = WebifyLogger.get('mdfile')
        
        try:
            if files['html-img']:
                with codecs.open(files['html-img'], 'r', 'utf-8') as stream:
                    self.img_template = stream.read()
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s' % files['html-img'])

        try:
            if files['html-imgs']:
                with codecs.open(files['html-imgs'], 'r', 'utf-8') as stream:
                    self.img_grid_template = stream.read()
        except:
            self.img_grid_template = None
            self.logger.warning('Cannot load %s' % files['html-imgs'])

        try:
            if files['html-vid']:
                with codecs.open(files['html-vid'], 'r', 'utf-8') as stream:
                    self.vid_template = stream.read()
        except:
            self.vid_template = None
            self.logger.warning('Cannot load %s' % files['html-vid'])

        try:
            if files['html-vids']:
                with codecs.open(files['html-vids'], 'r', 'utf-8') as stream:
                    self.vid_grid_template = stream.read()
        except:
            self.vid__template = None
            self.logger.warning('Cannot load %s' % files['html-vids'])

        self.img_ext = ('.gif','.png','.jpg','.jpeg')
        self.vid_ext = ('.mp4')

    def is_image(self, filename):
        return filename.lower().endswith(self.img_ext)

    def is_video(self, filename):
        return filename.lower().endswith(self.vid_ext)

    def apply(self, buffer, file_info):
        assert(buffer)

        i = 0
        tmp_buffer = ''

        img_re = '(\\!\\[.*?\\])(\\(.+?\\))'
        imgs = re.finditer(img_re, buffer)
        for img in imgs:
            s = img.start()
            e = img.end()
            caption = img.group(1)[2:-1]
            mediafile = img.group(2)[1:-1]

            mm = mediafile.split('|')
            if len(mm) == 1:
                context = {'file': mm[0]}

                if len(caption) > 0:
                    context['caption'] = caption

                if self.is_image(mm[0]):
                    template = self.img_template
                elif self.is_video(mm[0]):
                    template = self.vid_template
                else:
                    self.logger.warning('Invalid image or video file: "%s" in %s' % (context['file'], file_info))
            else:
                context = { 'files': [] }
                for item in mm:
                    context['files'].append({'file': item})

                if self.is_image(mm[0]):
                    template = self.img_grid_template
                elif self.is_video(mm[0]):
                    template = self.vid_grid_template
                else:
                    self.logger.warning('Invalid image or video file %s' % context['file'])

            if template:
                try:
                    r = mustache_renderer(template, context, file_info)
                    self.logger.debug('Applying HTML Media Filter to object %s' % buffer[s:e])
                except:
                    self.logger.warning('Cannot apply HTML Media Filter to object %s' % buffer[s:e])
                    r = buffer[s:img.end()]

                tmp_buffer += buffer[i:s]
                tmp_buffer += r
            else:
                tmp_buffer += buffer[i:e]
            i = e

        if i > 0:
            tmp_buffer += buffer[i:]
            buffer = tmp_buffer

        return buffer
