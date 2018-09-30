import logging
import codecs
import util
import os
import re
from mustachefile import mustache_render2

class HTML_Filter:

    def __init__(self, files, dbglevel, logfile):
        self.logger = util.setup_logger('HTML_Filter', dbglevel=dbglevel, logfile=logfile)

        try:
            if files['html-img']:
                with codecs.open(files['html-img'], 'r') as stream:
                    self.img_template = stream.read().decode('utf-8')
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s' % files['html-img'])

        try:
            if files['html-imgs']:
                with codecs.open(files['html-imgs'], 'r') as stream:
                    self.img_template = stream.read().decode('utf-8')
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s' % files['html-imgs'])

        try:
            if files['html-vid']:
                with codecs.open(files['html-vid'], 'r') as stream:
                    self.img_template = stream.read().decode('utf-8')
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s' % files['html-vid'])

        try:
            if files['html-vids']:
                with codecs.open(files['html-vids'], 'r') as stream:
                    self.img_template = stream.read().decode('utf-8')
        except:
            self.img_template = None
            self.logger.warning('Cannot load %s' % files['html-vids'])

        self.img_ext = ('.gif','.png','.jpg','.jpeg')
        self.mov_ext = ('.mp4')

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

    def is_movie(self, filename):
        return filename.lower().endswith(self.mov_ext)

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
                    print caption
                    print 'caption added?'
                    context['caption'] = caption

                if self.is_image(mm[0]):
                    template = self.img_template
                elif self.is_movie(mm[0]):
                    template = self.mov_template
                else:
                    pass
            else:
                context = { 'files': [] }
                for item in mm:
                    context['files'].append({'file': item})

                if self.is_image(mm[0]):
                    template = self.img_grid_template
                elif self.is_movie(mm[0]):
                    template = self.mov_grid_template
                else:
                    pass

            if template:
                try:
                    r = mustache_render2(None, None, template, context, self.logger)
                    self.logger.debug('Applying HTML Media Filter to object %s' % buffer[s:img.end()])
                except:
                    self.logger.warning('Cannot apply HTML Media Filter to object %s' % buffer[s:img.end()])
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
