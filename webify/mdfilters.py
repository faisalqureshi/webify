import logging
import codecs
import os
import re
import util2 as util

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
        self.logger = util.WebifyLogger.get('mdfile')
        
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
            self.vid_template = None
            self.logger.warning('Cannot load %s' % files['html-vids'])

        self.img_ext = ('.gif','.png','.jpg','.jpeg')
        self.vid_ext = ('.mp4')

    def is_image(self, filename):
        return filename.lower().endswith(self.img_ext)

    def is_video(self, filename):
        print(filename)
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

            context = {}
            if len(caption) > 0:
                context['caption'] = caption.strip()

            mm = mediafile.split('|')
            if len(mm) == 1:
                filename = mm[0].strip()
                context['file'] = filename

                if self.is_image(filename):
                    template = self.img_template
                    context['type'] = 'image'
                elif self.is_video(filename):
                    template = self.vid_template
                    context['type'] = 'video'
                else:
                    template = None
                    self.logger.warning('Invalid media type: "%s" in %s' % (filename, file_info))
            else:
                if self.is_image(mm[0]):
                    template = self.img_grid_template
                elif self.is_video(mm[0]):
                    template = self.vid_grid_template
                else:
                    template = None

                context['files'] = []
                for item in mm:
                    filename = item.strip()
                    context['files'].append({'file': filename})

                    if not (self.is_image(filename) or self.is_video(filename)):
                        template = None
                        self.logger.warning('Invalid media file: "%s" in %s' % (filename, file_info))
                        break

            if template:
                try:
                    r = util.mustache_renderer(template, context, file_info)
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
