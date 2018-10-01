import logging
import codecs
import util
import os
import re
from mustachefile import mustache_render2

class HTML_Filter:

    def __init__(self, files, dbglevel, logfile, mdfile):
        self.logger = util.setup_logger('HTML_Filter', dbglevel=dbglevel, logfile=logfile)
        self.mdfile = mdfile

        try:
            if files['html-img']:
                with codecs.open(files['html-img'], 'r') as stream:
                    self.img_template = stream.read().decode('utf-8')
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s - %s' % (files['html-img'], self.mdfile))

        try:
            if files['html-imgs']:
                with codecs.open(files['html-imgs'], 'r') as stream:
                    self.img_grid_template = stream.read().decode('utf-8')
        except:
            self.img_grid_template = None
            self.logger.warning('Cannot load %s - %s' % (files['html-imgs'], self.mdfile))

        try:
            if files['html-vid']:
                with codecs.open(files['html-vid'], 'r') as stream:
                    self.vid_template = stream.read().decode('utf-8')
        except:
            self.vid_template = None
            self.logger.warning('Cannot load %s - %s' % (files['html-vid'], self.mdfile))

        try:
            if files['html-vids']:
                with codecs.open(files['html-vids'], 'r') as stream:
                    self.vid_grid_template = stream.read().decode('utf-8')
        except:
            self.vid__template = None
            self.logger.warning('Cannot load %s - %s' % (files['html-vids'], self.mdfile))

        self.img_ext = ('.gif','.png','.jpg','.jpeg')
        self.vid_ext = ('.mp4')

    # def __init__(self, filterdir, dbglevel, logfile):
    #     self.filterdir = filterdir
    #     self.logger = util.setup_logger('MDfilter', dbglevel=dbglevel, logfile=logfile)
    #
    #     try:
    #         with codecs.open(os.path.join(filterdir,'img.mustache'), 'r') as stream:
    #             self.img_template = stream.read().decode('utf-8')
    #
    #         self.logger.debug('Loaded filters/img.mustache')
    #     except:
    #         self.img_template = None
    #         self.logger.warning('Cannot load filters/img.mustache')
    #
    #     try:
    #         with codecs.open(os.path.join(filterdir,'mov.mustache'), 'r') as stream:
    #             self.mov_template = stream.read().decode('utf-8')
    #
    #         self.logger.debug('Loaded mov.mustache')
    #     except:
    #         self.mov_template = None
    #         self.logger.warning('Cannot load filters/mov.mustache')
    #
    #     try:
    #         with codecs.open(os.path.join(filterdir,'img-grid.mustache'), 'r') as stream:
    #             self.img_grid_template = stream.read().decode('utf-8')
    #
    #         self.logger.debug('Loaded filters/img-grid.mustache')
    #     except:
    #         self.img_grid_template = None
    #         self.logger.warning('Cannot load filters/img-grid.mustache')
    #
    #     try:
    #         with codecs.open(os.path.join(filterdir,'mov-grid.mustache'), 'r') as stream:
    #             self.mov_grid_template = stream.read().decode('utf-8')
    #
    #         self.logger.debug('Loaded filters/mov-grid.mustache')
    #     except:
    #         self.mov_grid_template = None
    #         self.logger.warning('Cannot load filters/mov-grid.mustache')
    #
    #     self.img_ext = ('.gif','.png','.jpg','.jpeg')
    #     self.mov_ext = ('.mp4')

    def is_image(self, filename):
        return filename.lower().endswith(self.img_ext)

    def is_video(self, filename):
        return filename.lower().endswith(self.vid_ext)

    def apply(self, filepath, rootdir, buffer):
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
                    self.logger.warning('Invalid image or video file %s - %s' % (context['file'], self.mdfile))
            else:
                context = { 'files': [] }
                for item in mm:
                    context['files'].append({'file': item})

                if self.is_image(mm[0]):
                    template = self.img_grid_template
                elif self.is_video(mm[0]):
                    template = self.vid_grid_template
                else:
                    self.logger.warning('Invalid image or video file %s - %s' % (context['file'], self.mdfile))

            if template:
                try:
                    r = mustache_render2(None, None, template, context, self.logger)
                    self.logger.debug('Applying HTML Media Filter to object %s - %s' % (buffer[s:e], self.mdfile))
                except:
                    self.logger.warning('Cannot apply HTML Media Filter to object %s - %s' % (buffer[s:e], self.mdfile))
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
